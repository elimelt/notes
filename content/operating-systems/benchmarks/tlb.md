---
title: TLB and Page Walk Benchmarks
category: Operating Systems
tags:
  - tlb
  - page-table
  - virtual-memory
  - page-walk
  - huge-pages
  - memory-latency
  - benchmarks
date: 2025-12-29
updated: 2026-07-30
status: needs-review
description: Measures the TLB miss penalty on x86-64 by sweeping access stride from 8 bytes to 8 KB over a 256 MB array, separating cache misses from TLB misses.
sources:
  - title: What Every Programmer Should Know About Memory (Ulrich Drepper)
    url: https://www.akkadia.org/drepper/cpumemory.pdf
    type: paper
---

## Purpose

Measure what a TLB miss costs. Every virtual address has to be translated to a physical address, and the CPU caches translations in the Translation Lookaside Buffer. On a miss, x86-64 hardware walks a 4-level page table, which takes up to 4 dependent memory accesses per translation. This benchmark isolates that cost by controlling how many accesses land on each page.

## Setup

The CPU model and compiler flags were not recorded with these results, so the note is marked needs-review. The runs use a 256 MB array, 4 KB pages, and the same `./bench` harness as the other notes in this directory.

## Workload

Read the array at a fixed stride:

```c
for (size_t i = 0; i < n; i += stride) {
    sum += array[i];
}
```

Small strides touch each 4 KB page many times, so the translation is almost always already in the TLB. A 4 KB stride touches each page exactly once, so with a working set this large every access needs a fresh translation.

## Results

| Stride | Accesses/page | ns/access | vs sequential |
|--------|---------------|-----------|---------------|
| 8B | 512 | 1.36 ns | 1.0x |
| 64B | 64 | 2.49 ns | 1.8x |
| 512B | 8 | 5.38 ns | 4.0x |
| 4KB | 1 | 12.51 ns | 9.2x |
| 8KB | 0.5 | 13.31 ns | 9.8x |

## Interpretation

Two different effects hide in this table, and pulling them apart is the whole point:

| Stride | Cache behavior | TLB behavior |
|--------|---------------|--------------|
| 8B | Hit (prefetcher) | Hit (same page) |
| 64B | Miss (1 line/access) | Hit (64 accesses/page) |
| 512B | Miss | Hit (8 accesses/page) |
| 4KB | Miss | Miss (1 access/page) |

The slowdown from 64 B to 512 B stride is cache behavior, since each access now pulls a fresh cache line. The jump from 512 B (5.38 ns) to 4 KB (12.51 ns) is the TLB. Both strides miss cache the same way, so the extra ~7 ns per access is the translation cost. Drepper's memory paper ([What Every Programmer Should Know About Memory](https://www.akkadia.org/drepper/cpumemory.pdf)) covers the TLB and paging structures behind these numbers.

The miss penalty stays fixed instead of growing with stride, and 8 KB stride costs about the same as 4 KB. The page walk is itself a pointer chase, four dependent loads through PML4, PDPT, PD, and PT, so in the worst case it would cost several DRAM round trips. It doesn't here because the CPU caches intermediate page table entries in its paging structure caches, and the upper-level entries for a linear scan stay resident. Most walks only need the leaf PT entry, which keeps the penalty near 10 ns.

Capacity explains why the misses are total at page stride. An L1 dTLB on the order of 64-128 entries covers only a few hundred KB of 4 KB pages, and an L2 TLB in the low thousands of entries covers a few MB. Striding through 256 MB touches 65K distinct pages, far past either level.

Huge pages attack the same problem from the other side. A 2 MB page covers 512 times as much memory per TLB entry, so this page-strided workload would keep hitting the TLB until the working set passed the TLB entry count times 2 MB. I have not measured the huge-page variant here.

## Reproduction

```bash
./bench tlb_seq 256   # Sequential (TLB hits)
./bench tlb_64 256    # Cache line stride
./bench tlb_512 256   # Within-page stride
./bench tlb_4k 256    # Page stride (TLB misses)
./bench tlb_8k 256    # Skip pages
```

## Sources

- [What Every Programmer Should Know About Memory (Drepper)](https://www.akkadia.org/drepper/cpumemory.pdf)

## Related notes

- [[operating-systems/benchmarks/README|measuring real DRAM latency]]
- [[operating-systems/benchmarks/mlp|memory-level parallelism]]
