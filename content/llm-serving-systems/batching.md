---
title: Batching in LLM Serving Systems
category: Machine Learning Systems
tags:
  - batching
  - performance
  - throughput
  - latency
  - llm
  - serving-systems
  - machine-learning
date: 2025-05-25
updated: 2026-07-30
status: needs-review
description: How batching strategies (simple, continuous, chunked prefill, prefill-decode disaggregation) trade throughput against TTFT and TPOT, with the batch size formulas that fall out of SLO and KV-cache constraints.
sources:
  - title: CSE 599K, LLM Serving Systems, University of Washington, Spring 2025 (lecture notes)
    type: lecture
  - title: "Orca: A Distributed Serving System for Transformer-Based Generative Models (OSDI 2022)"
    url: https://www.usenix.org/conference/osdi22/presentation/yu
    type: paper
  - title: "SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills"
    url: https://arxiv.org/abs/2308.16369
    type: paper
  - title: "DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving"
    url: https://arxiv.org/abs/2401.09383
    type: paper
---

## Purpose

This note works through the main batching strategies for LLM serving and the constraints that limit batch size. Batching exposes the tradeoff between the latency and throughput models in [[llm-serving-systems/performance-modeling|Performance Modeling]] and the per-request KV-cache costs in [[llm-serving-systems/memory-management|Memory Management]].

These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025, taught by Prof. Baris Kasikci with TA Kan Zhu. The specific latencies and capacity numbers below come from lecture slides. I have not reproduced them, and the slides do not spell out the full measurement setup, so treat them as illustrative.

## Core idea

An H100 needs a GEMM batch size around 333 before it becomes compute bound (see the critical intensity derivation in [[llm-serving-systems/performance-modeling|Performance Modeling]]), so a serving system that decodes one request at a time wastes almost all of its FLOPs. Batching recovers that throughput. The cost is latency, and every batching strategy is a different answer to how much latency you pay and where.

## User experience metrics

The latency side of the tradeoff is measured with a few standard quantities:

- Time to First Token (TTFT): time from request submission to the first generated token. TTFT = queuing time + prefill time.
- Time Per Output Token (TPOT, also called ITL or inter-token latency): gap between consecutive output tokens. Reported as an average or as a maximum.
- End-to-end time: queue + prefill + full decode.
- Normalized latency: end-to-end time divided by output token count.

Service level objectives combine these. Meeting an end-to-end deadline is the easiest target, since the system can shuffle time between prefill and decode freely. TTFT plus average TPOT is harder. TTFT plus maximum TPOT is hardest, because a single slow decode step violates it. When the SLO is deadline shaped, the server can deliberately delay token output to smooth generation, releasing buffered tokens at a steady rate that still lands inside the deadline.

## Batching strategies

### Simple batching

Form a batch, run prefill for everyone, then decode everyone in lockstep until the last request finishes. Throughput is the lowest of the four strategies because the whole batch waits on the longest decode, and finished slots sit idle. TTFT and TPOT are short, and the implementation is trivial.

### Continuous batching (Orca)

[Orca](https://www.usenix.org/conference/osdi22/presentation/yu) admits new requests at token granularity: whenever a decode slot frees up, a waiting request takes it. Nothing waits for the longest request, so throughput rises, the GEMM batch size stabilizes, and queuing time drops. The cost is interference. Prefills run inside the same iteration as decodes, so a large arriving prompt stalls every concurrent decode, and prefill itself waits on decode work.

The steady-state GEMM batch size follows from counting tokens. A request with prefill length $p$ and decode length $d$ lives for $d + 1$ iterations (one iteration processes all $p$ prompt tokens, then $d$ iterations produce one token each) and contributes $p + d$ token computations over that lifetime. With $B$ requests in flight the average tokens per iteration is

$$\text{GEMM batch size} = \frac{p+d}{d+1}B = B + \frac{p-1}{d+1}B \approx \left(1 + \frac{p}{d}\right)B \text{ for large } d$$

Longer prompts inflate the GEMM batch, longer decodes shrink it toward $B$. Example from lecture: $B = 512$ with $p/d = 2$ gives a GEMM batch of about $512 \times 3 = 1536$.

### Chunked prefill

Continuous batching still produces generation stalls because prefill sizes vary. Chunked prefill (introduced by [Sarathi](https://arxiv.org/abs/2308.16369)) fixes a token budget per iteration and fills it with all the pending decodes plus a fixed-size chunk of whatever prefill is in progress. The GEMM batch size becomes constant, decode latency becomes controlled, and throughput is the highest of the four strategies. TTFT gets worse, since a prompt now takes several iterations to prefill, and the scheduler has to manage chunk state.

### Prefill-decode disaggregation

Run prefill and decode on separate clusters ([DistServe](https://arxiv.org/abs/2401.09383) is the reference design). The prefill server processes the prompt, ships the KV cache to a decode server, and the decode server generates tokens. Both TTFT and TPOT can be short because neither phase interferes with the other, and in the limit you can dedicate a machine per request. Throughput suffers, since the decode cluster runs memory bound at modest batch sizes, and the KV transfer adds real cost. Lecture figure: about 160 ms to move the KV cache for a 16K-token prompt. Chunked prefill combined with layer-wise transfer hides most of that latency by streaming KV pages while later chunks are still computing; only the last layer of the last chunk has to move after prefill finishes.

## What limits batch size

### SLO constraints

For disaggregated serving, the prefill batch is limited by TTFT and the decode batch by TPOT. The decode constraint is $B \cdot \text{attn} + \text{GEMM}(B) + C < \text{TPOT}$, where $\text{attn}$ is the per-request attention (KV read) cost, $\text{GEMM}(B)$ is the dense compute for batch size $B$, and $C$ is fixed overhead.

For chunked prefill with dense token budget $B_{dense}$, the fraction $\frac{d}{p+d}$ of the budget is decode tokens, so

$$\text{Cycle time} = \text{GEMM}(B_{dense}) + \frac{d}{p+d}B_{dense} \cdot \text{attn}$$

with the constraints that cycle time stays under TPOT and $\frac{p+d}{B_{dense}} \times \text{cycle time}$ (the iterations needed to fully prefill one request, times cycle time) stays under TTFT.

### KV cache capacity

An 8B model on an H100 leaves room for roughly 512K tokens of KV cache (derivation in [[llm-serving-systems/memory-management|Memory Management]]). A request holds its $p$ prefill tokens for its entire decode and its decode allocation grows linearly from 0 to $d$, so on average it occupies $p + \frac{d}{2}$ token slots. With capacity $C$ tokens:

$$B = \frac{C}{p + \frac{1}{2}d}$$

When lengths vary, longer requests occupy the cache for more iterations, which weights the average toward them:

$$B = \frac{d_{avg}\,C}{(pd)_{avg} + \frac{1}{2}(d^2)_{avg}}$$

Sanity check from the lecture example: 1K input tokens, output uniform on 0 to 4K, $C = 512K$. Then $d_{avg} = 2K$, $(pd)_{avg} = 2M$, $(d^2)_{avg} = \frac{(4K)^2}{3} \approx 5.33M$, giving $B \approx \frac{2K \times 512K}{2M + 2.67M} \approx 220$.

The awkward part is that $d$ is unknown at admission time. The cache fills gradually and can run out mid-decode.

### Handling memory pressure

Two families of mitigation. Prediction-based control uses a small encoder model to predict output length, stops admitting prefills when the predicted KV footprint would exceed capacity, and (for disaggregated setups) parks requests in a decode pending queue. When the system still runs out, it evicts. Offloading a victim's KV cache to CPU memory beats recomputing it, by roughly 12x in the lecture's A100 estimate (see the eviction analysis in [[llm-serving-systems/memory-management|Memory Management]]), with least-recently-used requests evicted first.

## Comparison

| Method              | Throughput | TTFT    | TPOT             | Infra complexity |
| ------------------- | ---------- | ------- | ---------------- | ---------------- |
| Simple              | Lowest     | Short   | Short            | Low              |
| Continuous batching | High       | Longer  | Long, unstable   | Low              |
| Chunked prefill     | Highest    | Longest | Long, controlled | Medium           |
| PD disaggregation   | Low        | Short   | Short            | High             |

## Edge cases and open issues

Hitting a 95th-percentile SLO target sometimes forces ugly policies, like dropping requests with very long inputs or outputs, indefinitely delaying requests predicted to violate their SLO, or prioritizing requests with strict SLOs over lenient ones. Fairness cuts against pure SLO attainment: every request should make progress, users should get comparable throughput shares, and a graded "badness" measure of SLO violation is more useful for scheduling than a binary attain-or-violate flag. Output length remains the central uncertainty. Long generations sit in the KV cache, create memory pressure, and cause batch size oscillations, so length prediction accuracy directly affects how close a scheduler gets to the formulas above.

## Related notes

- [[llm-serving-systems/performance-modeling|Performance Modeling]]
- [[llm-serving-systems/memory-management|Memory Management]]
- [[llm-serving-systems/speculative-decoding|Speculative Decoding]]
