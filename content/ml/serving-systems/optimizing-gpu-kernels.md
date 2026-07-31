---
title: Optimizing GPU Kernels
aliases:
  - llm-serving-systems/optimizing-gpu-kernels
category: Machine Learning Systems
tags:
  - gpu
  - kernel
  - optimization
  - cuda
  - triton
date: 2025-05-25
updated: 2026-07-30
status: needs-review
description: The four core kernel optimizations (coalescing, shared memory, bank conflict avoidance, divergence control) worked through three case studies, matrix transpose, parallel reduction, and tiled GEMM.
sources:
  - title: CSE 599K, LLM Serving Systems, University of Washington, Spring 2025 (lecture notes)
    type: lecture
  - title: CUDA C++ Programming Guide
    url: https://docs.nvidia.com/cuda/cuda-c-programming-guide/
    type: docs
---

## Purpose

This note works through the standard GPU kernel optimizations using three case studies: matrix transpose, parallel reduction, and GEMM. Start with [[ml/serving-systems/gpu-basics|GPU Architecture and Programming]] for the hardware model, then use [[ml/serving-systems/performance-modeling|Performance Modeling]] or the compact [[ml/serving-systems/roofline-reference|Roofline reference]] to identify which resource limits a given kernel.

These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025, taught by Prof. Baris Kasikci with TA Kan Zhu. The transpose timings below come from the course demo (an 8192x8192 FP32 transpose); the slides do not record the exact GPU or driver, so treat absolute numbers as indicative and the relative improvements as the real lesson.

## The memory hierarchy sets the rules

Kernel optimization is mostly about which memory you touch and in what pattern. The hierarchy (H100-class numbers, per lecture):

- Global memory: 80 GB at ~3 TB/s
- L2 cache: 50 MB at ~10 TB/s
- Shared memory / L1: 228 KB per SM at ~20 TB/s
- Registers: 64K x 32-bit per SM at ~600 TB/s

Each level buys roughly an order of magnitude in bandwidth. The four techniques that follow are all ways of moving work up this hierarchy or making a level deliver its rated bandwidth:

1. Coalesced global loading
2. Shared memory as a staging buffer
3. Bank conflict avoidance
4. Branch divergence minimization

## Case study 1: matrix transpose

The transpose is a pure data-movement kernel, so it isolates the memory techniques. Reads are row-major, writes are column-major, and one of the two will fight the hardware unless you restructure the access pattern. Total traffic for 8192x8192 FP32 is $8192^2 \times 4 \times 2 \approx 537$ MB per pass, which converts each timing below into an achieved bandwidth.

### V0: PyTorch baseline

`x.t()` only flips strides; `.contiguous()` performs the actual movement. Measured: 0.561 ms, about 956 GB/s, roughly a third of what the memory system can do.

### V1: row-wise partitioning

One block per row, each thread handling a slice of columns (the naive kernel written out in [[ml/serving-systems/how-to-write-a-fast-kernel|How to write a fast kernel]]). Measured: 3.65 ms, worse than PyTorch. The profiler blames uncoalesced global accesses: 117,440,512 excess sectors, 88% of total traffic wasted.

### V2: coalesced reads

Inside one warp, accesses to contiguous addresses coalesce into one or a few memory transactions. Reassigning threads so consecutive threads read consecutive addresses brings the time to 1.40 ms. The writes to the output are still strided by a full column, so 58,720,256 excess sectors remain (78% of total).

### V3: tiles through shared memory

You cannot make both sides of a transpose coalesce against global memory directly, so stage tiles in shared memory: read a tile row-wise (coalesced), transpose it inside shared memory, write it out row-wise in the transposed layout (also coalesced). Discontinuous access hurts far less in shared memory than in global memory. Measured: 312 us. The profiler now reports a 33-way bank conflict across 524,288 shared loads.

Shared memory can be allocated statically or dynamically:

```cpp
// static, up to 48 KB
__shared__ float f_array[10];

// dynamic, up to 228 KB (needs cudaFuncSetAttribute above 48 KB)
extern __shared__ int shared_mem[];
my_kernel<<<grid, block, shared_mem_size_in_bytes>>>(...);
```

### V4: padding away bank conflicts

Shared memory is divided into 32 banks, with consecutive 4-byte words striped across banks round-robin. When multiple threads in a warp hit different addresses in the same bank, the accesses serialize. A transposed tile column maps every element to the same bank when the tile width is a multiple of 32, which is exactly the 32-way conflict V3 shows. Padding each tile row by one element shifts consecutive rows to different bank offsets and breaks the pattern. Measured: 280 us, about 1.9 TB/s, a 13x improvement over V1.

## Branch divergence

Threads in a warp execute the same instruction stream. When a warp hits a branch where some threads take the `if` side and others the `else` side, the hardware runs both paths and masks out the inactive threads, so divergent code pays for every path any thread takes. Structure algorithms so that whole warps take the same branch whenever possible.

## Case study 2: parallel reduction

Reduce an array with an associative operation (sum, max, min):

```text
for element in array:
    temp = op(temp, element)
```

The parallel version is a tree: 8 elements to 4 partials to 2 to 1, in $\log n$ steps. The classic sequence of implementations fixes one problem at a time:

1. Interleaved addressing: thread $i$ works when $i \bmod 2^N = 0$, with stride $2^{N-1}$. Every other thread in a warp idles, severe branch divergence.
2. Better access patterns: reindex so active threads are contiguous, which improves coalescing but keeps some divergence.
3. Sequential addressing: start with a large stride and halve it (stride 8, 4, 2, 1). Active threads stay contiguous and bank conflicts disappear.
4. Load two elements per thread: each thread does a first add during the load, halving the block count for the same data.
5. Load even more elements per thread: raises memory utilization per thread, but fewer blocks means fewer SMs have work, so occupancy eventually drops. There is a sweet spot rather than a monotone win.

## Case study 3: GEMM

For $C = AB$ with $A$ of size $M \times K$ and $B$ of size $K \times N$, each output element consumes a row and a column, $2K$ elements. Computed naively that is $2MNK$ element loads while the unique data is only $MK + NK$. The gap is the caching opportunity.

Tiling loads blocks of $A$ ($T_M \times K$ strips) and $B$ ($K \times T_N$ strips) through shared memory and reuses them across a $T_M \times T_N$ output tile. Total loads become

$$L = \frac{T_M + T_N}{T_M \cdot T_N} \cdot MNK$$

so doubling tile dimensions roughly halves memory traffic, until shared memory and register capacity cap the tile size.

Modern GEMMs layer this tiling: a thread block owns a large output tile, each warp owns a medium tile, and tensor cores execute the innermost small GEMMs (shapes like 16x8x16). A tensor core is a hardware unit that a full warp drives collectively, supporting several data types at different rates; the lecture quotes up to 256x throughput over FP32 CUDA cores for the fastest types. Whether a given matmul can actually saturate them is a roofline question, covered in [[ml/serving-systems/performance-modeling|Performance Modeling]].

## Libraries to reach for first

Hand-writing kernels is the last resort. The standard library stack:

- cuBLAS: NVIDIA's closed-source GEMM library, the default answer for dense matmul.
- CUTLASS: open-source template GEMM library when you need a custom epilogue or data type.
- FlashInfer: attention kernels for serving (fused softmax, discontinuous GEMV).
- CUB: warp-, block-, and device-level primitives (reductions, scans, sorts).
- RAFT: vector search, clustering, top-k.

## Calling a custom kernel from Python

Pybind11 plus the torch extension machinery wraps a CUDA kernel for PyTorch:

```cpp
#include <pybind11/pybind11.h>
#include <torch/torch.h>
#include <torch/extension.h>
#include <cuda_runtime.h>

__global__ void add_kernel(int *a, int *b, int *c, size_t num) {
    int block_start = blockIdx.x * blockDim.x;
    int thread_id = threadIdx.x;
    int index = block_start + thread_id;
    if (index < num) {
        c[index] = a[index] + b[index];
    }
}

torch::Tensor add(torch::Tensor a, torch::Tensor b) {
    auto num = a.size(0);
    auto c = torch::empty_like(a);

    int threads_per_block = 256;
    int blocks_per_grid = (num + threads_per_block - 1) / threads_per_block;

    add_kernel<<<blocks_per_grid, threads_per_block>>>(
        a.data_ptr<int>(), b.data_ptr<int>(), c.data_ptr<int>(), num);
    cudaDeviceSynchronize();
    return c;
}

PYBIND11_MODULE(my_addition, m) {
    m.def("add", &add, "Add two tensors");
}
```

## Related notes

- [[ml/serving-systems/gpu-basics|GPU Architecture and Programming]]
- [[ml/serving-systems/how-to-write-a-fast-kernel|How to write a fast kernel]]
- [[ml/serving-systems/triton|Triton]]
- [[ml/serving-systems/performance-modeling|Performance Modeling]]
