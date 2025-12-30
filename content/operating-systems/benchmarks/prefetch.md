# Software Prefetching

## Hardware vs Software

Modern CPUs have **hardware prefetchers** that detect access patterns and speculatively fetch cache lines. Great for sequential/strided access, but fail for random patterns.

**Software prefetching** explicitly tells the CPU to fetch data before you need it:

```c
__builtin_prefetch(&array[i + 64], 0, 0);  // Prefetch 64 elements ahead
sum += array[i];                            // Use current element
```

## Results (256 MB array)

### Random Access

| Variant | Distance | ns/access | vs baseline |
|---------|----------|-----------|-------------|
| `pf_none` | 0 | 7.61 ns | 1.0× |
| `pf_8` | +8 | 6.23 ns | 1.2× |
| `pf_32` | +32 | 5.91 ns | 1.3× |
| `pf_128` | +128 | 5.99 ns | 1.3× |

### Sequential Access

| Variant | Distance | ns/access | vs baseline |
|---------|----------|-----------|-------------|
| `pf_seq` | 0 (hw only) | 1.37 ns | 1.0× |
| `pf_seq64` | +64 | 0.54 ns | 2.5× |

## Observations

### 1. Random Prefetch Helps Modestly (~25%)

For random access, we know the *sequence* of indices but not their *values*. We can prefetch `array[indices[i+N]]` while processing `array[indices[i]]`.

Limited improvement because:
- Prefetch distance must be large enough to hide DRAM latency (~300 cycles)
- But not so large that prefetched data gets evicted before use
- Memory bandwidth becomes the bottleneck, not latency

### 2. Sequential SW Prefetch Beats Hardware

Surprisingly, software prefetching beats the hardware prefetcher for sequential access. The hardware prefetcher is *conservative* - it doesn't fetch too far ahead to avoid cache pollution. Our explicit prefetch with distance +64 (512 bytes ahead) is more aggressive and wins when we know the pattern perfectly.

### 3. Optimal Prefetch Distance

Depends on memory latency (~75ns), loop iteration time, and cache capacity. For random access, +32 to +128 works well. For sequential, +64 (512 bytes = 8 cache lines) is effective.

## When Prefetching Doesn't Help

1. **Pointer chasing**: Can't prefetch `array[array[i]]` because you don't know `array[i]` yet
2. **Unpredictable patterns**: If you don't know future addresses, you can't prefetch them
3. **Cache-resident data**: Prefetching hurts if data is already in cache (extra instructions)
4. **Bandwidth-bound**: If memory bandwidth is saturated, prefetching adds pressure

## The Instruction

```c
__builtin_prefetch(addr, rw, locality);
// rw: 0 = read, 1 = write
// locality: 0 = no temporal locality, 3 = high temporal locality
```

Compiles to x86 `prefetchnta` (non-temporal) or `prefetcht0/t1/t2` (temporal).

## Running

```bash
./bench pf_none 256   # Random baseline
./bench pf_32 256     # Random prefetch +32
./bench pf_seq 256    # Sequential hw prefetch only
./bench pf_seq64 256  # Sequential sw prefetch +64
```

