# False Sharing

## The Problem

Multiple threads access **different variables** that share a **cache line**:

```c
uint64_t counters[8];  // All 64 bytes = 1 cache line!

void thread_n() {
    for (int i = 0; i < N; i++)
        counters[n]++;  // Writes to MY counter
}
```

Each thread owns a *different* element, but they all share one cache line. Every write invalidates the entire line on other cores.

## MESI Protocol

1. **Thread 0** writes `counters[0]` → cache line enters **Modified** state on Core 0
2. **Thread 1** writes `counters[1]` → must **invalidate** Core 0's copy first
3. **Thread 0** writes again → must **invalidate** Core 1's copy
4. Repeat... cache line "ping-pongs" between cores

Each invalidation costs ~40-100 cycles.

## Padding

Ensure each thread's data is on its own cache line:

```c
struct {
    uint64_t count;
    char pad[56];  // Pad to 64 bytes
} counters[8];
```

No sharing = no coherency traffic.

## Results (16 MB = 167M iterations/thread)

| Variant | Total time | ns/op | Speedup |
|---------|------------|-------|---------|
| `fs_bad` (packed) | 57.8 ms | 0.34 ns | 1.0× |
| `fs_good` (padded) | 6.8 ms | 0.04 ns | **8.5×** |

## Why 8.5× Faster?

Packed version spends most time in coherency stalls - 8 threads contending for 1 cache line, each increment requires exclusive ownership.

Padded version has zero coherency traffic - each core owns its cache line exclusively.

## Real-World Occurrences

1. **Counters/statistics**: Thread-local counters in a global array
2. **Locks**: Multiple locks packed in same cache line
3. **Work queues**: Head/tail pointers updated by different threads

## Detection

```bash
perf c2c record ./bench fs_bad 16
perf c2c report
```

Look for "Shared Data Cache Line" events and high "Snoop" counts.

## Solutions

1. **Padding**: Add dummy bytes to force cache line boundaries
2. **Alignment**: Use `__attribute__((aligned(64)))`
3. **Thread-local storage**: `__thread` or `thread_local`

## Running

```bash
./bench fs_bad 16   # False sharing (packed)
./bench fs_good 16  # No false sharing (padded)
```

