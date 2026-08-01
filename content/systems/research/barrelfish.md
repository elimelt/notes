---
title: The Multikernel, A new OS architecture for scalable multicore systems
aliases:
  - systems-research/barrelfish
category: Systems Research
tags:
  - os
  - operating-system
  - systems
  - multicore
  - kernel
  - paper-notes
date: 2025-02-12
updated: 2026-07-30
status: incomplete
description: Review notes on the Multikernel (Barrelfish) paper, which structures the OS as a distributed system of per-core kernels that communicate by message passing.
sources:
  - title: "The Multikernel: A new OS architecture for scalable multicore systems (SOSP 2009)"
    url: https://people.inf.ethz.ch/troscoe/pubs/sosp09-barrelfish.pdf
    type: paper
---

## Purpose

Reading notes on the Multikernel paper. The note records the problem the paper attacks, the core design move, and the parts of the argument I found convincing. The results and limitations sections of my original review never got filled in, so treat this as a partial review.

## Citation

- [The Multikernel: A new OS architecture for scalable multicore systems](https://people.inf.ethz.ch/troscoe/pubs/sosp09-barrelfish.pdf), Baumann et al., SOSP 2009.

## Problem

Traditional OS architectures scale poorly on multicore hardware. Optimizations tend to be specific to a particular workload and a particular choice of hardware, so they age badly as machines change. Worse, traditional kernels are littered with shared state, global data structures in shared memory that cause bottlenecks and unforeseen interactions between components. As core counts grow and hardware gets more heterogeneous, this shared-state design stops scaling.

## Main idea

Treat the machine as a network of independent cores and structure the OS as a distributed system. Each core runs its own OS instance, and all inter-core communication happens through explicit message passing rather than shared memory. The paper argues this matches what the hardware actually looks like (networked, heterogeneous) better than the sequential shared-state model, and it lets communication pipeline naturally.

## Mechanism

The design rests on three principles stated in the paper:

1. Make all inter-core communication explicit.
2. Make the OS structure hardware-neutral.
3. View state as replicated instead of shared.

Instead of protecting a global structure with locks, each core keeps a local replica and the OS keeps replicas consistent by exchanging messages. Sharing becomes an optimization you apply where the hardware makes it cheap, rather than the default.

## Why message passing over shared memory

## Related notes

- [[systems/operating-systems/lecture-notes/components|Components of an OS]]
- [[systems/operating-systems/v1-kernels-and-processes/1-introductions|What Is an Operating System?]]

The paper backs this reframing with a few observations:

- Machines, and even individual cores within a machine, are diverse. Hardware-specific shared-memory optimizations do not transfer across them.
- Even on cache-coherent systems, the hardware already behaves like a message-passing system underneath. Cache coherence protocols move messages between caches.
- Shared state makes cores stall on cache misses while they wait for lines to bounce between cores. Message passing can be implemented with async RPC, so a core can keep doing useful work while a request is in flight.
- Coherence traffic grows with core count, and the paper points to hardware that already gives up on coherence. Programmable devices like NICs and GPUs are not cache coherent with the host, so there is precedent for building against non-coherent hardware.

## Evidence

The paper builds Barrelfish, a multikernel for x86 multicore machines, and compares message-based coordination against shared-memory alternatives. The evaluation I remember best is the unmap (TLB shootdown) case study, where the message-based protocol scales better with core count than the IPI-based approach used by mainstream kernels. I did not record the concrete numbers in my original review, so go back to section 5 of the paper for them.

## Assumptions and limits

The argument assumes messages between cores are cheap relative to the coherence traffic they replace, which the paper demonstrates on the cache-coherent x86 machines it had. The projected payoff on large non-coherent machines is extrapolation, since machines like that were not broadly available at the time. I never wrote down my own list of weaknesses, which is the main gap in this review.

## Sources

- [The Multikernel: A new OS architecture for scalable multicore systems](https://people.inf.ethz.ch/troscoe/pubs/sosp09-barrelfish.pdf)

## Related notes

- [[systems/research/exokernel|Exokernel]]
- [[systems/research/xen|Xen and the Art of Virtualization]]
- [[systems/research/locality-principle|The Locality Principle]]
