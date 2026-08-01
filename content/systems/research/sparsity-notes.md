---
title: Faster Causal Self Attention
aliases:
  - systems-research/sparsity-notes
category: Systems Research
tags:
  - machine-learning
  - attention
  - attention-mechanism
  - transformer
  - flashattention
  - sparse-attention
date: 2025-01-14
updated: 2026-07-30
status: needs-review
description: Reading notes on three sparse attention papers, SCFA, SparseK, and MoA, covering how each one cuts the quadratic cost of attention over long sequences.
sources:
  - title: Faster Causal Attention Over Large Sequences Through Sparse Flash Attention
    url: https://arxiv.org/abs/2306.01160
    type: paper
  - title: "Sparser is Faster and Less is More: Efficient Sparse Attention for Long-Range Transformers"
    url: https://arxiv.org/abs/2406.16747
    type: paper
  - title: "MoA: Mixture of Sparse Attention for Automatic Large Language Model Compression"
    url: https://arxiv.org/abs/2406.14909
    type: paper
---

## Purpose

Reading notes on three papers about making causal self attention cheaper over long sequences. All three attack the same bottleneck, the quadratic cost of attention in sequence length, from different angles. These summaries are second-hand and I have not re-verified every number against the papers, hence the needs-review status.

## Sparse Causal Flash Attention (SCFA)

[Faster Causal Attention Over Large Sequences Through Sparse Flash Attention](https://arxiv.org/abs/2306.01160) (Pagliardini et al., 2023) extends FlashAttention to handle irregular, sparse attention patterns while keeping its computational efficiency. The technical move is modifying FlashAttention to handle non-triangular causal masks, which unlocks flexible attention patterns while keeping the memory and compute benefits of the original kernel.

Two applications drive the paper. Query/key (QK) dropping selectively removes certain query and key pairs. Hash-based attention uses locality-sensitive hashing to group similar queries and keys together.

Reported results: 2.0x training speedup at 8,192 tokens and 3.3x at 16,384 tokens, with perplexity comparable to standard attention, beating Reformer on both speed and accuracy. The computation stays exact rather than approximate, sparsity patterns can be dynamic rather than static, and there is no complexity overhead on top of regular FlashAttention. The benefits grow with sequence length.

## SparseK Attention

[Sparser is Faster and Less is More](https://arxiv.org/abs/2406.16747) introduces SparseK Attention, which uses a scoring network and a differentiable top-k mask operator to dynamically select a constant number of important key-value pairs for each query. The differentiability matters because it makes the selection trainable end to end.

That constant-size selection gives linear time complexity and a constant memory footprint during generation, and the mechanism stays efficient for both training and inference. It integrates with sliding window attention, works with pre-trained LLMs through fine-tuning, and uses an IO-aware implementation built on FlashAttention. The paper reports better perplexity than baseline sparse attention methods while matching or exceeding full attention quality.

Limits the authors call out: validation only reaches modest model sizes and context lengths due to compute constraints, only [[ml/deep-learning/decoder-only-transformers|decoder-only architectures]] and text tasks are tested, and short sequences pay some overhead.

## MoA (Mixture of Sparse Attention)

[MoA: Mixture of Sparse Attention for Automatic Large Language Model Compression](https://arxiv.org/abs/2406.14909) starts from the observation that existing sparse attention methods apply one uniform pattern across all attention heads, even though different heads serve different purposes. Uniform patterns also fail to extend the effective context length beyond their attention span.

MoA automatically discovers heterogeneous sparse attention patterns tailored to each head and layer. It profiles the influence of each attention position on model predictions with gradient-based analysis, builds a search space of attention patterns and elastic scaling rules that let spans grow differently with input length, and optimizes over that space with calibration datasets containing long-range dependencies.

Reported results: 3.9x longer effective context length than baseline methods at the same average attention span, retrieval accuracy improved 1.5-7.1x over uniform sparse baselines, maximum benchmark performance drop reduced from the 9-36% range to within 5%, 6.6-8.2x throughput over FlashAttention2, and 1.2-1.4x lower GPU memory usage. Performance degrades under extremely low density constraints, and the authors leave dynamic attention patterns and non-linear elastic rules to future work.

## Related notes

- [[systems/research/padded-encoder-decoder|Accelerating Padded Encoder-Decoder Transformer Models]]
- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
- [[deep-learning/decoder-only-transformer-on-wikitext-2|Decoder-Only Transformer on WikiText-2]]
- [[ml/serving-systems/transformers|Transformer Architecture and Implementation]]
- [[ml/serving-systems/inf-llm|InfLLM: Training-Free Long-Context Extrapolation for LLMs]]
- [[ml/deep-learning/encoder-decoder-transformers|Encoder-Decoder Transformers]]
- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
- [[deep-learning/decoder-only-transformer-on-wikitext-2|Decoder-Only Transformer on WikiText-2]]
- [[ml/serving-systems/transformers|Transformer Architecture and Implementation]]
- [[ml/serving-systems/inf-llm|InfLLM: Training-Free Long-Context Extrapolation]]
- [[ml/deep-learning/encoder-decoder-transformers|Encoder-Decoder Transformers]]
