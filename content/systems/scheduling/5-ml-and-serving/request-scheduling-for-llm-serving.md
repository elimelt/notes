---
title: Request Scheduling for LLM Serving
category: Scheduling
tags:
  - scheduling
  - llm serving
  - batching
  - admission control
  - latency
  - throughput
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Scheduling in autoregressive model serving, including admission, prefill versus decode tradeoffs, continuous batching, and SLO-aware request selection.
sources:
  - title: "Orca: A Distributed Serving System for Transformer-Based Generative Models"
    url: https://www.usenix.org/system/files/osdi22-yu.pdf
    type: paper
  - title: "SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills"
    url: https://arxiv.org/abs/2308.16369
    type: paper
  - title: "DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving"
    url: https://arxiv.org/abs/2401.09670
    type: paper
---

## Purpose

The scheduling problem in LLM serving is not "pick the next request" in the old CPU sense. The scheduler is simultaneously choosing:

- which requests are admitted
- how requests are batched
- whether prefill and decode interfere or separate
- whose token gets emitted next when resources are scarce

The queueing and fairness ideas are familiar. The cost model is not.

## Two Phases, Two Different Costs

Autoregressive serving has two major phases:

- **prefill**: process the input prompt
- **decode**: generate one token at a time

Prefill wants large matrix multiplies and is compute hungry. Decode is dominated much more by KV-cache reads and memory traffic.

So one scheduler is implicitly solving two different resource-allocation problems.

## Why Batching Is Scheduling

Batching is not just throughput optimization. It is the serving scheduler's main control knob.

- Large batches improve hardware utilization.
- Large batches increase waiting time.
- Prefill-heavy batches can stall decode-heavy workloads.

That is a scheduling tradeoff, not a library setting.

## Continuous Batching

The key Orca idea is iteration-level scheduling. New work can enter at token-step boundaries instead of waiting for an entire request batch to drain.

That reduces idle slots, but it also creates interference:

- long prefills can delay many decodes
- long decodes consume KV-cache capacity for a long time

## Chunked Prefill and Disaggregation

Chunked prefill breaks the prompt into bounded pieces so decode latency is less hostage to giant prompts. Prefill/decode disaggregation goes further and places the two phases on different machines or pools.

This is another way of saying:

- classify work by service shape
- stop forcing incompatible work classes through one queue

That is classic scheduling wisdom wearing new clothes.

## What a Practical Scheduler Optimizes

Common objectives:

- maximize throughput
- keep TTFT below a target
- keep per-token latency below a target
- avoid starvation of long prompts
- share service fairly across users

Those objectives conflict. A scheduler that greedily favors short prompts may look excellent on average and still be unusable for users with long contexts.

## Skeleton Scheduler Loop

```python
def schedule(waiting, active_decode, kv_budget_tokens, max_batch_tokens):
    admitted = []
    used_tokens = sum(req.live_tokens for req in active_decode)

    while waiting:
        req = waiting[0]
        if used_tokens + req.predicted_live_tokens > kv_budget_tokens:
            break
        if sum(r.step_tokens for r in admitted) + req.prefill_chunk > max_batch_tokens:
            break
        admitted.append(waiting.pop(0))
        used_tokens += req.predicted_live_tokens

    return admitted
```

Real systems need much more machinery. The shape is still:

- capacity check
- latency check
- fairness check
- then admit

## Scheduling Heuristics That Matter

- Separate short and long prompts when possible.
- Do not let giant prefills repeatedly blow up decode latency.
- Treat KV-cache capacity like a first-class scheduling resource.
- Track user fairness, not only request fairness.
- Reject or defer work early if admitting it guarantees SLO failure.

## Related Notes

- [[ml/serving-systems/batching|Batching]]
- [[ml/serving-systems/performance-modeling|Performance Modeling]]
- [[ml/serving-systems/memory-management|Memory Management]]
- [[systems/scheduling/4-cluster-and-datacenter/stragglers-speculation-and-overload|Stragglers, Speculation, and Overload]]

