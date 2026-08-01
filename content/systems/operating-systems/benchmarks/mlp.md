---
title: Memory-Level Parallelism Benchmarks
aliases:
  - operating-systems/benchmarks/mlp
category: Performance Engineering
tags:
  - memory-level-parallelism
  - mlp
  - pointer-chasing
  - mshr
  - latency-hiding
  - benchmarks
date: 2025-12-29
updated: 2026-07-30
status: needs-review
description: Measures how running multiple independent pointer chains overlaps DRAM accesses, scaling from 92.6 ns per access with one chain down to 8.9 ns with sixteen.
sources:
  - title: Original benchmark measurements by Elijah Melton
    type: experiment
  - title: What Every Programmer Should Know About Memory (Ulrich Drepper)
    url: https://www.akkadia.org/drepper/cpumemory.pdf
    type: paper
---

## Purpose

Measure how much DRAM latency the CPU can hide when memory accesses are independent of each other. A single pointer chase serializes everything, so it pays full latency on every load. Independent chains let the out-of-order core keep several misses in flight at once, and this benchmark counts how many this machine can actually sustain.

## Setup

The CPU model and compiler flags were not recorded with these results, so the note is marked needs-review. The runs use a 256 MB array and the same `./bench` harness as the other notes in this directory. The single-chain baseline here (92.6 ns) matches the serial DRAM latency measured in [[systems/operating-systems/benchmarks/README|measuring real DRAM latency]].

## Workload

The baseline is one pointer chase through a randomized chain:

```c
size_t idx = 0;
for (size_t i = 0; i < n; i++) {
    idx = array[idx];  // Can't start next load until this completes
}
```

Each load needs the result of the previous one, so the CPU issues one memory request, waits out the full DRAM round trip, then issues the next. Memory bandwidth sits mostly idle.

The variants run N independent chains in the same loop:

```c
// 4 independent chains - CPU can issue 4 loads in parallel
idx0 = array[idx0];
idx1 = array[idx1];
idx2 = array[idx2];
idx3 = array[idx3];
```

Nothing connects the chains, so the load/store unit can hold all of them as outstanding misses in its Miss Status Holding Registers (MSHRs) at once. The MSHR count is the hardware ceiling on how many chains can help.

It is worth checking the assembly to confirm the compiler kept the loads independent:

```asm
; 4-chain inner loop
.L_loop:
    movq  (%rax,%r8,8), %r8      ; chain 0
    movq  (%rax,%r9,8), %r9      ; chain 1 (independent)
    movq  (%rax,%r10,8), %r10    ; chain 2 (independent)
    movq  (%rax,%r11,8), %r11    ; chain 3 (independent)
    ...
```

The out-of-order engine sees four independent `movq` instructions and keeps all four memory requests in flight.

## Results

| Chains | ns/access | Speedup | Effective MLP |
|--------|-----------|---------|---------------|
| 1      | 92.6 ns   | 1.0x    | 1.0 |
| 2      | 53.6 ns   | 1.7x    | 1.7 |
| 4      | 31.0 ns   | 3.0x    | 3.0 |
| 8      | 15.6 ns   | 5.9x    | 5.9 |
| 16     | 8.9 ns    | 10.4x   | 10.4 |

For comparison, the `ran` benchmark (random access with independent indices, so maximum parallelism) lands at 7.6 ns:

| Benchmark | ns/access | MLP |
|-----------|-----------|-----|
| `chase` (1 chain) | 92.6 ns | 1 |
| `mlp16` (16 chains) | 8.9 ns | ~10 |
| `ran` (independent) | 7.6 ns | ~12 |

## Interpretation

Scaling is close to linear up to 8 chains. Each doubling of chains nearly halves the time per access, which means the hardware really does overlap the requests.

Past 8 chains the returns shrink. Sixteen chains gives 10.4x rather than 16x. The measured ceiling of roughly 10 to 12 concurrent misses is the interesting number here. It reflects the MSHR capacity of this core, plus memory controller queue depth and DRAM bank conflicts once that many requests are in flight. The fully independent `ran` benchmark converges to the same ceiling, so 7 to 8 ns per access is the best this machine can do for random DRAM reads no matter how the code is written.

Real code sits somewhere between the fully serial chase and the fully parallel random loop. Knowing where your access pattern falls tells you what to fix. Restructuring data so accesses stop depending on each other, batching lookups instead of doing them one at a time, and unrolling loops to expose independent loads all move you toward the parallel end. Prefetching helps when future addresses are computable, which is measured separately in [[systems/operating-systems/benchmarks/prefetch|software prefetching]].

## Reproduction

```bash
./bench mlp1 256   # Baseline (1 chain)
./bench mlp4 256   # 4 chains
./bench mlp16 256  # 16 chains

## Compare to random access (maximum MLP)
./bench ran 256
```

## Related notes

- [[systems/operating-systems/benchmarks/README|measuring real DRAM latency]]
- [[systems/operating-systems/benchmarks/prefetch|software prefetching]]
- [[systems/operating-systems/benchmarks/bandwidth|memory bandwidth]]
- [[systems/performance/streaming_benchmarks/cache_line_efficiency/README|cache line efficiency]]
- [[systems/operating-systems/benchmarks/store_fwd|store-to-load forwarding]]
