---
title: "InfLLM: Training-Free Long-Context Extrapolation for LLMs with an Efficient Context Memory"
aliases:
  - llm-serving-systems/inf-llm
category: Machine Learning Systems
tags:
  - llm
  - paper-notes
  - long-context
  - memory
  - lru
  - machine-learning
date: 2025-04-14
updated: 2026-07-30
status: evergreen
description: Paper notes on InfLLM, which extends short-context LLMs to very long sequences without training by pairing sliding window attention with a block-level external context memory.
sources:
  - title: "InfLLM: Training-Free Long-Context Extrapolation for LLMs with an Efficient Context Memory"
    url: https://arxiv.org/abs/2402.04617
    type: paper
  - title: InfLLM reference implementation (thunlp)
    url: https://github.com/thunlp/InfLLM
    type: code
---

## Purpose

Record of what InfLLM does, why it works without training, and where it breaks. InfLLM's external context store addresses the same long-context KV-cache pressure discussed in [[ml/serving-systems/memory-management|Memory Management in LLM Serving Systems]].

## Citation

- [InfLLM: Training-Free Long-Context Extrapolation for LLMs with an Efficient Context Memory](https://arxiv.org/abs/2402.04617) (Xiao et al., 2024). A copy of the paper lives locally at [papers/inf-llm.pdf](./papers/inf-llm.pdf), and the reference implementation is at [thunlp/InfLLM](https://github.com/thunlp/InfLLM).

## Problem

LLMs are pre-trained on sequences capped at a few thousand tokens, which limits their usefulness for agents, streaming inputs, and other workloads that need much longer contexts. The standard fix is continual pre-training on longer sequences, which costs a lot of compute and can degrade short-context performance. The paper asks whether an LLM trained on short sequences can process sequences far beyond its training window with no additional training and no architecture change.

## Main idea

Keep sliding window attention for the local context, and bolt on an external context memory for everything that falls outside the window. Distant key-value vectors are grouped into blocks, and for each attention step the model retrieves only the few most relevant blocks and attends over them alongside the local window. The claim behind the design is that LLMs already have an underused ability to reason over distant context; what they lack is a mechanism that surfaces the relevant pieces without drowning attention in irrelevant tokens.

## Mechanism

Three design details carry the method:

- Block-level memory. Past KV vectors are organized into fixed-size blocks, and only the most semantically significant tokens within each block represent it during relevance scoring. That keeps lookup cost low relative to scoring every past token.
- Dynamic offloading. Most memory blocks live in CPU memory. Frequently accessed blocks are cached on GPU with an LRU policy, which is what lets sequences up to 1M tokens run on modest GPU resources.
- No training anywhere. The retrieval scores reuse the model's existing attention representations, so the method applies to any off-the-shelf LLM.

## Evidence

The paper evaluates on long-context benchmarks against both training-free baselines and models continually trained on long sequences. Findings, per the paper:

- Base models pre-trained on 8K or 32K contexts match or exceed continually trained long-context models on question answering, summarization, and retrieval tasks.
- Retrieval accuracy holds up to 1,024K-token sequences.
- GPU memory use and inference time drop substantially compared to full attention or continually trained long-context models, making single-GPU long-context inference practical.
- On context retrieval tasks it outperforms retrieval-augmented generation setups without training a retriever.

## Assumptions and limits

The CPU side pays for what the GPU saves: storing the full KV history in host memory gets demanding at extreme lengths. Inference speed still has headroom, since block retrieval adds work per step. And the method inherits the base model's weaknesses; when the base model is bad at filtering noise or representing context, InfLLM's retrieval is built on those same representations, which shows up in some tasks with weaker base models.

## Open questions

How much would lightweight training of the block segmentation and representative-token selection improve retrieval relevance? And can this compose with KV compression techniques (like the ones covered in [[ml/serving-systems/sparsity-and-pruning|Sparsity and Pruning]]) to shrink both the memory footprint and the retrieval cost at once?

## Related notes

- [[ml/serving-systems/memory-management|Memory Management in LLM Serving Systems]]
- [[ml/serving-systems/sparsity-and-pruning|Sparsity and Pruning]]
- [[systems/research/sparsity-notes|Faster Causal Self Attention]]
- [[ml/nlp/prompting|Prompting Language Models]]
