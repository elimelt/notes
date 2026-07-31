---
title: Memory Bandwidth Benchmarks
aliases:
  - operating-systems/benchmarks/bandwidth
category: Operating Systems
tags:
  - memory
  - bandwidth
  - multi-threading
  - numa
  - benchmarks
date: 2025-12-29
updated: 2026-07-30
status: needs-review
description: Measures how sequential-read memory bandwidth scales from one to eight threads, and why a single core cannot saturate the memory controller.
sources:
  - title: What Every Programmer Should Know About Memory (Ulrich Drepper)
    url: https://www.akkadia.org/drepper/cpumemory.pdf
    type: paper
---

## Purpose

Measure how much memory bandwidth one core can pull on its own, and how bandwidth scales as more threads read from DRAM at once. A single core has a limited number of outstanding cache misses it can track, so it stalls long before the memory controller runs out of capacity. Adding threads adds outstanding requests, which lets the controller keep more DRAM banks and channels busy.

## Setup

The hardware, DIMM configuration, and compiler flags were not recorded alongside these results, which is why this note is marked needs-review. The runs use the same `./bench` harness as the other notes in this directory. The DRAM latency measurements in [[systems/operating-systems/benchmarks/README|measuring real DRAM latency]] record the system used there.

## Workload

Sequential read over a 1 GB array, summing every element:

```c
for (size_t i = 0; i < n; i++) {
    sum += array[i];
}
```

The thread count varies from 1 to 8. Each thread reads a disjoint chunk of the array, so there is no sharing and no synchronization inside the timed loop. The array is large enough that the working set never fits in cache.

## Results

| Threads | GB/s | vs 1 thread |
|---------|------|-------------|
| 1 | 24.9 | 1.0x |
| 2 | 44.1 | 1.8x |
| 4 | 47.8 | 1.9x |
| 8 | 63.7 | 2.6x |

## Interpretation

One thread reaches 24.9 GB/s. The core runs out of miss-tracking resources before DRAM runs out of bandwidth. Each core has a fixed number of Line Fill Buffers (Intel's name for the L1 miss registers, often called MSHRs elsewhere), and once they are all occupied the core cannot issue another cache miss. Prefetcher aggressiveness and per-core queue depth in the memory controller bound it further.

Going from one thread to two gives 1.8x, close to linear. After that the memory controller starts to saturate. Two to four threads adds almost nothing, and four to eight adds another 1.3x, which suggests the extra threads still expose some bank and channel level parallelism the controller could not get from four.

For reference, peak DRAM bandwidth is channels times 8 bytes times the transfer rate. Dual-channel DDR4-3200 works out to 2 x 8 B x 3200 MT/s = 51.2 GB/s, and dual-channel DDR5-4800 to 76.8 GB/s. The 63.7 GB/s measured here at 8 threads sits in that range, but without the recorded DIMM configuration I can't compute the utilization for this machine. Achieved bandwidth always lands below the peak number because row buffer misses, refresh cycles, and command overhead steal bus time. Drepper's memory paper ([What Every Programmer Should Know About Memory](https://www.akkadia.org/drepper/cpumemory.pdf)) walks through those overheads in detail.

On multi-socket machines the picture changes again. A thread reading from the other socket's memory pays an interconnect hop, which raises latency and cuts bandwidth. These runs were on a single socket, so NUMA placement did not matter here.

## Reproduction

```bash
./bench bw_1 1024   # 1 thread
./bench bw_2 1024   # 2 threads
./bench bw_4 1024   # 4 threads
./bench bw_8 1024   # 8 threads
```

Use arrays of 1 GB or more so the run stays memory-bound instead of measuring cache bandwidth.

## Sources

- [What Every Programmer Should Know About Memory (Drepper)](https://www.akkadia.org/drepper/cpumemory.pdf)

## Related notes

- [[systems/operating-systems/benchmarks/README|measuring real DRAM latency]]
- [[systems/operating-systems/benchmarks/mlp|memory-level parallelism]]
- [[systems/operating-systems/benchmarks/reductions|parallel reductions]]
