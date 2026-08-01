---
title: Parallelism in LLM Serving Systems
aliases:
  - llm-serving-systems/parallelism
category: Machine Learning Systems
tags:
  - parallelism
  - performance
  - throughput
  - latency
  - llm
  - serving-systems
  - machine-learning
date: 2025-05-25
updated: 2026-07-30
status: evergreen
description: Data, pipeline, and tensor parallelism for large models, plus activation memory accounting, sequence parallelism, ZeRO/FSDP sharding, and how to compose them into 3D parallelism.
sources:
  - title: CSE 599K, LLM Serving Systems, University of Washington, Spring 2025 (lecture notes)
    type: lecture
  - title: "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism"
    url: https://arxiv.org/abs/1909.08053
    type: paper
  - title: Reducing Activation Recomputation in Large Transformer Models
    url: https://arxiv.org/abs/2205.05198
    type: paper
  - title: "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models"
    url: https://arxiv.org/abs/1910.02054
    type: paper
  - title: "GPipe: Efficient Training of Giant Neural Networks using Pipeline Parallelism"
    url: https://arxiv.org/abs/1811.06965
    type: paper
---

## Purpose

This note lays out the three main parallelism strategies (data, pipeline, tensor), the memory accounting that motivates them, and how they compose. Parallel execution becomes necessary when the model or KV cache exceeds one device; compare the [[ml/serving-systems/memory-management|memory constraints]] and the routing-specific case in [[ml/serving-systems/mixture-of-experts|Mixture of Experts]].

These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025, taught by Prof. Baris Kasikci with TA Kan Zhu.

## Why one GPU stops being enough

Single-GPU performance keeps improving through number formats (FP32 to FP16 to INT8), specialized instructions (DP4A, HMMA, IMMA), process nodes (28nm down to 5nm), and sparsity support, and it is still fundamentally limited. Model sizes grew faster: ELMo at 94M, GPT-2 at 1.5B, GPT-3 at 175B, MT-NLG at 530B. A single GPU cannot hold the weights of models at that scale, let alone the activations and optimizer state during training.

The interconnect hierarchy determines what distribution costs. Within a node, NVLink 3.0 moves 600 GB/s while PCIe 4.0 moves 32 GB/s. Between nodes, InfiniBand HDR moves about 25 GB/s. Bandwidth drops by more than an order of magnitude at the node boundary, and every parallelism decision below is downstream of that fact.

## Collective communication primitives

Four operations cover almost everything:

- AllReduce: every device ends with the elementwise reduction of all devices' data.
- Broadcast: one device's data goes to all others.
- AllGather: every device ends with the concatenation of all devices' data.
- ReduceScatter: reduction followed by scattering shards.

AllReduce decomposes into ReduceScatter followed by AllGather, and that decomposition is bandwidth-optimal, which is why it shows up repeatedly in the analysis below.

## What state has to live somewhere

Training holds model parameters, gradients, activations from the forward pass, and optimizer state (momentum, variance). Serving holds parameters, activations, and the KV cache. Each parallelism strategy shards a different subset.

## Data parallelism

Each GPU holds a full model copy and processes a slice of the batch; gradients are aggregated after the backward pass. The centralized implementation ships gradients to a parameter server that broadcasts updated weights, and the server becomes both a bandwidth bottleneck and a single point of failure. The decentralized implementation aggregates peer-to-peer with AllReduce (ring, tree, or ReduceScatter + AllGather).

Data parallelism scales batch size and nothing else. Every GPU still stores the full parameters, gradients, and optimizer state, so it cannot help once the model itself outgrows a device.

## Pipeline parallelism

Split the model by layers into stages, one stage per GPU. Forward activations flow left to right, backward gradients right to left, and only activations cross stage boundaries, point to point.

A naive schedule leaves most stages idle most of the time. [GPipe](https://arxiv.org/abs/1811.06965) splits the batch into $m$ microbatches so stages overlap, at the cost of holding more in-flight activations. The bubble fraction is $\frac{p-1}{m}$ for $p$ stages, so more microbatches shrink the idle time. The 1F1B schedule alternates one forward and one backward per stage during steady state (warm-up, alternate, drain), keeping the pipe full with less activation memory. Zero Bubble Pipeline ([Qi et al.](https://arxiv.org/abs/2401.10241)) goes further by splitting the backward pass into activation-gradient work (needed immediately by the previous stage) and weight-gradient work (deferrable), and scheduling the deferrable half into what would have been bubble time.

Pipeline parallelism shards the model cheaply in communication terms, but it is batch-size sensitive: small batches mean few microbatches mean big bubbles.

## Tensor parallelism

Split within layers instead of across them, following [Megatron-LM](https://arxiv.org/abs/1909.08053). For an MLP block $Z = \text{Dropout}(\text{GeLU}(XA)B)$, split $A$ by columns so each GPU computes $Y_i = \text{GeLU}(XA_i)$ with no communication, then split $B$ by rows so each GPU computes $Z_i = Y_i B_i$, and one AllReduce forms $Z = \sum Z_i$. Attention splits by heads: each GPU processes a subset of heads and an AllReduce combines the output projection. Each layer ends up with an AllReduce in the forward pass and a mirrored one in the backward pass.

The tradeoff against pipeline parallelism is communication volume. Pipeline stages exchange activations once per boundary, about $bsh$ bytes. Tensor parallelism moves roughly $8bsh$ per layer through AllReduces (lecture estimate), so it wants NVLink-class links and is usually confined within a node. In exchange there are no bubbles and no batch size requirement, so utilization stays high even at small batches.

## Activation memory and how to shrink it

Per layer, activations for a transformer take approximately

$$\text{Memory per layer} = sbh\left(34 + 5\frac{as}{h}\right)$$

bytes, where $s$ is sequence length, $b$ batch size, $h$ hidden size, and $a$ the number of attention heads (derivation in [Korthikanti et al.](https://arxiv.org/abs/2205.05198)). Two levers reduce it:

Checkpointing stores only layer inputs and recomputes intermediate activations during the backward pass, trading roughly a third of throughput for a large memory saving, which often buys back a bigger batch.

Tensor parallelism with $t$ ways shards the big matrix multiply activations but leaves the pointwise parts unsharded:

$$sbh\left(10 + \frac{24}{t} + 5\frac{as}{ht}\right)$$

The residual $10sbh$ is LayerNorm ($4sbh$), dropout ($2sbh$), and stored layer inputs ($4sbh$). Those are pointwise along the sequence, so sequence parallelism splits them along the sequence dimension across the same $t$ GPUs, with an AllGather to reassemble before the MLP. That removes the unsharded term entirely:

| Configuration     | Activations per layer                     |
| ----------------- | ----------------------------------------- |
| No parallelism    | $sbh(34 + 5\frac{as}{h})$                 |
| Tensor only       | $sbh(10 + \frac{24}{t} + 5\frac{as}{ht})$ |
| Tensor + sequence | $sbh(\frac{34}{t} + 5\frac{as}{ht})$      |

With tensor plus sequence parallelism, activation memory finally scales linearly in device count.

## ZeRO and FSDP

Data parallelism's redundancy is the target of [ZeRO](https://arxiv.org/abs/1910.02054). For $\Psi$ parameters trained with Adam in mixed precision, each GPU holds $2\Psi$ bytes of FP16 params, $2\Psi$ of FP16 gradients, and $K\Psi$ of optimizer state ($K = 12$: FP32 master params, momentum, and variance at $4\Psi$ each). ZeRO shards this state across the $N_d$ data-parallel workers in three stages: stage 1 shards optimizer state, stage 2 adds gradients, stage 3 adds the parameters themselves, bringing per-GPU memory to $\frac{(2 + 2 + K)\Psi}{N_d}$. PyTorch's Fully Sharded Data Parallel (FSDP) implements this idea.

## Composing: 3D parallelism

Deployment proceeds in two phases. First make the model fit: tensor parallelism within a node (where NVLink can afford the AllReduce traffic), pipeline parallelism across nodes (where only point-to-point activations cross the slow links). Then scale compute by adding data parallelism across groups, with gradient accumulation to amortize communication.

A cluster of 8-GPU nodes typically runs 8-way tensor parallel inside each node, pipeline parallel across nodes, and data parallel across node groups. The batch must be large enough to keep the pipeline bubble small, tensor parallelism should not be split so wide that per-GPU GEMMs get thin, and the right configuration ultimately depends on the model shape and the bandwidth topology.

## Related notes

- [[ml/serving-systems/memory-management|Memory Management]]
- [[ml/serving-systems/mixture-of-experts|Mixture of Experts]]
- [[ml/serving-systems/performance-modeling|Performance Modeling]]
- [[hardware/computer-architecture/simd-vectors-gpus-accelerators|From SIMD to SIMT: Vectors, GPUs, and Accelerators]]
