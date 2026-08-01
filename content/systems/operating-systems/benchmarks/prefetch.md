---
title: Software Prefetching Benchmarks
aliases:
  - operating-systems/benchmarks/prefetch
category: Performance Engineering
tags:
  - prefetching
  - cache
  - memory-latency
  - hardware-prefetcher
  - performance
  - benchmarks
date: 2025-12-29
updated: 2026-07-30
status: needs-review
description: Compares hardware and software prefetching for random and sequential access, measuring how prefetch distance affects the win and where explicit prefetches beat the hardware prefetcher.
sources:
  - title: GCC documentation for __builtin_prefetch
    url: https://gcc.gnu.org/onlinedocs/gcc/Other-Builtins.html
    type: docs
---

## Purpose

Measure when issuing explicit prefetch instructions beats letting the hardware prefetcher do its thing. Hardware prefetchers detect sequential and strided patterns and fetch ahead on their own, and they do nothing useful for random patterns. Software prefetching can cover the random case whenever the code knows future addresses, and it turns out it can also beat the hardware on the sequential case.

## Setup

The CPU model and compiler flags were not recorded with these results, so the note is marked needs-review. The runs use a 256 MB array and the same `./bench` harness as the other notes in this directory. The DRAM latency assumed in the analysis (~75 to 100 ns) comes from the pointer-chase measurement in [[systems/operating-systems/benchmarks/README|measuring real DRAM latency]].

## Workload

The software prefetch is GCC's builtin ([docs](https://gcc.gnu.org/onlinedocs/gcc/Other-Builtins.html)):

```c
__builtin_prefetch(&array[i + 64], 0, 0);  // Prefetch 64 elements ahead
sum += array[i];                            // Use current element
```

The signature is `__builtin_prefetch(addr, rw, locality)` where `rw` is 0 for read and 1 for write, and `locality` runs from 0 (no temporal locality) to 3 (high). On x86 it compiles to `prefetchnta` or `prefetcht0/t1/t2`.

The random variants walk a precomputed index array, prefetching `array[indices[i+N]]` while processing `array[indices[i]]`. The sequential variants stream through the array with and without an explicit prefetch at distance +64 elements.

## Results

Random access:

| Variant | Distance | ns/access | vs baseline |
|---------|----------|-----------|-------------|
| `pf_none` | 0 | 7.61 ns | 1.0x |
| `pf_8` | +8 | 6.23 ns | 1.2x |
| `pf_32` | +32 | 5.91 ns | 1.3x |
| `pf_128` | +128 | 5.99 ns | 1.3x |

Sequential access:

| Variant | Distance | ns/access | vs baseline |
|---------|----------|-----------|-------------|
| `pf_seq` | 0 (hw only) | 1.37 ns | 1.0x |
| `pf_seq64` | +64 | 0.54 ns | 2.5x |

## Interpretation

For random access the win tops out around 25%. The indices are known ahead of time, so the prefetch addresses are computable, and yet the improvement stays modest. The prefetch distance has to be long enough to cover the DRAM round trip, and the 7.6 ns baseline already reflects heavy memory-level parallelism (see [[systems/operating-systems/benchmarks/mlp|memory-level parallelism]]), so the run is close to bandwidth-bound before any prefetching happens. Once bandwidth is the limit, all a prefetch can do is smooth out when the requests land.

The sequential result surprised me. The explicit prefetch at +64 elements (512 bytes, 8 cache lines ahead) beats the hardware prefetcher by 2.5x. My read is that the hardware prefetcher stays conservative about how far ahead it fetches so it does not pollute the cache on patterns it has misjudged. The software prefetch has no such doubt because the code knows the pattern exactly, so fetching aggressively far ahead pays off.

Distance tuning depends on the memory latency, the work per iteration, and cache capacity. In these runs, +32 to +128 worked for random access and +64 worked for sequential. Too short a distance and the data has not arrived when the load executes. Too long and the prefetched lines get evicted before use.

Prefetching does nothing for a pointer chase, since `array[array[i]]` needs `array[i]` before the prefetch address even exists. It also backfires on data already resident in cache, where the extra instructions are pure overhead, and on bandwidth-saturated loops, where the prefetches just add pressure.

## Reproduction

```bash
./bench pf_none 256   # Random baseline
./bench pf_32 256     # Random prefetch +32
./bench pf_seq 256    # Sequential hw prefetch only
./bench pf_seq64 256  # Sequential sw prefetch +64
```

## Sources

- [GCC documentation for __builtin_prefetch](https://gcc.gnu.org/onlinedocs/gcc/Other-Builtins.html)

## Related notes

- [[systems/operating-systems/benchmarks/mlp|memory-level parallelism]]
- [[systems/operating-systems/benchmarks/README|measuring real DRAM latency]]
- [[systems/performance/streaming_benchmarks/cache_line_efficiency/README|cache line efficiency]]
- [[systems/operating-systems/benchmarks/reductions|parallel reductions]]
- [[systems/operating-systems/benchmarks/tlb|TLB and page walks]]
