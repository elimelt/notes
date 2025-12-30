# Memory Bandwidth

## The Problem

A single core cannot saturate memory bandwidth. Modern DDR4/DDR5 systems provide 50-100+ GB/s, but one core typically achieves 20-30 GB/s due to:
- Limited outstanding memory requests per core
- Memory controller parallelism across channels/ranks

## The Benchmark

Simple sequential read with varying thread counts:

```c
for (size_t i = 0; i < n; i++) {
    sum += array[i];
}
```

Each thread processes a disjoint chunk of the array.

## Results (1 GB array)

| Threads | GB/s | vs 1 thread |
|---------|------|-------------|
| 1 | 24.9 | 1.0× |
| 2 | 44.1 | 1.8× |
| 4 | 47.8 | 1.9× |
| 8 | 63.7 | 2.6× |

## Observations

### 1. Single-Core Bottleneck

One core achieves ~25 GB/s. This is limited by:
- Number of Line Fill Buffers (LFBs) / Miss Status Handling Registers (MSHRs)
- Memory controller queue depth per core
- Prefetcher effectiveness

### 2. Diminishing Returns

Bandwidth doesn't scale linearly with threads:
- 1→2 threads: 1.8× (good scaling)
- 2→4 threads: 1.1× (memory controller saturating)
- 4→8 threads: 1.3× (some additional parallelism)

### 3. Memory Controller Saturation

The memory controller has finite bandwidth. Once saturated, adding threads doesn't help. The exact saturation point depends on:
- Number of memory channels
- DDR speed and timing
- Memory controller design

### 4. NUMA Effects

On multi-socket systems, threads should access local memory. Remote memory access adds latency and reduces bandwidth.

## Theoretical vs Achieved

DDR4-3200 dual-channel: ~51 GB/s theoretical
DDR5-4800 dual-channel: ~77 GB/s theoretical

Achieved bandwidth is typically 60-80% of theoretical due to:
- Row buffer misses
- Refresh cycles
- Command/address overhead

## Running

```bash
./bench bw_1 1024   # 1 thread
./bench bw_2 1024   # 2 threads
./bench bw_4 1024   # 4 threads
./bench bw_8 1024   # 8 threads
```

Use large arrays (1GB+) to ensure memory-bound behavior.

