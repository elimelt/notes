---
title: Xen and the Art of Virtualization
aliases:
  - systems-research/xen
category: Systems Research
tags:
  - virtualization
  - hypervisor
  - xen
  - operating-system
  - systems
  - paper-notes
date: 2025-01-26
updated: 2026-07-30
status: evergreen
description: Review notes on the Xen paper, covering paravirtualization, why hypervisor-aware guests beat full emulation, and the costs of requiring guest modification.
sources:
  - title: Xen and the Art of Virtualization (SOSP 2003)
    url: https://www.cl.cam.ac.uk/research/srg/netos/papers/2003-xensosp.pdf
    type: paper
---

## Purpose

Reading notes on the Xen paper. The note records what paravirtualization buys over full virtualization, the design details that made porting guests tractable, and what the approach costs.

## Citation

- [Xen and the Art of Virtualization](https://www.cl.cam.ac.uk/research/srg/netos/papers/2003-xensosp.pdf), Barham et al., SOSP 2003.

## Problem

Full virtualization emulates the underlying hardware completely so an unmodified guest OS can run on it. That approach is slow because of emulation overhead, and it prevents guest OSes from accessing hardware features of the host that would let them behave correctly and efficiently, like real time sources.

## Main idea

Xen is a hypervisor that runs multiple OSes on the same hardware through **paravirtualization**. Guest OSes are modified to be aware of the hypervisor and make calls to it for access to hardware features. Xen implements efficient mechanisms for memory management, scheduling, event delivery, and I/O inside the hypervisor, and delegates resources to guests through them. The paper demonstrates the resulting performance on **XenoLinux**, their port of Linux.

## Key insights

Guests benefit from knowing they are virtualized, both for correctness (clocks, paging) and performance (fast handlers). Paravirtualization delivers a large performance improvement over full virtualization in exchange for modifying the guest, and Xen keeps the modification small by exposing a simple, clean interface that ports to new OSes without touching much guest source.

Because emulation is unnecessary in most cases, overhead stays low for both latency and throughput across most operations.

## Evidence

The paper's evaluation shows performance close to native Linux for many workloads, and where it falls short of native it still beats full virtualization by a wide margin. Many guest OSes run concurrently with little memory footprint attributable to the hypervisor.

## Assumptions and limits

Guest OSes still need modification, which raises the cost of adoption for any new OS. Xen at this point also lacked SMP support inside guests, so some workloads remained far more efficient on native hardware.

## Open questions

- Could guest OSes be ported to hypervisor-awareness automatically or programmatically? Could new OS implementations conform to an interface that makes them hypervisor-compliant by construction?
- Has anyone worked on detecting hot spots, routines a guest calls constantly, and automatically registering fast handlers for them in the hypervisor?

## Sources

- [Xen and the Art of Virtualization](https://www.cl.cam.ac.uk/research/srg/netos/papers/2003-xensosp.pdf)

## Related notes

- [[systems/research/exokernel|Exokernel]]
- [[systems/research/barrelfish|The Multikernel]]
