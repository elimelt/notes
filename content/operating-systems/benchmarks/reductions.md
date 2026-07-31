---
title: Parallel Reductions Benchmarks
category: Operating Systems
tags:
  - simd
  - avx2
  - ilp
  - multi-threading
  - vectorization
  - memory-bandwidth
  - benchmarks
date: 2025-12-29
updated: 2026-07-30
status: needs-review
description: Benchmarks array reduction variants (single accumulator, multiple accumulators, AVX2, threads, and combinations) across array sizes, with the generated assembly showing what the compiler actually emitted.
---

## Purpose

Measure how much a large array reduction speeds up when you break its dependency chain with more accumulators, SIMD, and threads, and figure out where the bottleneck actually sits. The naive version looks like it should starve the ALUs, and the assembly plus the numbers show whether it does.

The naive reduction chains every addition on the previous one:

```c
uint64_t sum = 0;
for (size_t i = 0; i < n; i++) {
    sum += array[i];  // Each add depends on the previous!
}
```

A modern core can execute 4 or more adds per cycle, so a serial chain of adds leaves most of the execution units idle. In principle.

## Setup

Compiled with `gcc -O3 -march=native` on an x86-64 CPU with AVX2. Threaded variants use 8 pthreads. The exact CPU model was not recorded with these results, which is why the note is marked needs-review. The runs use the same `./bench` harness as the other notes in this directory.

## Workload

| Variant | Description |
|---------|-------------|
| `red_naive` | Single accumulator - creates dependency chain |
| `red_ilp` | 8 independent accumulators - breaks dependency chain |
| `red_simd` | AVX2 vector adds (4 x 64-bit per instruction) |
| `red_thread` | 8 pthreads, each summing a portion |
| `red_ilp_simd` | 4 independent AVX2 accumulators |
| `red_all` | Threads + ILP + SIMD combined |
| `red_opt` | Simple loop - compiler free to auto-vectorize |

Array size sweeps from 1 MB to 1024 MB so the working set crosses each cache level.

## Results

Performance by array size, in ns per element:

| Size | naive | ilp | simd | thread | ilp+simd | all |
|------|-------|-----|------|--------|----------|-----|
| 1 MB | 0.41 | 0.21 | 0.17 | 1.70 | 0.15 | 1.40 |
| 4 MB | 0.21 | 0.19 | 0.18 | 0.37 | 0.21 | 0.35 |
| 16 MB | 0.35 | 0.27 | 0.24 | 0.18 | 0.25 | 0.15 |
| 64 MB | 0.41 | 0.31 | 0.30 | 0.19 | 0.30 | 0.17 |
| 256 MB | 0.40 | 0.31 | 0.33 | 0.17 | 0.32 | 0.14 |
| 1024 MB | 0.39 | 0.31 | 0.32 | 0.15 | 0.32 | 0.13 |

Speedup vs naive at 1024 MB:

| Variant | Time (ms) | ns/elem | Speedup |
|---------|-----------|---------|---------|
| `red_naive` | 52.8 | 0.39 | 1.0x |
| `red_ilp` | 41.8 | 0.31 | 1.3x |
| `red_simd` | 43.3 | 0.32 | 1.2x |
| `red_thread` | 19.5 | 0.15 | 2.7x |
| `red_ilp_simd` | 42.4 | 0.32 | 1.2x |
| `red_all` | 16.9 | 0.13 | 3.1x |

## Interpretation

The 8-accumulator version was supposed to break the dependency chain:

```c
// 8 independent chains - maybe CPU can execute in parallel?
sum0 += array[i+0];
sum1 += array[i+1];
sum2 += array[i+2];
```

It gains 1.3x rather than anything close to 8x. At these sizes the loop is limited by memory bandwidth rather than by the add units, so extra ILP has little to push against. SIMD lands in the same place as scalar ILP for the same reason. Both break the dependency chain, and an AVX2 load moves 32 bytes per instruction, but memory can't feed the core fast enough for the ALU width to matter.

Array size flips which strategy wins. At 1-4 MB the data fits in cache, single-thread variants are fast, and threading actively hurts (0.37-1.70 ns/elem vs 0.21-0.41 for naive) because thread startup and joining dominate such a short run. From 16 MB up the data lives in DRAM and threading takes over, holding 0.15-0.19 ns/elem while every single-thread variant sits around 0.3-0.4. Multiple threads keep more memory requests in flight and draw from multiple channels at once, which is the same effect measured directly in [[operating-systems/benchmarks/bandwidth|memory bandwidth]].

## Assembly

The compiler auto-vectorizes every variant, which explains several results that look odd at first.

`red_naive`, single accumulator in the source:

```asm
.L25:
    vpaddq  (%rax), %ymm0, %ymm0      ; AVX2: add 4 x 64-bit from memory to ymm0
    addq    $32, %rax                  ; advance pointer by 32 bytes (4 elements)
    cmpq    %rdx, %rax
    jne     .L25
; horizontal reduction:
    vextracti128  $0x1, %ymm0, %xmm1  ; extract high 128 bits
    vpaddq  %xmm0, %xmm1, %xmm0       ; add high + low halves
    vpsrldq $8, %xmm0, %xmm1          ; shift right 8 bytes
    vpaddq  %xmm1, %xmm0, %xmm0       ; final sum
```

The compiler turned the scalar loop into one AVX2 accumulator doing 4 parallel adds. So "naive" was never actually serial.

`red_ilp`, 8 scalar accumulators in the source:

```asm
.L42:
    addq    $1, %rdx
    vpaddq  (%rax), %ymm1, %ymm1      ; accumulator 1: 4 x 64-bit
    vpaddq  32(%rax), %ymm0, %ymm0    ; accumulator 2: 4 x 64-bit
    addq    $64, %rax                  ; 64 bytes = 8 elements per iteration
    cmpq    %rsi, %rdx
    jb      .L42
```

The compiler recognized the 8 independent accumulators and converted them to 2 AVX2 accumulators, 8 parallel adds.

`red_simd`, hand-written AVX2 with one accumulator:

```asm
.L54:
    vpaddq  (%rax), %ymm0, %ymm0      ; 1 AVX2 accumulator
    addq    $32, %rax
    cmpq    %rax, %rcx
    jne     .L54
```

Identical to what the compiler produced for the naive loop. Hand-writing the intrinsics bought nothing.

`red_ilp_simd`, 4 AVX2 accumulators:

```asm
.L79:
    vpaddq  (%rax), %ymm1, %ymm1      ; accumulator 1
    vpaddq  32(%rax), %ymm2, %ymm2    ; accumulator 2
    subq    $-128, %rax               ; advance 128 bytes (16 elements)
    vpaddq  -64(%rax), %ymm0, %ymm0   ; accumulator 3
    vpaddq  -32(%rax), %ymm3, %ymm3   ; accumulator 4
    cmpq    %rcx, %rax
    jne     .L79
```

16 parallel 64-bit adds per iteration. `red_opt` compiles to the same loop as `red_naive`, and the thread workers each auto-vectorize their own chunk the same way.

Summing up what each main loop actually runs:

| Variant | Main Loop Instruction | Accumulators | Elements/Iteration |
|---------|----------------------|--------------|-------------------|
| `red_naive` | `vpaddq (%rax), %ymm0, %ymm0` | 1 x ymm | 4 |
| `red_ilp` | 2 x `vpaddq` | 2 x ymm | 8 |
| `red_simd` | `vpaddq (%rax), %ymm0, %ymm0` | 1 x ymm | 4 |
| `red_ilp_simd` | 4 x `vpaddq` | 4 x ymm | 16 |
| `red_opt` | `vpaddq (%rax), %ymm0, %ymm0` | 1 x ymm | 4 |

Every variant runs `vpaddq`, so the only real difference is accumulator count. More accumulators mean fewer stalls waiting on the previous add, and at 256 MB and up that difference vanishes because memory bandwidth caps all of them. That is why `red_naive` and `red_ilp_simd` tie at large sizes, and why threading, which raises the memory throughput ceiling itself, is the only change that moves the number much.

## Reproduction

```bash
# Build
make

# Run individual benchmark
./bench red_naive 256    # 256 MB array
./bench red_ilp 256
./bench red_all 256

# Compare all variants
for v in red_naive red_ilp red_simd red_thread red_ilp_simd red_all; do
    ./bench $v 256 2>&1 | grep "Time per"
done
```

## Related notes

- [[operating-systems/benchmarks/bandwidth|memory bandwidth]]
- [[operating-systems/benchmarks/false_sharing|false sharing]]
