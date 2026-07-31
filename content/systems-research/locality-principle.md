---
title: The Locality Principle
category: Systems
tags:
  - os
  - operating-system
  - systems
  - virtual-memory
  - caching
  - paper-notes
date: 2025-03-05
updated: 2026-07-30
status: evergreen
description: Review notes on Denning's retrospective about the working set model and how locality of reference became a general design principle for memory systems.
sources:
  - title: The Locality Principle, Peter J. Denning, Communications of the ACM 48(7), 2005
    url: https://dl.acm.org/doi/10.1145/1070838.1070856
    type: paper
  - title: Author's PDF
    url: https://denninginstitute.com/pjd/PUBS/CACMcols/cacmJul05.pdf
    type: paper
---

## Purpose

Reading notes on Denning's retrospective about locality. The note traces how the working set model fixed thrashing in early virtual memory, and why locality generalized into a design principle far beyond paging. My original note linked the wrong PDF; the sources above are the correct ones.

## Citation

- [The Locality Principle](https://dl.acm.org/doi/10.1145/1070838.1070856), Peter J. Denning, Communications of the ACM, July 2005 ([author's PDF](https://denninginstitute.com/pjd/PUBS/CACMcols/cacmJul05.pdf)).

## Problem

Early virtual memory implementations were plagued by thrashing, where the system spends more time swapping pages in and out of memory than executing the program. Thrashing happens when a program's working set is larger than the physical memory available to it, so it page faults repeatedly and throughput collapses.

## Main idea

Denning recounts the history of virtual memory and the development of the working set model for managing memory. While studying the problem, he found a natural pattern in program behavior: memory references cluster, and the set of pages a program needs stays related over time by locality. That property is general, and it can be exploited to improve the performance of systems well beyond paging, particularly any system that talks to external storage.

## Mechanism

The working set model $W(t, T)$ defines a process's memory needs as the set of pages it referenced in the time interval of length $T$ preceding time $t$. That gives an abstract, measurable definition of what a process needs, and a theoretical basis for reasoning about memory behavior.

The model turns into a control mechanism through admission control on the multiprogramming level. The OS refuses to activate a program whose working set would not fit in available memory. Feedback control on that admission decision prevents thrashing outright, because memory never gets committed past what the active working sets demand. The same coping strategy applies whenever working sets grow too large: queue up requests and control admission.

## Assumptions and limits

The original model fixes $T$, which makes it behave like an LRU cache of a fixed window, and no single window suits all workloads. Some workloads also break the model's shape entirely, like a job that reads a massive file sequentially and never revisits a page.

## Evidence

The paper is historical, so the evidence is the record. Working-set-based memory management made virtual memory viable and reasonably predictable, and locality went on to be applied across caches, storage hierarchies, and plenty of other domains.

## Open questions

- Can malicious actors exploit systems designed around the common case of locality, turning worst-case access patterns into a denial of service?
- Is designing for high-throughput sequential reads directly at odds with designing for locality, or can a system target both at once?

## Sources

- [The Locality Principle, CACM 2005](https://dl.acm.org/doi/10.1145/1070838.1070856)
- [Author's PDF at the Denning Institute](https://denninginstitute.com/pjd/PUBS/CACMcols/cacmJul05.pdf)

## Related notes

- [[systems-research/barrelfish|The Multikernel]]
- [[systems-research/hints-for-computer-system-design|Hints for Computer System Design]]
