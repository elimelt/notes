---
title: False Sharing Benchmarks
aliases:
  - operating-systems/benchmarks/false_sharing
category: Performance Engineering
tags:
  - false-sharing
  - cache coherence
  - mesi
  - multi-threading
  - cache-line
  - benchmarks
date: 2025-12-29
updated: 2026-07-30
status: needs-review
description: Demonstrates the cost of false sharing by having eight threads increment counters packed into one cache line, then padding each counter to its own line for an 8.5x speedup.
sources:
  - title: What Every Programmer Should Know About Memory (Ulrich Drepper)
    url: https://www.akkadia.org/drepper/cpumemory.pdf
    type: paper
  - title: perf-c2c(1) manual page
    url: https://man7.org/linux/man-pages/man1/perf-c2c.1.html
    type: docs
---

## Purpose

Measure what happens when threads write to different variables that happen to live in the same cache line. The coherence protocol works on whole lines, so the threads fight over the line even though they never touch each other's data. That is false sharing.

## Setup

The CPU model and compiler flags were not recorded with these results, so the note is marked needs-review. The runs use 8 threads and the same `./bench` harness as the other notes in this directory. Cache lines are 64 bytes.

## Workload

Eight threads, each incrementing its own counter in a shared array:

```c
uint64_t counters[8];  // All 64 bytes = 1 cache line!

void thread_n() {
    for (int i = 0; i < N; i++)
        counters[n]++;  // Writes to MY counter
}
```

Each thread owns a different element, and all eight elements fit in one 64-byte cache line. The fixed version pads each counter out to its own line:

```c
struct {
    uint64_t count;
    char pad[56];  // Pad to 64 bytes
} counters[8];
```

## Results

16 MB of work total, which is about 167M increments per thread:

| Variant | Total time | ns/op | Speedup |
|---------|------------|-------|---------|
| `fs_bad` (packed) | 57.8 ms | 0.34 ns | 1.0x |
| `fs_good` (padded) | 6.8 ms | 0.04 ns | 8.5x |

## Interpretation

The packed version loses because of the coherence protocol. Under MESI, a core must hold a line in Modified state to write it. So thread 0 writes `counters[0]` and its core takes the line Modified. Thread 1 then writes `counters[1]`, which forces an invalidation of core 0's copy before core 1 can proceed. Thread 0 writes again and invalidates core 1. The line ping-pongs between cores for the entire run, and every increment waits on a cross-core ownership transfer. Drepper covers the protocol and this exact failure mode in [What Every Programmer Should Know About Memory](https://www.akkadia.org/drepper/cpumemory.pdf).

The padded version gives each core a line nobody else touches. There is no coherency traffic at all, and each increment runs at register-plus-L1 speed. The entire 8.5x gap is ownership transfers.

This shows up in real code wherever per-thread data gets packed into one allocation. Common cases are per-thread counters in a global stats array, several locks placed adjacently in a struct, and queue head and tail pointers that different threads update.

## Detection

`perf c2c` samples cache-to-cache transfers and reports lines contended across cores (see the [perf-c2c manual page](https://man7.org/linux/man-pages/man1/perf-c2c.1.html)):

```bash
perf c2c record ./bench fs_bad 16
perf c2c report
```

Look for the shared data cache line events and high snoop counts.

## Fixes

Pad hot per-thread fields to a cache line boundary, align them with `__attribute__((aligned(64)))`, or move them into thread-local storage with `thread_local` so they never share an allocation in the first place.

## Reproduction

```bash
./bench fs_bad 16   # False sharing (packed)
./bench fs_good 16  # No false sharing (padded)
```

## Sources

- [What Every Programmer Should Know About Memory (Drepper)](https://www.akkadia.org/drepper/cpumemory.pdf)
- [perf-c2c(1) manual page](https://man7.org/linux/man-pages/man1/perf-c2c.1.html)

## Related notes

- [[systems/operating-systems/benchmarks/reductions|parallel reductions]]
- [[systems/operating-systems/benchmarks/bandwidth|memory bandwidth]]
