---
title: The Multikernel, A new OS architecture for scalable multicore systems
category: Systems
tags: os, operating-system, systems, multicore, kernel
description: A review of the paper The Multikernel, A new OS architecture for scalable multicore systems, where the OS is treated as a distributed system.
---

###### [The Multikernel: A new OS architecture for scalable multicore systems](https://people.inf.ethz.ch/troscoe/pubs/sosp09-barrelfish.pdf)

---

### What is the Problem?

Scaling to varying loads and demands on multicore systems is difficult with traditional OS architectures. Optimizations tend to be specific to not only a particular workload, but also a particular choice of hardware.

In particular, traditional kernels are littered with shared state (e.g. global data structures in shared memory) that can lead to bottlenecks and unforeseen interactions between components. Modern systems being multicore makes this a real problem for scalability that adapts to all varieties of workloads.


### Summary

The authors proposed a new OS architecture, the Multikernel, that treats the OS as a distributed system. The key idea is to use message passing for all inter-core communication. It turns out that message passing is a better model for hardware (networked, heterogeneous) than sequentially updating shared state, and it allows for natural pipelining as well.

### Key Insights

- Systems, and even individual cores within a machine, are extremely diverse. It is therefore hard to write optimizations that work on all of them.
- Even on current, cache coherent systems, the hardware is designed to facilitate message passing (e.g. cache coherence protocols).
- Message passing has less overhead than shared memory. Shared state tends to cause cores to wait on cache misses, stalling the pipeline. Message passing on the other hand can be implemented with async RPCs, and is even still faster with synchronous RPCs in some cases.
- Cache coherence overhead typically grows with the number of cores, even becoming a bottleneck at ~80 cores. Modern programmable cores (e.g. NICs, GPUs) are not cache coherent, so there is precedent for non-coherent systems.

### Notable Design Details/Strengths

- Make all inter-core communication explicit
- Make OS structure hardware-neutral
- View state as replicated instead of shared

### Limitations/Weaknesses

-
-

### Summary of Key Results

-
-

### Open Questions

-
-
