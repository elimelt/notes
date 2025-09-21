# Streaming Data

Streaming is a super common technique. The basic idea is you can't fit the entire dataset in memory, so you process it in a stream of chunks. For example, say we're uploading a massive file to cloud storage like S3. We don't want to read the entire thing into memory, and then pipe it out into the network in what would naturally be chunks. We'd be waiting to upload the entire file (the real bottleneck), while filling up all our memory, causing higher E2E latency while also resulting in a higher memory footprint.

A lot of the time, you can rely on libraries to do this for you. For example, `Node.js` `stream`, Java `Stream` APIs, and such. Luckily, these are usually pretty efficient and optimized, but it's still fun, and sometimes necessary, to think about what's going on under the hood.

The metrics I'll focus on the most are throughput + bandwidth, and memory usage. It turns out to be pretty natural to think about processing streams of data in terms of bytes/second, and peak memory usage.

## A basic model of streaming

There are two very different scenarios, with one overarching concept (bottleneck):

- Bottlenecked by processing: We have some long-running processing of each byte of input that has significant IO/latency, and potentially a lot of resource usage/contentions, limiting our ability to parallelize. This is the case for example when we're processing a file from disk, or a network stream. In this case, we seek to optimize for throughput in our ...business logic, with little consideration for the actual latency of the streaming itself, since our processing dwarfs the time spent on our streaming setup.
- Bottlenecked by I/O: We aren't doing anything particularly expensive to our data, e.g. we read it, and then do a lot of CPU-side computation like calculating metrics. A lot of times we'll be entirely bottlenecked by the raw movement of data, making any overhead much more important.

Being bottlenecked by processing means you can probably just use a library for the actual streaming, and focus on your business logic without trying to micro-optimize the streaming itself. Being bottlenecked by I/O is more interesting:

Say you're reading a dataset from memory, transforming it `n` times, and writing results back — that's `n + 2` memory operations per byte of input (read original, write temporary, write result). Under an idealized bandwidth model with memory bandwidth `B` (GB/s), the effective rate is approximately `B / (n + 2)`. The upper bound for a simple copy is about `B / 2` (one read + one write). Real systems will be below this due to caches, NUMA, contention, and software overheads.

> What determines `B`?

It’s hard to approach peak bandwidth in practice. Modern CPUs move data in cache lines (typically 64 B), and access pattern dominates:

- `seq8`: Sequential scan that touches only 8 B per 64 B line. Hardware pre-fetchers can keep lines flowing, but most of each line is unused, so effective bandwidth tracks the fraction consumed (~1/8 of peak).
- `seq64`: Sequential scan consuming the whole 64 B line (e.g., via `memcpy`). Every byte brought in from DRAM is used, so measured throughput can approach the platform’s sustained memory bandwidth.
- `rand8`: Random pointer chasing with one dependent 8 B load per line. With little prefetch and limited outstanding misses, throughput is latency-bound and much lower than sequential scans.

Example relative outcomes (not absolute; highly system-dependent):

| Pattern | Relative throughput |
|---------|---------------------|
| `seq64` | ~1.0x (approaches peak) |
| `seq8`  | ~0.125x (fraction of line used) |
| `rand8` | << 0.01x (latency-bound) |

## Streaming Is Like Sequential Pagination

At its core, streaming is like sequential pagination where you process pages in order and discard them immediately. This constraint - sequential access with no retention - lets you process datasets larger than memory.

Traditional pagination lets you process pages in any order. For example, REST APIs often include metadata that let you request an arbitrary page, e.g. `?page=10`. This random access is nice, but without either hash-based indexes or B-trees, you're likely to spend a lot of time scanning through the dataset to get this kind of random access.

> Some implementations of pagination rely on pointers to the next or previous page, which is closer to streaming.

Streaming removes these freedoms. You get to process one page at a time in the order they come, and immediately discard them.

In either case, we reduce our memory requirement from O(total_dataset_size) to O(page_size). However, with streaming, we don't need to worry about implementing any efficient lookup/index structure, since we're just processing sequential parts of our data. In many cases we only have huge files to process, and if we can do so by processing it in the order it's stored on disk, we get lots of performance for free.

## File Formats

Each format defines its page size differently:

- **Parquet**: Pages are row groups (default 128MB uncompressed)
- **CSV**: Pages are lines or batches of lines (e.g. 1000 lines)
- **Arrow**: Pages are record batches (user-defined, often 64K records)

The memory required for streaming is the page size times the number of concurrent pages being processed, plus any overhead for decompression or parsing.

**Apache Parquet** uses row groups as its unit of I/O. The default row group size is `128MB` of uncompressed data. With Snappy compression (typical ratio of `2-3x`), that's `43-64MB` on disk. To process this, you need:

- Compressed row group in memory: `64MB`
- Decompression buffer: `128MB`
- Decoded values buffer: `128MB` (Parquet stores definition levels, repetition levels, and values separately)

Total working memory: `320MB` for a `64MB` disk chunk. If your schema has nested columns or variable-length strings, add another `1-2x` for materialization.

**CSV** processes line by line. A typical CSV row with `20` columns might be `200 bytes` (illustrative; actual sizes vary widely). With a read buffer of `8KB`, you're holding `40` rows in memory at once. Working memory is just your buffer size plus parsing overhead - call it `16KB` total.

**Apache Arrow** uses a columnar memory layout that matches its on-disk format exactly. A column of `1 million 64-bit integers` takes `8MB` on disk and `8MB` in memory. No decompression, no intermediate buffers. The memory requirement is exactly the size of the columns you're actively processing.

For a `1GB` file with `10 million rows` and `20 columns`:

- Parquet: `320MB` working memory per row group × number of concurrent row groups
- CSV: `16KB` for streaming, or full file size if loaded entirely
- Arrow: Exactly the size of accessed columns (selective column reading is free)

## Algorithms

Consider a simple streaming pipeline that parses JSON, filters records, enriches with external data, and aggregates results. We can calculate the theoretical throughput limits.

Each algorithm approach is really a different pagination strategy:

- **Pipeline parallelism**: One page flows through all stages sequentially
- **Data parallelism**: Multiple pages processed simultaneously, one per worker
- **Batch processing**: Accumulate many pages, then process as a group

The streaming constraint (sequential processing, immediate disposal) limits us to the first two, though in practice you'd likely combine them using windowing.

**Pipeline parallelism** processes one record through all stages sequentially. If stages take:

- Parse: `50μs`
- Filter: `5μs`
- Enrich: `200μs`  
- Aggregate: `20μs`

Total latency is `275μs` per record. But throughput is limited by the slowest stage: `1 ÷ 200μs = 5,000 records/second`. The other stages spend most of their time waiting.

**Data parallelism** runs the complete pipeline on different data chunks. With `8` workers:

- Throughput: `8 × 5,000 = 40,000 records/second`
- Memory: `8 × working_set_size`
- Coordination overhead: atomic counters, locks, or channels for aggregation

The coordination becomes critical. If workers need to synchronize for aggregation (e.g. a global sum), that stage bottlenecks the whole pipeline. Applying Amdahl's law: if `5%` of your work is serial, maximum speedup is `1 ÷ 0.05 = 20x` regardless of worker count.

**Windowing** introduces time-based memory requirements. A time-based window of has a memory footprint of $W \times T \times R$, where $W$ is the window size in seconds, $T$ is the throughput in records/second, and $R$ is the record size in bytes. For example, a window of `10 seconds` at `5,000 records/second` needs to buffer `50,000 records`. At `200 bytes` per record, that's `10MB`.

## Linux I/O Overhead

Every `read` system call...

1. Saves user-space registers
2. Switches to kernel mode
3. Executes kernel code
4. Copies data from kernel to user buffer
5. Switches back to user mode
6. Restores registers

On modern x86-64 processors, a minimal system call (like `getpid`) is on the order of hundreds of nanoseconds depending on CPU and kernel version. I/O system calls are more expensive because they involve actual work beyond the mode switch.

Let's trace what happens with traditional `read` versus `io_uring` for reading `1000` 4KB blocks:

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

The difference is dramatic for high-IOPS workloads. But `io_uring` adds complexity - you need to manage ring buffers, track completions, and handle partial reads. For simple sequential reading of large files, the overhead difference might not justify the complexity.

**Memory mapping** (mmap) amortizes system call cost differently. One `mmap` call maps the entire file into virtual address space. Page faults bring data into memory on demand:

```c
void* data = mmap(NULL, file_size, PROT_READ, MAP_PRIVATE, fd, 0);
// No system call per read, just memory access
// But: page fault on first access to each 4KB page
```

Page fault cost is similar in magnitude to a system call, but you get cache-line-level granularity after the initial fault. For random access patterns, this is often optimal. For sequential streaming, `read` with appropriate buffer sizes can trigger kernel read-ahead more effectively.

## Zero-Copy: Following the Data Path

Standard file-to-socket transfer involves multiple copies. Here's the exact path for `read` + `write`:

1. **DMA from disk to kernel buffer**: Hardware handles this, no CPU involvement
2. **CPU copy from kernel to user buffer**: `memcpy()` at memory bandwidth
3. **CPU copy from user to kernel socket buffer**: Another `memcpy()`
4. **DMA from kernel buffer to NIC**: Hardware again

For a `1GB` file, the CPU path performs two memory copies (kernel→user, user→kernel). If sustained memory bandwidth is `B_mem`, the copy time budget is roughly:

- Steps 2 + 3: `2 × 1GB ÷ B_mem`

With `sendfile`, those two copies are eliminated:

1. DMA from disk to kernel buffer
2. Direct DMA from kernel buffer to NIC

The CPU never touches the data. This frees up memory bandwidth for other operations. The file transfer rate is then limited by the minimum of storage throughput, network throughput, and kernel path overheads, not memory bandwidth.

## Implementations

### Java Virtual Threads

Java's virtual threads are user-mode threads multiplexed onto carrier threads. Each virtual thread requires only stack space for its current call chain - typically a few KB versus `1MB` for platform threads.

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

The Semaphore limits concurrent operations to `100`, preventing unbounded task creation. Direct ByteBuffers avoid JVM heap allocation and enable potential zero-copy operations.

### JavaScript Stream Back-pressure

`Node.js` streams use high water marks to control buffering. When a buffer fills, the stream emits 'drain' events to resume flow:

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

The `64KB` high water mark means Node buffers up to `64KB` before pausing the input stream. This prevents memory exhaustion while maintaining reasonable throughput.

### Python AsyncIO with Bounded Concurrency

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

The semaphore ensures at most `20` chunks are processed concurrently. Batching tasks prevents unlimited growth of the task queue.
