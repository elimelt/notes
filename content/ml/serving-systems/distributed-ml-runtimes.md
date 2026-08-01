---
title: Distributed Machine Learning Runtime Architecture
aliases:
  - llm-serving-systems/distributed-ml-runtimes
category: Machine Learning Systems
tags:
  - distributed-training
  - parameter-server
  - dataflow
  - collectives
  - machine-learning
date: 2026-08-01
updated: 2026-08-01
status: draft
description: Runtime abstractions underlying modern LLM training frameworks -- parameter servers, dataflow-graph runtimes with device placement, and collective-based runtimes -- and how they compare on communication pattern, staleness, and fault recovery.
sources:
  - title: "Large Scale Distributed Deep Networks (DistBelief)"
    url: https://papers.neurips.cc/paper/4687-large-scale-distributed-deep-networks.pdf
    type: paper
  - title: "TensorFlow: A System for Large-Scale Machine Learning"
    url: https://arxiv.org/abs/1605.08695
    type: paper
  - title: "Horovod: fast and easy distributed deep learning in TensorFlow"
    url: https://arxiv.org/abs/1802.05799
    type: paper
  - title: "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism"
    url: https://arxiv.org/abs/1909.08053
    type: paper
---

## Purpose

Modern LLM training frameworks (Megatron-LM, DeepSpeed, PyTorch FSDP) sit on top of runtime abstractions that predate them by a decade. This note explains those abstractions: parameter servers, dataflow-graph execution with device placement, and collective-based runtimes, why the field moved from the first two toward the third for dense-model training, and how the underlying ideas still show up (parameter servers for embeddings, dataflow graphs for compilers) inside systems described in [[ml/serving-systems/distributed-training|Distributed Training of Large Language Models]].

## Parameter servers

[DistBelief](https://papers.neurips.cc/paper/4687-large-scale-distributed-deep-networks.pdf) (Dean et al., NeurIPS 2012) introduced the parameter server pattern for training with "tens of thousands of CPU cores": a set of server machines holds the authoritative copy of the model's parameters, and worker machines pull parameters, compute gradients on a data shard, and push gradient updates back.

**Synchronous** parameter-server training waits for all workers to report gradients each step before updating, equivalent in effect to a centralized AllReduce; it makes progress deterministic but ties throughput to the slowest worker. **Asynchronous** training (DistBelief's Downpour SGD) lets workers pull and push whenever ready, with no barrier, so a fast worker can compute several gradients using a parameter version that later workers already made stale. This is **staleness**: a worker's gradient step is applied against parameters that have since moved. DistBelief accepted staleness for throughput and reported successfully training a network 100x larger than prior published models on ImageNet, plus real gains on a production speech model. Bounded-staleness variants sit between the two: allow asynchronous updates but block a worker if it falls more than $k$ versions behind the server's current parameter version, trading some of the throughput gain back for a cap on how stale any single gradient can be.

DistBelief's second algorithm, Sandblaster, generalizes the same server/worker split to batch optimization methods like L-BFGS rather than only SGD, showing the parameter-server abstraction is about *where state lives and how updates flow*, not about a specific optimizer.

The parameter server's structural weakness, inherited by the "centralized" implementation described in [[ml/serving-systems/parallelism|Parallelism]], is that the server set is both a bandwidth bottleneck (every worker's gradients funnel through it) and a single point of failure unless replicated. It scales well when parameters are sparse and updates touch only a slice of them (embedding tables, where each worker only pulls/pushes the rows it needs), which is why parameter servers persisted in recommendation-system training long after dense-model training moved to collectives.

## Dataflow-graph runtimes

[TensorFlow](https://arxiv.org/abs/1605.08695) (Abadi et al., 2016) generalizes further: represent the whole computation, not just parameter updates, as a dataflow graph of operators and tensors, and let the runtime place graph nodes onto whichever devices (CPU, GPU, TPU) are available, inserting communication ops automatically at placement boundaries. The paper is explicit that this is a reaction to the parameter-server model: "whereas in previous 'parameter server' designs the management of shared state is built into the system, TensorFlow enables developers to experiment with novel optimizations and training algorithms." Shared state (variables) becomes just another node in the graph rather than a privileged server-side abstraction, so a user can express a parameter server, an AllReduce-style scheme, or something else entirely, all as graph structure.

Device placement is a real scheduling problem: given a graph, a set of heterogeneous devices, and per-op cost/communication estimates, decide which device runs which op to minimize execution time or communication volume. TensorFlow's stock placer used greedy heuristics; the flexibility to express *any* placement policy is the point, not a specific optimal solution. This flexibility comes with overhead: building and dispatching a general dataflow graph on every device is more machinery than a fixed collective pattern needs, which is part of why later systems specialized back down.

## Collective-based runtimes

[Horovod](https://arxiv.org/abs/1802.05799) (Sergeev and Del Balso, 2018) narrows the abstraction deliberately: instead of general dataflow placement, wrap each worker's existing single-GPU training script with a thin library that inserts a ring-AllReduce over gradients each step, using NCCL for the actual communication. The motivation stated in the paper is that TensorFlow's stock distributed mode required substantial code changes and incurred non-negligible communication overhead; Horovod's pitch is closer to "keep your single-GPU code, add one line for gradient synchronization." Ring AllReduce splits each device's gradient tensor into $N$ chunks (for $N$ devices) and passes chunks around a ring in two phases, ReduceScatter then AllGather, so total data moved per device is independent of $N$ and each device only ever talks to its two ring neighbors: this is the same AllReduce = ReduceScatter + AllGather decomposition used throughout [[ml/serving-systems/parallelism|Parallelism]].

Megatron-LM ([Shoeybi et al. 2019](https://arxiv.org/abs/1909.08053)) builds directly on this collective-based model rather than either parameter servers or general dataflow placement: tensor parallelism inserts a handful of AllReduce calls per transformer layer directly into native PyTorch code, "with the insertion of a few communication operations," and pipeline parallelism moves activations point-to-point between adjacent stages. Both are fixed, hand-chosen communication patterns rather than a placer's decision, which is exactly the tradeoff collective-based runtimes make against TensorFlow-style generality: less flexibility, far less per-op dispatch overhead, and a communication pattern that a systems engineer can reason about and tune directly.

## Comparing the three for dense model training

| Property | Parameter server | Dataflow graph (TensorFlow) | Collective-based (Horovod, Megatron) |
| --- | --- | --- | --- |
| Where shared state lives | dedicated server processes | graph node like any other | replicated across workers, synced via collective |
| Communication pattern | worker <-> server, star topology | placer-chosen, can be anything | fixed collective (ring/tree AllReduce), peer-to-peer |
| Bottleneck risk | server bandwidth / single point of failure | dispatch overhead, placement quality | none structural; bounded by slowest peer at the barrier |
| Staleness options | sync, async, bounded-staleness | whatever the graph encodes | effectively synchronous (barrier at each AllReduce) |
| Best fit | sparse parameters (embeddings) | heterogeneous devices, research flexibility | dense, homogeneous GPU clusters |

Dense transformer training is exactly the "dense, homogeneous GPU clusters" cell: every parameter is used and updated on every step, so there's no sparsity for a parameter server to exploit, and the hardware is close to identical across workers, so a fixed collective pattern tuned once (ring topology matched to the physical interconnect) beats a general placer re-deciding on every graph. That is the systems reason Megatron-, DeepSpeed-, and FSDP-style frameworks all converged on collectives rather than either predecessor, and it connects directly to the tensor/pipeline/data parallelism composition in [[ml/serving-systems/distributed-training|Distributed Training of Large Language Models]].

## Checkpointing, restart, and stragglers

The runtime abstraction shapes how fault recovery works. A parameter-server system can often restart a single failed worker without disturbing others, since workers don't coordinate directly; async or bounded-staleness updates already tolerate a worker being briefly unavailable. A collective-based runtime has the opposite property: a synchronous AllReduce requires every participant to show up, so one dead or slow GPU stalls the entire step (the straggler problem, treated generally in [[systems/scheduling/4-cluster-and-datacenter/stragglers-speculation-and-overload|Stragglers, Speculation, and Overload]]), and a hard failure requires either restarting the whole collective group from the last checkpoint or a resize-and-continue mechanism that reconstructs the process group with one fewer (or a replacement) member. This is why long collective-based training runs checkpoint frequently and treat the restart path as a first-class part of the system rather than an edge case, a tradeoff also discussed in [[ml/serving-systems/distributed-training|Distributed Training of Large Language Models]].

## An analytic trace of one step

For $N$ workers running collective-based synchronous data parallelism with per-worker compute time $T_{compute}$ and ring-AllReduce time $T_{comm} \approx \frac{2(N-1)}{N} \cdot \frac{|\theta|}{BW}$ for gradient tensor size $|\theta|$ bytes and per-link bandwidth $BW$ (the standard ring-AllReduce cost model, matching the AllReduce decomposition in [[ml/serving-systems/parallelism|Parallelism]]):

```text
worker 0: [--- compute T_c ---][-- allreduce chunk exchange (ring) --][optimizer step]
worker 1: [--- compute T_c ---][-- allreduce chunk exchange (ring) --][optimizer step]
...
worker N-1: [-compute T_c (straggler: 1.3x)-][-- waits, then allreduce --][optimizer step]
```

If every worker's compute time is identical, step time is $T_{compute} + T_{comm}$ regardless of $N$ (ring AllReduce's defining property: communication volume per device does not grow with worker count). If one worker runs at $1.3\times T_{compute}$, every other worker idles at the AllReduce barrier waiting for it, and step time becomes $1.3\,T_{compute} + T_{comm}$: the straggler's slowdown is paid by the entire cluster, not just that worker. This labeled analytic trace, not a measured benchmark, is the mechanism explanation for why straggler mitigation matters more as $N$ grows: the probability that at least one of $N$ workers is a straggler on a given step increases with $N$ even if each worker's per-step straggler probability is fixed.

## Related notes

- [[ml/serving-systems/parallelism|Parallelism]]
- [[ml/serving-systems/distributed-training|Distributed Training of Large Language Models]]
- [[systems/distributed-systems/index|Distributed Systems]]
- [[systems/distributed-systems/consistency|Consistency Models]]
- [[systems/scheduling/index|Scheduling]]
- [[systems/performance/latency-throughput-and-utilization|Latency, Throughput, and Utilization]]
