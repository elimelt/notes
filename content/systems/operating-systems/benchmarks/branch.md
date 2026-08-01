---
title: Branch Prediction Benchmarks
aliases:
  - operating-systems/benchmarks/branch
category: Performance Engineering
tags:
  - branch-prediction
  - cpu
  - pipeline
  - branchless
  - performance
  - benchmarks
date: 2025-12-29
updated: 2026-07-30
status: needs-review
description: Measures the cost of branch misprediction by comparing sorted, random, and branchless variants of a conditional sum, and derives a per-misprediction penalty from the results.
sources:
  - title: The microarchitecture of Intel, AMD and VIA CPUs (Agner Fog)
    url: https://www.agner.org/optimize/microarchitecture.pdf
    type: docs
---

## Purpose

Measure what a branch misprediction costs on a real workload. Modern CPUs speculatively execute past branches before the outcome is known. A wrong guess forces a pipeline flush, and Agner Fog's [microarchitecture manual](https://www.agner.org/optimize/microarchitecture.pdf) puts that penalty in the tens of cycles for recent Intel and AMD cores. This benchmark makes the penalty visible by feeding the same branch predictable and unpredictable data.

## Setup

The CPU model and compiler flags were not recorded with these results, so the note is marked needs-review. The cycle conversions below assume a 3 GHz clock. The runs use the same `./bench` harness as the other notes in this directory.

## Workload

Conditionally sum the elements of a 64 MB array:

```c
for (size_t i = 0; i < n; i++) {
    if (array[i] < threshold)
        sum += array[i];
}
```

Three variants change how predictable the branch is:

- `br_sort`: first half of the array below the threshold, second half above. The predictor learns this immediately.
- `br_rand`: each element is below the threshold with 50% probability. The predictor is wrong about half the time.
- `br_less`: branchless, using a mask instead of a branch.

## Results

| Variant | ns/element | vs sorted |
|---------|------------|-----------|
| `br_sort` (sorted) | 0.85 ns | 1.0x |
| `br_less` (branchless) | 1.41 ns | 1.7x |
| `br_rand` (random) | 2.75 ns | 3.2x |

## Interpretation

The random variant pays 2.75 - 0.85 = 1.9 ns extra per element. Only about half the elements mispredict, so each misprediction costs roughly 3.8 ns, or about 11 cycles at 3 GHz. That is on the low end of published flush penalties, which makes sense because the out-of-order core can overlap some of the recovery with other work.

The branchless variant replaces the branch with arithmetic:

```c
uint64_t mask = -(array[i] < threshold);  // 0 or 0xFFFFFFFFFFFFFFFF
sum += array[i] & mask;
```

It executes more instructions per element, so it loses to the well-predicted branch (1.41 ns vs 0.85 ns). It wins big against the mispredicted branch (1.41 ns vs 2.75 ns) because its cost is flat regardless of the data. The practical rule falls out of the numbers. Keep the branch when the data has a pattern the predictor can learn, and go branchless when the data is effectively random, as with hashed keys. If you can't tell which case you're in, profile it.

One caveat when reproducing this: GCC and Clang at `-O3` sometimes convert branches to conditional moves (`cmov`) on their own, which erases the difference between the branchy and branchless variants. Check the generated assembly if the numbers look flat.

On the hardware side, predictors track the history of each branch and the recent outcomes of all branches, and combine both. Agner Fog's [manual](https://www.agner.org/optimize/microarchitecture.pdf) describes the schemes used by each microarchitecture. These predictors can learn repeating patterns like taken three times then not taken once. Truly random data defeats all of them, which is exactly what `br_rand` exploits.

## Reproduction

```bash
./bench br_sort 64   # Predictable (sorted)
./bench br_rand 64   # Unpredictable (random)
./bench br_less 64   # Branchless (mask)
```

## Sources

- [The microarchitecture of Intel, AMD and VIA CPUs (Agner Fog)](https://www.agner.org/optimize/microarchitecture.pdf)

## Related notes

- [[systems/operating-systems/benchmarks/store_fwd|store-to-load forwarding]]
- [[systems/operating-systems/benchmarks/prefetch|software prefetching]]
- [[systems/performance/streaming_benchmarks/cache_line_efficiency/README|Cache Line Efficiency Benchmark]]
- [[systems/operating-systems/benchmarks/reductions|Parallel Reductions Benchmarks]]
- [[hardware/computer-architecture/rtl-reading-lab|Open-Source CPU RTL Reading Lab]]
