---
title: Streaming Data
aliases:
  - performance-engineering/streaming
category: Performance Engineering
tags:
  - streaming
  - memory
  - bandwidth
  - throughput
  - performance
  - data-processing
date: 2024-12-08
updated: 2026-07-30
status: evergreen
description: A working model for streaming data processing, covering memory bandwidth limits, page-based memory budgets for common file formats, parallelism strategies, syscall overhead, and zero-copy I/O.
sources:
  - title: Apache Parquet documentation
    url: https://parquet.apache.org/docs/
    type: docs
  - title: Node.js stream documentation
    url: https://nodejs.org/api/stream.html
    type: docs
  - title: io_uring(7) man page
    url: https://man7.org/linux/man-pages/man7/io_uring.7.html
    type: docs
  - title: sendfile(2) man page
    url: https://man7.org/linux/man-pages/man2/sendfile.2.html
    type: docs
---

## Purpose

This note builds a model for reasoning about streaming workloads: when the bottleneck is memory bandwidth versus processing, how much memory a stream actually needs for common file formats, and where the operating system costs hide. The cache-line effects behind the bandwidth examples are measured directly in the [[systems/performance/streaming_benchmarks/cache_line_efficiency/README|Cache Line Efficiency Benchmark]].

Streaming is a super common technique. The basic idea is you can't fit the entire dataset in memory, so you process it in a stream of chunks. For example, say we're uploading a massive file to cloud storage like S3. We don't want to read the entire thing into memory and then pipe it out into the network. We'd be waiting to buffer the entire file while the upload is the real bottleneck, filling up all our memory, getting higher end-to-end latency and a higher memory footprint at the same time.

A lot of the time you can rely on libraries to do this for you, like Node.js `stream` or the Java `Stream` APIs. These are usually efficient and well optimized, but it's still fun, and sometimes necessary, to think about what's going on under the hood.

The metrics I'll focus on the most are throughput and memory usage. It turns out to be pretty natural to think about processing streams of data in terms of bytes per second and peak memory footprint.

## A basic model of streaming

Every streaming workload has a bottleneck, and it lands in one of two places:

- Bottlenecked by processing: each byte of input takes long-running work with significant latency, resource usage, or contention that limits parallelism. Processing a file from disk with heavy per-record business logic looks like this. Here you optimize the business logic, since the processing dwarfs the time spent on the streaming machinery itself.
- Bottlenecked by I/O: the per-byte work is cheap, so the raw movement of data dominates, and any overhead in the data path matters a lot.

Being bottlenecked by processing means you can probably just use a library for the actual streaming and skip micro-optimizing it. Being bottlenecked by I/O is more interesting.

Say you're reading a dataset from memory, transforming it $n$ times, and writing results back. That's $n + 2$ memory operations per byte of input (read original, write temporaries, write result). Under an idealized bandwidth model with memory bandwidth $B$ (GB/s), the effective rate is approximately $B / (n + 2)$. The upper bound for a simple copy is about $B / 2$, one read plus one write. Real systems land below this due to caches, NUMA, contention, and software overheads.

What determines $B$? Peak bandwidth is hard to approach in practice. Modern CPUs move data in cache lines (typically 64 B), and access pattern dominates:

- `seq8`: Sequential scan that touches only 8 B per 64 B line. Hardware prefetchers can keep lines flowing, but most of each line is unused, so effective bandwidth tracks the fraction consumed (~1/8 of peak).
- `seq64`: Sequential scan consuming the whole 64 B line (e.g., via `memcpy`). Every byte brought in from DRAM is used, so measured throughput can approach the platform's sustained memory bandwidth.
- `rand8`: Random pointer chasing with one dependent 8 B load per line. With little prefetch and limited outstanding misses, throughput is latency-bound and much lower than sequential scans.

Example relative outcomes (not absolute; highly system-dependent, measured in the [[systems/performance/streaming_benchmarks/cache_line_efficiency/README|benchmark]]):

| Pattern | Relative throughput |
|---------|---------------------|
| `seq64` | ~1.0x (approaches peak) |
| `seq8`  | ~0.125x (fraction of line used) |
| `rand8` | << 0.01x (latency-bound) |

## Streaming is like sequential pagination

At its core, streaming is sequential pagination where you process pages in order and discard them immediately. That constraint, sequential access with no retention, is what lets you process datasets larger than memory.

Traditional pagination lets you process pages in any order. REST APIs often include metadata that lets you request an arbitrary page, e.g. `?page=10`. Random access is nice, but without hash indexes or B-trees behind it, serving an arbitrary page means scanning through the dataset.

> Some implementations of pagination rely on pointers to the next or previous page, which is closer to streaming.

Streaming removes these freedoms. You process one page at a time in the order they arrive, then discard.

Either way, the memory requirement drops from O(total_dataset_size) to O(page_size). Streaming additionally needs no lookup or index structure, since it only ever touches sequential parts of the data. In many cases the input is a huge file, and processing it in the order it sits on disk gets you the `seq64`-style bandwidth from the table above for free.

## File formats

Each format defines its page size differently:

- **Parquet**: Pages are row groups ([default 128 MB uncompressed](https://parquet.apache.org/docs/))
- **CSV**: Pages are lines or batches of lines (e.g. 1000 lines)
- **Arrow**: Pages are record batches (user-defined, often 64K records)

The memory required for streaming is the page size times the number of concurrent pages being processed, plus any overhead for decompression or parsing.

**Apache Parquet** uses row groups as its unit of I/O. The default row group size is 128 MB of uncompressed data. With Snappy compression at a typical 2-3x ratio, that's 43-64 MB on disk. To process one row group you need:

- Compressed row group in memory: 64 MB
- Decompression buffer: 128 MB
- Decoded values buffer: 128 MB (Parquet stores definition levels, repetition levels, and values separately)

That works out to around 320 MB of working memory for a 64 MB disk chunk. If your schema has nested columns or variable-length strings, add another 1-2x for materialization.

**CSV** processes line by line. A typical CSV row with 20 columns might be 200 bytes (illustrative; actual sizes vary widely). With a read buffer of 8 KB, you're holding 40 rows in memory at once. Working memory is your buffer size plus parsing overhead, call it 16 KB total.

**Apache Arrow** uses a columnar memory layout that matches its on-disk format exactly. A column of 1 million 64-bit integers takes 8 MB on disk and 8 MB in memory. No decompression, no intermediate buffers. The memory requirement is exactly the size of the columns you're actively processing.

For a 1 GB file with 10 million rows and 20 columns:

- Parquet: 320 MB working memory per row group, times the number of concurrent row groups
- CSV: 16 KB for streaming, or full file size if loaded entirely
- Arrow: exactly the size of accessed columns (selective column reading is free)

## Algorithms

Consider a simple streaming pipeline that parses JSON, filters records, enriches with external data, and aggregates results. We can calculate the theoretical throughput limits.

Each algorithmic approach is really a different pagination strategy:

- **Pipeline parallelism**: One page flows through all stages sequentially
- **Data parallelism**: Multiple pages processed simultaneously, one per worker
- **Batch processing**: Accumulate many pages, then process as a group

The streaming constraint (sequential processing, immediate disposal) limits us to the first two, though in practice you'd likely combine them using windowing.

**Pipeline parallelism** processes one record through all stages sequentially. Suppose the stages take:

- Parse: 50 μs
- Filter: 5 μs
- Enrich: 200 μs
- Aggregate: 20 μs

Total latency is 275 μs per record, but throughput is limited by the slowest stage: $1 \div 200\ \mu s = 5{,}000$ records/second. The other stages spend most of their time waiting.

**Data parallelism** runs the complete pipeline on different data chunks. With 8 workers:

- Throughput: $8 \times 5{,}000 = 40{,}000$ records/second
- Memory: $8 \times$ working set size
- Coordination overhead: atomic counters, locks, or channels for aggregation

The coordination becomes critical. If workers need to synchronize for aggregation (e.g. a global sum), that stage bottlenecks the whole pipeline. Applying Amdahl's law: if 5% of your work is serial, maximum speedup is $1 \div 0.05 = 20x$ regardless of worker count.

**Windowing** introduces time-based memory requirements. A time-based window has a memory footprint of $W \times T \times R$, where $W$ is the window size in seconds, $T$ is the throughput in records/second, and $R$ is the record size in bytes. For example, a window of 10 seconds at 5,000 records/second needs to buffer 50,000 records. At 200 bytes per record, that's 10 MB.

## Linux I/O overhead

Every `read` system call:

1. Saves user-space registers
2. Switches to kernel mode
3. Executes kernel code
4. Copies data from kernel to user buffer
5. Switches back to user mode
6. Restores registers

On modern x86-64 processors, a minimal system call (like `getpid`) is on the order of hundreds of nanoseconds depending on CPU and kernel version. I/O system calls are more expensive because they involve actual work beyond the mode switch.

Let's trace what happens with traditional `read` versus [io_uring](https://man7.org/linux/man-pages/man7/io_uring.7.html) for reading 1000 4 KB blocks:

**Traditional read():**

```c
for (int i = 0; i < 1000; i++) {
    read(fd, buffer, 4096);  // system call per read
}
// Many syscalls (O(N)); overhead scales with call count
// Total data transfer: 4MB
```

**`io_uring`:**

```c
// Setup submission queue entries
for (int i = 0; i < 1000; i++) {
    io_uring_prep_read(sqe, fd, buffer, 4096);  // Just memory writes
}
io_uring_submit(ring);  // Single system call
// Single system call; overhead roughly constant w.r.t N
// Total data transfer: 4MB
```

The gap grows with IOPS, since the per-call overhead is what gets amortized. `io_uring` adds complexity in exchange: you manage ring buffers, track completions, and handle partial reads. For simple sequential reading of large files, the overhead difference might not justify it.

**Memory mapping** (mmap) amortizes system call cost differently. One `mmap` call maps the entire file into virtual address space, and page faults bring data into memory on demand:

```c
void* data = mmap(NULL, file_size, PROT_READ, MAP_PRIVATE, fd, 0);
// No system call per read, just memory access
// But: page fault on first access to each 4KB page
```

Page fault cost is similar in magnitude to a system call, but you get cache-line-level granularity after the initial fault. For random access patterns this is often optimal. For sequential streaming, `read` with appropriate buffer sizes can trigger kernel read-ahead more effectively.

## Zero-copy: following the data path

Standard file-to-socket transfer involves multiple copies. Here's the exact path for `read` + `write`:

1. **DMA from disk to kernel buffer**: Hardware handles this, no CPU involvement
2. **CPU copy from kernel to user buffer**: `memcpy()` at memory bandwidth
3. **CPU copy from user to kernel socket buffer**: Another `memcpy()`
4. **DMA from kernel buffer to NIC**: Hardware again

For a 1 GB file, the CPU path performs two memory copies (kernel to user, user to kernel). If sustained memory bandwidth is $B_{mem}$, the copy time budget for steps 2 and 3 is roughly $2 \times 1\,GB \div B_{mem}$.

With [sendfile](https://man7.org/linux/man-pages/man2/sendfile.2.html), those two copies are eliminated:

1. DMA from disk to kernel buffer
2. Direct DMA from kernel buffer to NIC

The CPU never touches the data, which frees up memory bandwidth for other operations. The file transfer rate is then limited by the minimum of storage throughput, network throughput, and kernel path overheads rather than memory bandwidth.

## Implementations

### Java virtual threads

Java's virtual threads are user-mode threads multiplexed onto carrier threads. Each virtual thread requires only stack space for its current call chain, typically a few KB versus around 1 MB for platform threads.

```java
public class StreamProcessor {
    private static final int BUFFER_SIZE = 8192;
    private static final int MAX_CONCURRENT = 100;

    public void processLargeFile(Path inputPath, Path outputPath) throws Exception {
        try (var input = FileChannel.open(inputPath, StandardOpenOption.READ);
             var output = FileChannel.open(outputPath,
                 StandardOpenOption.WRITE, StandardOpenOption.CREATE)) {

            Semaphore backpressure = new Semaphore(MAX_CONCURRENT);
            ByteBuffer buffer = ByteBuffer.allocateDirect(BUFFER_SIZE);

            long position = 0;
            long fileSize = input.size();

            try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
                while (position < fileSize) {
                    backpressure.acquire();

                    buffer.clear();
                    int bytesRead = input.read(buffer, position);
                    if (bytesRead == -1) break;

                    buffer.flip();
                    byte[] data = new byte[bytesRead];
                    buffer.get(data);

                    long writePosition = position;
                    executor.submit(() -> {
                        try {
                            byte[] processed = transform(data);
                            ByteBuffer writeBuffer = ByteBuffer.wrap(processed);
                            output.write(writeBuffer, writePosition);
                        } catch (Exception e) {
                            // handle error
                        } finally {
                            backpressure.release();
                        }
                    });

                    position += bytesRead;
                }
            }
        }
    }

    private byte[] transform(byte[] data) {
        // transformation logic
        return data;
    }
}
```

The Semaphore limits concurrent operations to 100, preventing unbounded task creation. Direct ByteBuffers avoid JVM heap allocation and enable potential zero-copy operations.

### JavaScript stream back-pressure

[Node.js streams](https://nodejs.org/api/stream.html) use high water marks to control buffering. When a buffer fills, the stream emits 'drain' events to resume flow:

```javascript
const { Transform } = require('stream');
const fs = require('fs');

class ProcessingStream extends Transform {
    constructor(options) {
        super({
            highWaterMark: 64 * 1024  // 64KB buffer
        });
        this.activeTransforms = 0;
        this.maxConcurrent = 10;
    }

    async _transform(chunk, encoding, callback) {
        // wait if too many transforms in progress
        while (this.activeTransforms >= this.maxConcurrent) {
            await new Promise(resolve => setImmediate(resolve));
        }

        this.activeTransforms++;

        try {
            const processed = await this.processChunk(chunk);
            callback(null, processed);
        } catch (error) {
            callback(error);
        } finally {
            this.activeTransforms--;
        }
    }

    async processChunk(chunk) {
        // async processing
        return chunk;
    }
}

const input = fs.createReadStream('large.file', { highWaterMark: 64 * 1024 });
const processor = new ProcessingStream();
const output = fs.createWriteStream('output.file');

input.pipe(processor).pipe(output);
```

The 64 KB high water mark means Node buffers up to 64 KB before pausing the input stream. This prevents memory exhaustion while maintaining reasonable throughput.

### Python asyncio with bounded concurrency

Python's `asyncio` provides primitives for controlled concurrent execution:

```python
import asyncio
import aiofiles

class StreamProcessor:
    def __init__(self, max_concurrent=10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.chunk_size = 8192

    async def process_file(self, input_path, output_path):
        async with aiofiles.open(input_path, 'rb') as input_file:
            async with aiofiles.open(output_path, 'wb') as output_file:
                tasks = []
                position = 0

                while True:
                    chunk = await input_file.read(self.chunk_size)
                    if not chunk:
                        break

                    task = asyncio.create_task(
                        self.process_and_write(chunk, output_file, position)
                    )
                    tasks.append(task)
                    position += len(chunk)

                    # Process in batches to control memory
                    if len(tasks) >= 100:
                        await asyncio.gather(*tasks)
                        tasks = []

                # Process remaining tasks
                if tasks:
                    await asyncio.gather(*tasks)

    async def process_and_write(self, chunk, output_file, position):
        async with self.semaphore:
            processed = await self.transform(chunk)
            await output_file.seek(position)
            await output_file.write(processed)

    async def transform(self, data):
        # CPU-intensive work should be in thread pool
        return data.upper()

# Usage
processor = StreamProcessor(max_concurrent=20)
asyncio.run(processor.process_file('input.dat', 'output.dat'))
```

The semaphore ensures at most 20 chunks are processed concurrently. Batching tasks prevents unlimited growth of the task queue.

## Sources

- [Apache Parquet documentation](https://parquet.apache.org/docs/)
- [Node.js stream documentation](https://nodejs.org/api/stream.html)
- [io_uring(7) man page](https://man7.org/linux/man-pages/man7/io_uring.7.html)
- [sendfile(2) man page](https://man7.org/linux/man-pages/man2/sendfile.2.html)

## Related notes

- [[systems/performance/latency-throughput-and-utilization|latency, throughput, and utilization]]
- [[systems/performance/streaming_benchmarks/cache_line_efficiency/README|Cache Line Efficiency Benchmark]]
