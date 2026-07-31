---
title: Speculative Decoding in LLM Serving Systems
category: Machine Learning Systems
tags:
  - speculative-decoding
  - llm
  - performance
  - machine-learning
date: 2025-05-25
updated: 2026-07-30
status: evergreen
description: How speculative decoding accelerates inference with draft models and rejection sampling, why the output distribution is preserved, and the tree-based extensions (Medusa, SpecInfer).
sources:
  - title: Fast Inference from Transformers via Speculative Decoding (Leviathan et al.)
    url: https://arxiv.org/abs/2211.17192
    type: paper
  - title: Accelerating Large Language Model Decoding with Speculative Sampling (Chen et al.)
    url: https://arxiv.org/abs/2302.01318
    type: paper
  - title: "Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads"
    url: https://arxiv.org/abs/2401.10774
    type: paper
  - title: "SpecInfer: Accelerating Generative Large Language Model Serving with Tree-based Speculative Inference and Verification"
    url: https://arxiv.org/abs/2305.09781
    type: paper
  - title: CSE 599K, LLM Serving Systems, University of Washington, Spring 2025 (lecture notes)
    type: lecture
---

## Purpose

This note explains speculative decoding: the algorithm, why it leaves the output distribution unchanged, and the tree-based variants used in serving systems. Speculative decoding changes the decode workload and makes throughput depend on acceptance rates, which complements the scheduling tradeoffs in [[llm-serving-systems/batching|Batching]] and the baseline model in [[llm-serving-systems/performance-modeling|Performance Modeling]].

These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025, taught by Prof. Baris Kasikci with TA Kan Zhu.

## Core idea

A small draft model generates several candidate tokens quickly, and the large target model verifies them all in a single parallel forward pass. The analogy is speculative execution in CPUs: guess ahead, verify cheaply, and roll back only what was wrong. The technique comes from [Leviathan et al.](https://arxiv.org/abs/2211.17192) and [Chen et al.](https://arxiv.org/abs/2302.01318), developed independently.

Two observations make it work. At low batch size, decoding is memory bound (see [[llm-serving-systems/performance-modeling|Performance Modeling]]): a forward pass over one token and a forward pass over five tokens cost nearly the same wall-clock time because both are dominated by streaming the weights. So verifying a batch of drafted tokens is almost free relative to generating them one at a time. And draft models are accurate on easy tokens, which are most tokens. Completing "Geoffrey Hinton did his PhD at the University of..." does not need a 70B model; a small model gets "Edinburgh" right, and the target model's capacity only matters at genuinely hard positions.

## The algorithm

One round with draft length $\gamma$ (say 5):

1. Draft: run the draft model $M_p$ autoregressively $\gamma$ times, sampling $x_1, \dots, x_5$ with distributions $p_1, \dots, p_5$:

```text
p1(x) = Mp(prefix)                    -> x1
p2(x) = Mp(prefix, x1)                -> x2
...
p5(x) = Mp(prefix, x1, x2, x3, x4)   -> x5
```

2. Verify: run the target model $M_q$ once over the whole drafted sequence, producing all the target distributions in one pass:

```text
q1(x), q2(x), ..., q6(x) = Mq(prefix, x1, x2, x3, x4, x5)
```

This works because a single transformer forward pass yields next-token distributions at every position (the same fact that makes prefill parallel; see [[llm-serving-systems/transformers|Transformers]]):

```python
# Project to vocabulary
# in:  (seq_len, hidden_dim)
# out: (seq_len, vocab_size)
logits = model_output.matmul(lm_head_weight.t())
```

The target model only produces distributions here; new tokens are sampled from the draft model, plus one correction sample described below.

### Accepting and rejecting

Walk the drafted tokens left to right, comparing the draft probability $p(x)$ of each sampled token against the target probability $q(x)$:

- If $q(x) \geq p(x)$: accept. The target model likes this token at least as much as the draft did.
- If $q(x) < p(x)$: accept with probability $q(x)/p(x)$.

On the first rejection, discard that token and everything after it, and sample the replacement from the corrected distribution $\propto \max(q(x) - p(x), 0)$. This is exactly rejection sampling, and the Leviathan and Chen papers prove the combined procedure produces samples distributed identically to sampling from the target model alone. The acceleration is lossless in distribution.

Per round the output is between 1 token (first draft token rejected, correction sample emitted) and $\gamma + 1$ tokens (all accepted, plus one free token from $q_{\gamma+1}$). The worst case costs no more than ordinary decoding, since a normal forward pass also yields one token.

## Performance

Two parameters govern speedup: $\alpha$, how well the draft distribution matches the target (acceptance rate), and $\gamma$, the draft length. Higher $\alpha$ means longer accepted runs. For fixed $\alpha$ there is an optimal $\gamma$, because each additional draft token is more likely to be thrown away while still costing draft compute. The Leviathan paper reports 1.4x to 3.4x speedups with T5 drafters depending on model size and task (T5-Small 2.6-3.4x, T5-Base 2.4-3.0x, T5-Large 1.4-2.2x).

## Tree-based variants

### Medusa

[Medusa](https://arxiv.org/abs/2401.10774) drops the separate draft model and adds extra decoding heads to the target model itself, each predicting a token several positions ahead. The heads are cheap to train (Medusa-1 fine-tunes heads on a frozen backbone; Medusa-2 trains heads and backbone together with a special recipe) and serving stays simple because there is one model with one parallelism configuration.

Since each head proposes several candidates, the candidates compose into a tree of possible continuations rather than a single sequence. Tree attention verifies all branches in one forward pass: a topology-aware attention mask lets every token attend only to its ancestors in the tree, so distinct branches do not contaminate each other. The paper reports around 2.3-3.6x speedup across task categories.

### SpecInfer

[SpecInfer](https://arxiv.org/abs/2305.09781) attacks draft coverage: one draft model may miss the target's actual continuation, so it runs several small speculators (or one boosted with multiple sampling) to build a candidate token tree, then verifies the whole tree in one pass with the same topology-aware causal masking idea. Verification piggybacks on the memory-bound regime, where scoring many tree nodes costs little more than scoring one.

## When it helps

Speculative decoding pays off when decoding is memory bound (low batch size), when the text is predictable enough for drafts to hit (code, templated prose), and when output quality cannot be compromised, since the distribution is provably unchanged. At high batch sizes the target model's verification passes stop being free, the compute-bound regime takes over, and the technique's advantage shrinks; that interaction with scheduler load is exactly the territory of [[llm-serving-systems/batching|Batching]].

## Related notes

- [[llm-serving-systems/batching|Batching]]
- [[llm-serving-systems/performance-modeling|Performance Modeling]]
- [[llm-serving-systems/transformers|Transformers]]
