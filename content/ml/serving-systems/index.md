---
title: Serving Systems
category: Machine Learning Systems
tags:
  - llm serving
  - inference
  - gpu
  - batching
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Overview of the model-serving notes, focused on inference bottlenecks, GPU behavior, and large-model optimization.
sources:
  - title: "LoRA: Low-Rank Adaptation of Large Language Models"
    url: https://arxiv.org/abs/2106.09685
    type: paper
  - title: "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism"
    url: https://arxiv.org/abs/1909.08053
    type: paper
  - title: CUDA C++ Programming Guide
    url: https://docs.nvidia.com/cuda/cuda-c-programming-guide/
    type: docs
---

## Purpose

These notes are about making large models run well. The recurring questions are simple: where the time goes, where the memory goes, and which optimization changes the real bottleneck. [[ml/serving-systems/gpu-basics|GPU basics]] and [[ml/serving-systems/performance-modeling|performance modeling]] are the best entry points because they make the later optimization notes easier to judge.

The rest of the section clusters around a few themes. [[ml/serving-systems/batching|Batching]], [[ml/serving-systems/parallelism|parallelism]], [[ml/serving-systems/gpu-interconnects|GPU interconnects]], and [[ml/serving-systems/memory-management|memory management]] are system design questions. [[ml/serving-systems/optimizing-gpu-kernels|Optimizing GPU kernels]], [[ml/serving-systems/triton|Triton]], and [[ml/serving-systems/how-to-write-a-fast-kernel|how to write a fast kernel]] are implementation questions. [[ml/serving-systems/transformers|Transformers]] and [[ml/serving-systems/speculative-decoding|speculative decoding]] tie the systems work back to model structure. [[ml/serving-systems/peft-and-preference-optimization|PEFT and preference optimization]] covers the adaptation side: how a base model gets fine-tuned and preference-tuned cheaply, and how the resulting adapters get served.

## Entry points

- Foundations: [[ml/serving-systems/gpu-basics|GPU basics]], [[ml/serving-systems/performance-modeling|performance modeling]], [[ml/serving-systems/roofline-reference|roofline reference]]
- Scheduling and memory: [[ml/serving-systems/batching|batching]], [[ml/serving-systems/memory-management|memory management]], [[ml/serving-systems/parallelism|parallelism]], [[ml/serving-systems/gpu-interconnects|GPU interconnects]]
- Kernel work: [[ml/serving-systems/optimizing-gpu-kernels|optimizing GPU kernels]], [[ml/serving-systems/triton|Triton]], [[ml/serving-systems/how-to-write-a-fast-kernel|how to write a fast kernel]]
- Model-specific techniques: [[ml/serving-systems/transformers|transformers]], [[ml/serving-systems/quantization|quantization]], [[ml/serving-systems/speculative-decoding|speculative decoding]], [[ml/serving-systems/sparsity-and-pruning|sparsity and pruning]]
- Fine-tuning and adaptation: [[ml/serving-systems/peft-and-preference-optimization|PEFT and preference optimization]]
- Distributed training: [[ml/serving-systems/distributed-training|distributed training of LLMs]], [[ml/serving-systems/distributed-ml-runtimes|distributed ML runtime architecture]], [[ml/serving-systems/mixture-of-experts|mixture of experts]]
