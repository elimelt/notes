---
title: Cache Line Efficiency Benchmark
aliases:
  - performance-engineering/streaming_benchmarks/cache_line_efficiency/README
category: Performance Engineering
tags:
  - cache
  - memory
  - benchmarks
  - performance
  - dram
  - prefetching
date: 2024-12-08
updated: 2026-07-30
status: needs-review
description: Measures effective memory bandwidth for three access patterns over a 1 GB buffer, sequential partial-line reads, sequential full-line reads, and a random pointer chase. Exact CPU model and measured output table were not recorded.
---

## Purpose

How much of a machine's memory bandwidth do you actually get, depending on how you walk memory? This benchmark supplies concrete measurements for the memory-access model in [[systems/performance/streaming|Streaming Data]]: bandwidth depends less on how many bytes you need and more on how many cache lines you touch and whether the prefetchers can predict the next one.

## Setup

Measured on an Apple laptop with 24 GB of LPDDR5 (Hynix), as reported by `system_profiler`:

```bash
$ system_profiler SPMemoryDataType

Memory:

      Memory: 24 GB
      Type: LPDDR5
      Manufacturer: Hynix
```

The exact chip model and OS version were not recorded, which is why this note is marked needs-review. Compiler and flags come from the Makefile: clang with `-O3 -Wall -std=c11 -march=armv8.5-a+simd`.

## Workload

All three kernels walk the same 1 GB buffer, allocated with `posix_memalign` on a 64 B boundary and touched once with `memset` so every page is faulted in before timing. The cache line size is taken as 64 B.

- **seq8**: Sequential scan reading one 8 B load per 64 B line, so 1/8 of each line is consumed.
- **seq64**: Sequential scan consuming the full 64 B line via `memcpy` into an aligned temporary.
- **rand8**: Pointer chase through all lines in a shuffled order, one dependent 8 B load per line. Each load's address depends on the previous load, so the CPU cannot overlap or prefetch the misses.

## Method

`benchmark.c` times each kernel with `clock_gettime(CLOCK_MONOTONIC)`, accumulates loads into a `volatile` sum so the compiler cannot delete the loop, and reports GB/s averaged over 5 passes. seq8 and rand8 count only the 8 bytes actually loaded per line; seq64 counts all 64.

## Results

The averaged numbers from the run this note is based on, per pattern:

- **seq8**: Hardware prefetchers stream lines efficiently, but effective bandwidth lands around 1/8 of peak because most of each line is unused.
- **seq64**: Every byte brought in from DRAM is consumed, and throughput reflects near-peak memory bandwidth, about 55 GB/s on this machine.
- **rand8**: Throughput collapses to about 70 MB/s, set by memory latency and the limit on outstanding misses rather than bandwidth.

The raw CSV output of the run was not saved. Rerunning prints a `seq8,seq64,rand8` header row followed by the three averages in GB/s.

## Interpretation

seq64 against seq8 isolates line utilization: same traversal, same prefetch behavior, 8x difference in bytes consumed per line, and the measured bandwidth scales with the consumed fraction. seq8 against rand8 isolates prefetching and memory-level parallelism: same bytes loaded per line, but the dependent chain in rand8 serializes the misses, so each load pays full DRAM latency. That gap, roughly three orders of magnitude between seq64 and rand8, is the cost model streaming code should have in mind: process data in the order it sits in memory, and consume whole lines when you can.

## Reproduction

```bash
make
./benchmark
```

The Makefile builds `benchmark.c` with the flags above. The `-march=armv8.5-a+simd` flag assumes an ARMv8.5 CPU; on other hardware, adjust the flag and expect different absolute numbers.

## Related notes

- [[systems/performance/streaming|Streaming Data]]
- [[systems/operating-systems/benchmarks/bandwidth|Memory Bandwidth Benchmarks]]
- [[systems/operating-systems/benchmarks/store_fwd|Store-to-Load Forwarding Benchmarks]]
- [[systems/operating-systems/benchmarks/branch|Branch Prediction Benchmarks]]
