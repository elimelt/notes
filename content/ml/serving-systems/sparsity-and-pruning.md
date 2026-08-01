---
title: Sparsity and Pruning in LLM Serving Systems
aliases:
  - llm-serving-systems/sparsity-and-pruning
category: Machine Learning Systems
tags:
  - sparsity
  - pruning
  - performance-optimization
  - machine-learning
date: 2025-05-25
updated: 2026-07-30
status: needs-review
description: Weight, activation, and KV-cache sparsity for LLM serving, covering magnitude pruning, Wanda, contextual sparsity (Deja Vu), Quest, MLA, and TEAL.
sources:
  - title: CSE 599K, LLM Serving Systems, University of Washington, Spring 2025 (lecture notes)
    type: lecture
  - title: "The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks"
    url: https://arxiv.org/abs/1803.03635
    type: paper
  - title: A Simple and Effective Pruning Approach for Large Language Models (Wanda)
    url: https://arxiv.org/abs/2306.11695
    type: paper
  - title: "Deja Vu: Contextual Sparsity for Efficient LLMs at Inference Time"
    url: https://arxiv.org/abs/2310.17157
    type: paper
  - title: "Quest: Query-Aware Sparsity for Efficient Long-Context LLM Inference"
    url: https://arxiv.org/abs/2406.10774
    type: paper
  - title: DeepSeek-V2 Technical Report (Multi-Head Latent Attention)
    url: https://arxiv.org/abs/2405.04434
    type: paper
  - title: Training-Free Activation Sparsity in Large Language Models (TEAL)
    url: https://arxiv.org/abs/2408.14690
    type: paper
---

## Purpose

This note surveys where sparsity shows up in LLMs (weights, activations, KV cache) and the pruning techniques that exploit each kind. Like [[ml/serving-systems/quantization|Quantization]], sparsity changes the model representation to cut serving cost, and whether the cut turns into actual speedup depends on the hardware bottlenecks described in [[ml/serving-systems/performance-modeling|Performance Modeling]].

These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025, taught by Prof. Baris Kasikci with TA Kan Zhu. Speedup and accuracy numbers are quoted from the cited papers; I have not reproduced them.

## Why pruning works at all

Pruning removes structure from a trained network: individual weights, neurons, attention heads, or whole layers. Alone it degrades accuracy gradually, and pruning followed by fine-tuning holds accuracy much further, occasionally even beating the original model. The wall arrives around 80-90% sparsity even with fine-tuning.

The theoretical grounding starts with Optimal Brain Damage (LeCun et al., 1989), which shows the optimal weights to remove are the ones whose removal least increases the loss, measured through the Hessian. The Hessian is too expensive at scale, so weight magnitude serves as the standard cheap proxy.

The [Lottery Ticket Hypothesis](https://arxiv.org/abs/1803.03635) explains why good sparse subnetworks exist to be found: a large randomly initialized network contains small subnetworks ("winning tickets") that, trained in isolation from their original initialization, match the full model. Over-parametrization amounts to running many initialization lotteries in parallel, and pruning after training uncovers a winner that was there from the start.

## Weight sparsity

Three structural regimes, trading flexibility against implementability:

- Structured: remove whole rows, columns, channels, heads, or layers. Easy to execute efficiently since the dense kernels just shrink.
- Semi-structured: fixed patterns like 2:4 (two nonzero out of every four weights), which NVIDIA Ampere and later accelerate in hardware.
- Unstructured: remove any weight anywhere. Highest quality at a given sparsity, and hard to turn into wall-clock speedup because the access pattern is irregular.

### Wanda

[Wanda](https://arxiv.org/abs/2306.11695) prunes per output, scoring each weight by the product of its magnitude and the L2 norm of its input activation. The activation term matters because LLM activations have a few large-magnitude features (the same outlier phenomenon that drives [[ml/serving-systems/quantization|quantization]] design), so a small weight multiplying a large activation can still be important. No retraining, no weight updates.

```python
def prune(W, X, s):
    metric = W.abs() * X.norm(p=2, dim=0)      # Wanda pruning metric
    _, sorted_idx = torch.sort(metric, dim=1)  # sort per output
    pruned_idx = sorted_idx[:, :int(C_in * s)] # indices to prune
    W.scatter_(dim=1, index=pruned_idx, src=0) # zero out weights
    return W
```

The paper reports accuracy comparable to SparseGPT at 50%, 4:8, and 2:4 sparsity while being much simpler, since SparseGPT performs expensive weight updates during pruning.

### Deja Vu: contextual sparsity

Static pruning commits to one sparsity pattern for all inputs. [Deja Vu](https://arxiv.org/abs/2310.17157) observes that for a given input, only a small input-dependent subset of heads and MLP neurons matters, and predicts that subset on the fly. Small lookahead predictors run ahead of the main computation: the attention input at block $k$ predicts the MLP sparsity at block $k$, and the MLP input predicts attention sparsity at block $k+1$, so prediction overlaps with computation. The paper reports no accuracy drop up to around 75% contextual sparsity and 1.8-6x latency improvement over strong baselines, with hardware-aware sparse kernels doing the realization work.

## KV cache sparsity

Attention weights at inference are extremely sparse in practice; the lecture cites attention matrices over 95% sparse with under 1% of weights carrying meaningful mass. That makes the KV cache (the memory-bound side of decoding, see [[ml/serving-systems/memory-management|Memory Management]]) a natural target.

### Quest

Eviction-based methods drop "unimportant" KV entries based on history, and the failure mode is that a token evicted now may matter for a future query. [Quest](https://arxiv.org/abs/2406.10774) keeps the entire KV cache in memory and instead reduces movement: it tracks per-page metadata (elementwise min and max keys), estimates each page's maximum possible attention score for the current query, and computes attention only over the top-K pages. Query-awareness is the point, since importance is decided per query rather than from history. The paper reports 7.03x self-attention speedup at 32K context with a 2K token budget, with accuracy holding on long-dependency tasks.

### Multi-Head Latent Attention

[DeepSeek-V2's MLA](https://arxiv.org/abs/2405.04434) compresses the KV cache at the architecture level: instead of caching full per-head keys and values, cache one learned low-rank latent vector per token and expand it on the fly. The paper reports a 93.3% KV cache reduction and 5.76x generation throughput improvement over DeepSeek 67B.

| Attention mechanism | KV cache per token | Capability |
|---------------------|--------------------|------------|
| Multi-Head Attention (MHA) | $2n_h d_h l$ | Strong |
| Grouped-Query Attention (GQA) | $2n_g d_h l$ | Moderate |
| Multi-Query Attention (MQA) | $2d_h l$ | Weak |
| MLA | $(d_c + d_h^R)\,l \approx \frac{9}{2}d_h l$ | Stronger than MHA per the paper |

Here $d_c$ is the latent dimension ($4d_h$ in the paper) and $d_h^R$ the decoupled RoPE head dimension ($d_h/2$). RoPE needed the decoupling trick because position-dependent rotations do not commute with the low-rank compression, so MLA keeps a small rotated component concatenated beside the compressed part.

## Activation sparsity

LLM activation distributions concentrate around zero across MLP projections and attention weight matrices. When an activation is (near) zero, the weight columns it multiplies contribute nothing, so the corresponding weight reads can be skipped entirely. In the memory-bound decode regime, skipped weight movement converts directly to latency.

[TEAL](https://arxiv.org/abs/2408.14690) applies this training-free: during decoding, threshold low-magnitude activations to zero and skip loading the associated weight channels. Reported results: around 25% sparsity costs little accuracy for a 1.2-1.3x speedup, and 50% sparsity costs a small degradation for 1.6-1.8x, holding across model sizes from 8B to 70B.

## Making sparsity pay

The recurring lesson is that sparsity only helps when the hardware can skip the zeros. 2:4 patterns get dedicated tensor core support; unstructured sparsity mostly does not pay off; activation and KV sparsity pay off in the memory-bound decode regime because the saved work is memory traffic. Zero-shot methods (Wanda, TEAL) trade a little accuracy for deployment simplicity, and fine-tuning buys the accuracy back when the budget allows. Weight and activation sparsity compose, which is where the aggressive efficiency work is heading.

## Related notes

- [[ml/serving-systems/quantization|Quantization]]
- [[ml/serving-systems/performance-modeling|Performance Modeling]]
- [[ml/serving-systems/memory-management|Memory Management]]
- [[systems/research/sparsity-notes|Faster Causal Self Attention]]
- [[systems/research/padded-encoder-decoder|Accelerating Padded Encoder-Decoder Transformer Models]]
