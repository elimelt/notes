# Cache Line Efficiency Benchmark

- **seq8**: Sequential scan, reading only 8 B from each 64 B cache line. Implemented with a single load per line, averaged over multiple passes on a 1 GB buffer. Hardware prefetchers stream lines efficiently, but effective bandwidth is reduced to \~1/8 of peak because most of each line is unused.
- **seq64**: Sequential scan, reading the full 64 B line via a single vectorized load (`memcpy`). Same 1 GB buffer, averaged. Every byte brought in from DRAM is consumed, so effective bandwidth reflects near-peak memory throughput (\~55 GB/s).
- **rand8**: Random pointer chase with one dependent 8 B load per line across the same 1 GB buffer. No prefetching, no overlap; throughput collapses to \~70 MB/s, set by memory latency and the limit on outstanding misses.

```bash
$ system_profiler SPMemoryDataType

Memory:

      Memory: 24 GB
      Type: LPDDR5
      Manufacturer: Hynix
```

## How to run

```bash
make run
```