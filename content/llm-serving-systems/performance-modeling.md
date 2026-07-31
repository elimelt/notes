---
title: Performance Modeling for LLM Serving Systems
category: Machine Learning Systems
tags:
  - performance
  - roofline
  - arithmetic-intensity
  - machine-learning
date: 2025-05-10
updated: 2026-07-30
status: needs-review
description: The roofline model applied to LLM serving, critical operational intensity on the H100, and memory/compute/network execution time models that show serving is mostly compute-bound.
sources:
  - title: CSE 599K, LLM Serving Systems, University of Washington, Spring 2025 (lecture notes)
    type: lecture
  - title: "Roofline: An Insightful Visual Performance Model for Multicore Architectures (Williams, Waterman, Patterson, CACM 2009)"
    url: https://dl.acm.org/doi/10.1145/1498765.1498785
    type: paper
  - title: How to Scale Your Model, All About Rooflines
    url: https://jax-ml.github.io/scaling-book/roofline/
    type: book
---

## Purpose

This note builds a performance model for LLM serving: the roofline model for single-kernel analysis, then whole-system execution time models for memory, compute, and network. A compact version of the core model lives in the [[llm-serving-systems/roofline-reference|Roofline reference]]. The same model guides [[llm-serving-systems/optimizing-gpu-kernels|kernel optimization]] and system-level choices such as [[llm-serving-systems/batching|batching]].

These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025, taught by Prof. Baris Kasikci with TA Kan Zhu. The framework throughput comparison near the end is quoted from lecture slides without the underlying benchmark configuration, which is why this note carries needs-review status.

## The roofline model

The [roofline model](https://dl.acm.org/doi/10.1145/1498765.1498785) characterizes a kernel by its operational intensity:

$$\text{Operational Intensity} = \frac{\text{FLOPs performed}}{\text{Bytes moved}}$$

Plot intensity against achievable FLOPs/s and the hardware traces out a roofline: a slanted region where performance is capped by memory bandwidth times intensity (memory bound), and a flat region capped by peak compute (compute bound). A kernel below the ridge point wastes compute waiting on memory; a kernel past it can only improve by doing less math or using faster math.

The ridge sits at the critical intensity, where the workload's demand matches the hardware's ratio:

$$\frac{\text{Computation FLOPs}}{\text{Communication Bytes}} = \frac{\text{Accelerator FLOPs/s}}{\text{Bandwidth Bytes/s}}$$

Above that ratio the kernel is compute bound, below it memory bound. To move up in the memory-bound region you improve data movement (coalescing, tiling, prefetching, NUMA-aware placement); in the compute-bound region you improve math throughput (multithreading, ILP, SIMD, tensor cores).

## H100 numbers

Peak FP16 tensor throughput is about 1000 TFLOPs dense (2000 with 2:4 structured sparsity) and memory bandwidth about 3000 GB/s, so the critical intensity is

$$\frac{1000 \times 10^{12}}{3000 \times 10^9} \approx 333 \text{ FLOPs/Byte}$$

Any kernel below 333 FLOPs per byte moved is memory bound on this part.

### Dot product

An FP32 dot product of length $N$ does $2N$ FLOPs ($N$ multiplies, $N$ adds) and moves $8N$ bytes in plus 4 bytes out:

$$\text{OI} = \frac{2N}{8N + 4} \approx \frac{1}{4}$$

Hopelessly memory bound, three orders of magnitude below critical intensity. (Counting FP16 data instead shifts the constant, and the conclusion survives.)

### Matrix multiplication

For FP16 matrices $[M,N] \times [N,K] \rightarrow [M,K]$: reads are $2MN + 2NK$ bytes, writes $2MK$ bytes, compute $2MNK$ FLOPs.

$$\text{OI} = \frac{2MNK}{2MN + 2NK + 2MK} \approx M \quad \text{when } N, K \gg M$$

For the batched GEMMs in LLM serving, $M$ is the batch dimension, so matmul on the H100 goes compute bound around batch 333. This single number drives the batching pressure throughout [[llm-serving-systems/batching|Batching]].

One caveat on treating "bandwidth" as one number: clusters are hierarchical. HBM moves TB/s while the network moves 25 GB/s (200 Gb/s), so the same roofline logic applies again at the cluster level with a different denominator, a NUMA effect at rack scale.

## System-level model

Notation for the whole-system estimates:

- Hardware: $N_{GPU}$ GPUs, aggregate memory bandwidth $MemBW$, memory capacity $GPU_{mem}$, compute $Compute$, interconnect bandwidth $NetBW$.
- Model: hidden dim $D_{model}$, layers $L$, parameters $P_{model}$, GQA group size $R_{GQA}$, dtype size $S_{type}$.
- Workload: average prefill length $p$, decode length $d$, dense batch size $B_{dense}$. Per-request throughput is $\frac{\text{Throughput}_{total}}{p+d}$ and decode throughput is $d\frac{\text{Throughput}_{total}}{p+d}$.

Three execution time estimates for one iteration:

Memory: one iteration streams essentially all of GPU memory (weights, KV cache) once, so

$$T_{memory} = \frac{GPU_{mem}}{MemBW}$$

Compute: dense operations cost 2 FLOPs per parameter per token, so

$$T_{compute} = \frac{2B_{dense}P_{model}}{Compute}$$

Network: with tensor parallelism, each layer runs about 4 AllGather-equivalents over activations of shape $B_{dense} \times D_{model}$ (an AllReduce counts as roughly two AllGathers), each taking $N_{GPU}-1$ hops:

$$T_{net} = \frac{4(N_{GPU} - 1)\,D_{model}\,B_{dense}\,S_{type}\,L}{NetBW}$$

## What the ratios say

Network versus compute:

$$\frac{T_{net}}{T_{compute}} = 2(N_{GPU} - 1)\frac{D_{model}L}{P_{model}} \cdot \frac{S_{type} \cdot Compute}{NetBW}$$

Since $P_{model}$ grows like $D_{model}^2 L$ while the numerator grows like $D_{model} L$, bigger models push this ratio down. Plugging in typical model and hardware numbers, serving comes out compute bound rather than network bound.

Memory versus compute:

$$\frac{T_{memory}}{T_{compute}} = \frac{Compute \cdot GPU_{mem}}{MemBW \cdot 2B_{dense}P_{model}}$$

GQA shrinks the KV cache and lets $B_{dense}$ grow (see [[llm-serving-systems/transformers|Transformers]]), which favors compute-boundedness. Growing model sizes do the same. Batches dominated by long decodes pull the other way, since decode attention reads KV without matching dense FLOPs. On balance, at realistic batch sizes, serving is compute bound here too.

## Optimal throughput and the gap in practice

If compute is the binding constraint, peak throughput per GPU is

$$\text{Throughput} = \frac{B_{dense}}{T_{compute}} = \frac{Compute}{2P_{model}}$$

The lecture's example puts LLaMA 70B on an A100 at 1857 tokens/s/GPU by this bound, and quotes measured framework throughput far below it: vLLM around 494-552 tokens/s, DeepSpeed-FastGen 372-513, TensorRT-LLM 636-817. The slides do not record the benchmark setup (input/output lengths, hardware count, parallelism config), so treat these as one snapshot rather than a ranking. The robust conclusion is the size of the gap: frameworks at the time achieved roughly a quarter to half of the compute-bound ceiling, so keeping tensor cores busy is the central engineering problem in serving.

## Related notes

- [[llm-serving-systems/roofline-reference|Roofline reference]]
- [[llm-serving-systems/batching|Batching]]
- [[llm-serving-systems/optimizing-gpu-kernels|Optimizing GPU Kernels]]
- [[llm-serving-systems/parallelism|Parallelism]]
