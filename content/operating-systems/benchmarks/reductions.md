# Parallel Reductions Benchmark

## The Problem with Naive Reduction

A naive reduction creates a **dependency chain**:

```c
uint64_t sum = 0;
for (size_t i = 0; i < n; i++) {
    sum += array[i];  // Each add depends on the previous!
}
```

Each addition must wait for the previous one to complete. On a modern CPU that can execute 4+ adds per cycle, this leaves most execution units idle.

## Benchmark Variants

| Variant | Description |
|---------|-------------|
| `red_naive` | Single accumulator - creates dependency chain |
| `red_ilp` | 8 independent accumulators - breaks dependency chain |
| `red_simd` | AVX2 vector adds (4 × 64-bit per instruction) |
| `red_thread` | 8 pthreads, each summing a portion |
| `red_ilp_simd` | 4 independent AVX2 accumulators |
| `red_all` | Threads + ILP + SIMD combined |
| `red_opt` | Simple loop - compiler free to auto-vectorize |

## Results

### Performance by Array Size (ns per element)

| Size | naive | ilp | simd | thread | ilp+simd | all |
|------|-------|-----|------|--------|----------|-----|
| **1 MB** | 0.41 | 0.21 | 0.17 | 1.70 | 0.15 | 1.40 |
| **4 MB** | 0.21 | 0.19 | 0.18 | 0.37 | 0.21 | 0.35 |
| **16 MB** | 0.35 | 0.27 | 0.24 | 0.18 | 0.25 | 0.15 |
| **64 MB** | 0.41 | 0.31 | 0.30 | 0.19 | 0.30 | 0.17 |
| **256 MB** | 0.40 | 0.31 | 0.33 | 0.17 | 0.32 | 0.14 |
| **1024 MB** | 0.39 | 0.31 | 0.32 | 0.15 | 0.32 | 0.13 |

### Speedup vs Naive (1024 MB)

| Variant | Time (ms) | ns/elem | Speedup |
|---------|-----------|---------|---------|
| `red_naive` | 52.8 | 0.39 | 1.0× |
| `red_ilp` | 41.8 | 0.31 | **1.3×** |
| `red_simd` | 43.3 | 0.32 | **1.2×** |
| `red_thread` | 19.5 | 0.15 | **2.7×** |
| `red_ilp_simd` | 42.4 | 0.32 | **1.2×** |
| `red_all` | 16.9 | 0.13 | **3.1×** |

## Key Observations

### 1. ILP Benefit (~1.3× speedup)

The 8-accumulator version tries to break the dependency chain:

```c
// 8 independent chains - maybe CPU can execute in parallel?
sum0 += array[i+0];
sum1 += array[i+1];
sum2 += array[i+2];
```

The ~1.3× speedup (not 8×) indicates the workload is **memory-bandwidth bound**, not compute-bound.

### 2. Small Arrays and Threading

At 1-4 MB (fits in cache), threading overhead dominates:
- `red_naive`: 0.21-0.41 ns
- `red_thread`: 0.37-1.70 ns (slower!)

### 3. Large Arrays: Threading Wins

At 64+ MB (exceeds cache), threading provides the biggest benefit:
- `red_naive`: 0.39-0.41 ns
- `red_thread`: 0.15-0.19 ns (**2.5-2.7× faster**)

Multiple threads can saturate memory bandwidth from different memory controllers/channels.

### 4. SIMD \approx ILP for this Workload

SIMD and scalar ILP show similar performance because:
- Both break the dependency chain
- Memory bandwidth is the bottleneck, not ALU throughput
- AVX2 loads 32 bytes/instruction, but memory can't keep up

### 5. Cache Effects

Performance varies with array size due to cache hierarchy:

| Size | Likely Location | Observed Behavior |
|------|-----------------|-------------------|
| 1 MB | L2/L3 cache | Fastest single-thread; threading hurts |
| 4 MB | L3 cache | ILP/SIMD help; threading overhead visible |
| 16+ MB | Main memory | Threading helps; memory-bound |

## Assembly

Compiled with `gcc -O3 -march=native`. The compiler auto-vectorizes all variants

### red_naive (compiler auto-vectorizes)

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

Even though source has single accumulator, compiler vectorizes to **1 AVX2 accumulator** (4 parallel adds).

### red_ilp (8 scalar → 2 AVX2 accumulators)

```asm
.L42:
    addq    $1, %rdx
    vpaddq  (%rax), %ymm1, %ymm1      ; accumulator 1: 4 x 64-bit
    vpaddq  32(%rax), %ymm0, %ymm0    ; accumulator 2: 4 x 64-bit
    addq    $64, %rax                  ; 64 bytes = 8 elements per iteration
    cmpq    %rsi, %rdx
    jb      .L42
```

Compiler recognizes 8 independent accumulators and converts to **2 AVX2 accumulators** (8 parallel adds).

### red_simd (hand-written AVX2)

```asm
.L54:
    vpaddq  (%rax), %ymm0, %ymm0      ; 1 AVX2 accumulator
    addq    $32, %rax
    cmpq    %rax, %rcx
    jne     .L54
```

Same as naive! Hand-written SIMD with 1 accumulator matches compiler's auto-vectorization.

### red_ilp_simd (4 AVX2 accumulators = 16 parallel adds)

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

**4 independent AVX2 accumulators** = 16 parallel 64-bit adds per iteration.

### red_opt (compiler completely free)

```asm
.L116:
    vpaddq  (%rax), %ymm0, %ymm0      ; identical to red_naive!
    addq    $32, %rax
    cmpq    %rdx, %rax
    jne     .L116
```

Identical to naive - compiler auto-vectorizes the simple loop.

### Thread workers

**ThreadSum** (naive per-thread):
```asm
    vpaddq  ...  ; compiler auto-vectorizes each thread's work
```

**ThreadSumILPSimd** (optimized per-thread):
```asm
.L17:
    vpaddq  -64(%rcx,%rax,8), %ymm0, %ymm0  ; 2 AVX2 accumulators
    vpaddq  -32(%rcx,%rax,8), %ymm1, %ymm1
    ...
```

### Key Instructions Summary

| Variant | Main Loop Instruction | Accumulators | Elements/Iteration |
|---------|----------------------|--------------|-------------------|
| `red_naive` | `vpaddq (%rax), %ymm0, %ymm0` | 1 × ymm | 4 |
| `red_ilp` | 2 × `vpaddq` | 2 × ymm | 8 |
| `red_simd` | `vpaddq (%rax), %ymm0, %ymm0` | 1 × ymm | 4 |
| `red_ilp_simd` | 4 × `vpaddq` | 4 × ymm | 16 |
| `red_opt` | `vpaddq (%rax), %ymm0, %ymm0` | 1 × ymm | 4 |

### Why Similar Performance?

All variants use AVX2 `vpaddq` (4 × 64-bit add). However, **More accumulators** = more ILP = fewer stalls waiting for previous add, but **memory bandwidth** is the real bottleneck at large sizes. That's why `red_naive` ≈ `red_ilp_simd` for 256+ MB arrays. The only major win is **threading** which saturates multiple memory channels.

## Conclusion

For **memory-bound** workloads like large array reduction, the bottleneck is memory bandwidth, not CPU compute. Multi-threading helps by utilizing multiple memory channels, while ILP/SIMD provide modest benefits.

## Running the Benchmarks

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

