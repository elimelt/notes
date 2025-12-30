# Memory-Level Parallelism (MLP)

## The Problem

A single pointer chase serializes memory accesses:

```c
size_t idx = 0;
for (size_t i = 0; i < n; i++) {
    idx = array[idx];  // Can't start next load until this completes
}
```

Each load depends on the previous result. The CPU issues one memory request, waits ~75ns for DRAM, then issues the next. Memory bandwidth sits mostly idle.

## Multiple Chains

Run N independent pointer chains simultaneously

```c
// 4 independent chains - CPU can issue 4 loads in parallel
idx0 = array[idx0];
idx1 = array[idx1];
idx2 = array[idx2];
idx3 = array[idx3];
```

No dependencies between chains. The CPU's load/store unit can have multiple outstanding memory requests in its **Miss Status Holding Registers (MSHRs)**. Modern CPUs probably have anywhere from a dozen to 64 MSHRs.

## Results (256 MB array)

| Chains | ns/access | Speedup | Effective MLP |
|--------|-----------|---------|---------------|
| 1      | 92.6 ns   | 1.0×    | 1.0 |
| 2      | 53.6 ns   | 1.7×    | 1.7 |
| 4      | 31.0 ns   | 3.0×    | 3.0 |
| 8      | 15.6 ns   | 5.9×    | 5.9 |
| 16     | 8.9 ns    | 10.4×   | 10.4 |

## Observations

### 1. Near-Linear Scaling to ~8 Chains

Each additional chain nearly halves latency until we hit hardware limits. The CPU successfully overlaps memory requests when there are no dependencies.

### 2. Diminishing Returns Past 8-10 Chains

At 16 chains, we see ~10× speedup rather than 16×. This reflects:
- MSHR capacity limits (~10-12 on this CPU)
- Memory controller queue depth
- DRAM bank conflicts when many requests are in flight

### 3. Convergence with Random Access

Compare to `ran` benchmark (random with independent indices): ~7ns. That's our ceiling - maximum MLP the hardware can sustain.

| Benchmark | ns/access | MLP |
|-----------|-----------|-----|
| `chase` (1 chain) | 92.6 ns | 1 |
| `mlp16` (16 chains) | 8.9 ns | ~10 |
| `ran` (independent) | 7.6 ns | ~12 |

## Why

Most real code has memory access patterns somewhere between fully serial (pointer chase) and fully parallel (independent random). Understanding MLP helps you:

1. **Restructure data** to enable parallel accesses
2. **Batch operations** instead of one-at-a-time processing
3. **Unroll loops** to expose multiple independent memory operations
4. **Use prefetching** when you know future access patterns

## Assembly

Ensuring the compiler doesn't serialize the loads:

```asm
; 4-chain inner loop
.L_loop:
    movq  (%rax,%r8,8), %r8      ; chain 0
    movq  (%rax,%r9,8), %r9      ; chain 1 (independent)
    movq  (%rax,%r10,8), %r10    ; chain 2 (independent)
    movq  (%rax,%r11,8), %r11    ; chain 3 (independent)
    ...
```

All four `movq` instructions can be issued in the same cycle. The CPU's out-of-order engine tracks that they're independent and keeps all four memory requests in flight.

## Running

```bash
./bench mlp1 256   # Baseline (1 chain)
./bench mlp4 256   # 4 chains
./bench mlp16 256  # 16 chains

# Compare to random access (maximum MLP)
./bench ran 256
```

