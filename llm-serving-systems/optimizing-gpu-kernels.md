---
title: Optimizing GPU Kernels
category: Machine Learning Systems
tags: gpu, kernel, optimization, cuda, triton
description: How to write high-performance GPU kernels using CUDA and Triton, with practical examples and optimization techniques.
---

# GPU Kernel Optimizations
> Disclaimer: These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025 instructed by both Prof. Baris Kasikci and TA Kan Zhu

## GPU Architecture Recap
- Memory hierarchy with varying capacities and bandwidths:
  - Global Memory (80GB): ~3TB/s
  - L2 Cache (50MB): ~10TB/s
  - Shared Memory/L1 Cache (228 KB): ~20TB/s
  - Registers (64K * 32 Bit): ~600TB/s
- Streaming Multiprocessors (SMs) contain cores, registers, and shared memory

## GPU Programming Model

| Concept | Definition | Corresponding Architecture | Communication | Limits |
|---------|------------|---------------------------|---------------|--------|
| Thread | Minimal units that execute instructions | Functional units | Local | Up to 255 registers |
| Warp | Group of Threads | "SM tiles" | Register file | 32 threads |
| Thread Blocks | Group of Warps | SM | Shared memory | Up to 32 warps (1024 threads) |
| Kernel | Function on GPU | GPU | L2 / Global memory | Up to (2^32-1)^3 Blocks |

## Triton Framework
- **What is Triton?** A compiler framework from OpenAI for high-performance kernels with reduced human inputs
  - Python interface
  - Automated thread management
  - High performance
- **Why Triton?**
  - Write customized kernels easily
  - Higher performance than PyTorch for complex kernels
- Triton composes kernels at the block level
- Provides useful primitives: `tl.load`, `tl.store`, `tl.min`, etc.

## CUDA
- **What is CUDA?**
  - Bare-bone GPU programming
  - One-to-one mapping to the hardware
  - Highest performance
  - Heavy implementation burden

- **Memory Management in CUDA**
  - Allocation and deallocation:
    - `cudaMalloc` -> device memory allocation
    - `cudaMallocHost` -> pinned host memory allocation
    - `cudaFree` -> free memory
  - Memory movement and setting:
    - `cudaMemcpy` -> synchronize copy
    - `cudaMemcpyAsync` -> asynchronize copy
    - `cudaMemset` -> synchronize set
    - `cudaMemsetAsync` -> asynchronize set

- **CUDA Kernels**
  - Declaring a kernel: `__global__ void kernel_name(args...)`
  - Declaring a device helper function: `__device__ T helper_name(args...)`
  - Args are on the host
  - Pointers to device memory also reside in the host
  - Inside a kernel, args (basic types) can be used and device pointers can be dereferenced

- **Launching a Kernel**
  - Defining block shapes: `dim3 block(x,y,z)`
  - Defining thread shapes: `dim3 thread(x,y,z)`
  - Launching kernels: `kernel_name<<<block, thread>>>(args);`

- **Synchronization and Error Checking**
  - Thread synchronization: `__syncthreads()` -> device function
  - Block synchronization: Usually not feasible, except for cooperative launch
  - Device synchronization: `cudaDeviceSynchronize()` -> host function
  - Error checking: `cudaGetLastError()`, `cudaGetErrorString()`

- **Additional CUDA Features in Modern GPUs**
  - Unified memory address (P100+)
  - NvLink (P100+)
  - Clusters (H100+)
  - TMA (H100+)
  - NVSHARP (H100+)
  - FP4 and FP6 (B100+)

## GPU Optimization Techniques

### How to Write Fast Kernels
Four key optimization strategies:
1. Coalesced Global Loading
2. Using Shared Memory
3. Avoiding Bank Conflicts
4. Avoiding Branch Divergence

### Matrix Transpose Example
- **Problem**: When transposing a matrix, memory access patterns change from row-major to column-major

- **V0: Torch Implementation**
  - `x.t()` will not actually perform the transpose
  - Must use `contiguous()`
  - Performance: 0.561 ms, 956 GB/s -> 1/3 of optimal

- **V1: Row-wise Partitioning**
  - Each thread handles elements from one row
  - Performance: 3.65 ms
  - Issue: Uncoalesced global accesses

- **V2: Global Memory Coalescing**
  - Inside one warp, if memory access addresses are contiguous, memory access is coalesced (batched)
  - Data can be retrieved from global memory in one or a few transactions
  - Performance: 1.40 ms
  - Issue: Uncoalesced writes to output matrix

- **V3: Tilewise Partitioning**
  - Load small tiles into shared memory
  - Reading discontinuously from shared memory doesn't significantly affect performance
  - Performance: 312 mus
  - Issue: Bank conflicts

- **V4: Padding Shared Memory**
  - Add padding to shared memory to avoid bank conflicts
  - Performance: 280 mus, 1.9TB/s

### Bank Conflicts
- Shared memory is divided into banks (typically 32)
- If multiple threads in a warp access the same bank, accesses are serialized
- Bank conflicts occur when threads access different addresses in the same bank
- Solutions:
  - Padding shared memory
  - Rearranging memory access patterns

### Branch Divergence
- Threads in a warp always execute the same instructions
- If a warp has both threads that need to execute the 'if' path and threads that need to execute the 'else' path, all threads will execute both paths
- The warp explores all paths and then uses a mask to determine outputs
- For optimal performance, minimize branch divergence within a warp

## Reduction Problem
- **Definition**: Combine elements using an operation (sum, max, min, etc.)
- Example: `for elements in array: temp = op(temp, element)`

### Parallel Reduction Optimizations
1. **Reduction #1**: Basic parallel reduction with divergent branching
2. **Reduction #2**: Better access patterns to improve coalescing
3. **Reduction #3**: Sequential addressing to eliminate bank conflicts
4. **Reduction #4**: Load multiple elements per thread
5. **Reduction #5**: Load even more elements per thread

- **Trade-off**: More elements loading means higher memory utilization, but number of blocks reduces, and GPU utilization goes down

## GEMM (General Matrix Multiplication)
- **Memory Load Challenge**:
  - For every output element: Load one row + one column = 2K elements
  - Total memory load = 2MNK
  - Unique load is only MK + NK
  - Need to cache efficiently

- **GEMM Tiling**:
  - Load data in tiles to reduce memory accesses
  - Input: TILE_M * TILE_K
  - Weight: TILE_K * TILE_N
  - Output: TILE_M * TILE_N
  - Memory load reduced by a factor of tile dimension

- **Tensor Core**:
  - Special hardware unit that performs small shape GEMM
  - A warp (32 threads) collectively uses the tensor core
  - Different data types supported with different speeds (FP16, TF32, FP64, etc.)

# Matrix Transpose Kernel Case Study

## Problem Setup
- Transform a 4	imes4 matrix from row-major to column-major layout
- Input: `[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]`
- Output: `[0,4,8,12,1,5,9,13,2,6,10,14,3,7,11,15]`

## Transpose V1: Row-wise Partitioning
- **Performance**: 3.65 ms
- **Problem**: Uncoalesced global accesses
  - **Uncoalesced Global Accesses**: 117,440,512 excessive sectors (88% of total)
  - Branch efficiency: 100%, but poor memory access pattern

## Transpose V2: Global Memory Coalescing
- **Key Concept**: Inside one warp, if memory access addresses are contiguous, the memory access is coalesced (batched)
- **Performance**: 1.40 ms (significant improvement)
- **Remaining Issue**: Uncoalesced writes to output matrix
  - Still has 58,720,256 excessive sectors (78% of total)

## Transpose V3: Tilewise Partitioning with Shared Memory
- **Strategy**: Use shared memory as intermediate buffer
- **Key Insight**: Reading discontinuously from shared memory doesn't significantly affect performance
- **Performance**: 312 mus
- **New Problem**: Bank conflicts
  - **Bank Conflict Rate**: 33.0-way bank conflict across 524,288 shared load requests

### Shared Memory Allocation Methods

#### Static Allocation
```cpp
__shared__ float f_array[10];
```
- Easier to use
- Fixed size, up to 48 KB

#### Dynamic Allocation
```cpp
extern __shared__ int shared_mem[];
// Launch kernel with:
my_kernel<<<grid, block, shared_mem_size_in_bytes>>>
```
- Up to 228 KB
- Requires `cudaFuncSetAttribute()` for sizes > 48KB

## Understanding Bank Conflicts

**Bank Structure**: Shared memory is organized into banks (typically 32 banks)
- Elements are distributed across banks in round-robin fashion
- **Conflict occurs** when multiple threads in a warp access different addresses in the same bank
- **No conflict** when threads access the same address or different banks

## Transpose V4: Padding to Avoid Bank Conflicts
- **Solution**: Add padding to shared memory arrays
- **Result**:
  - **Performance**: 280 mus
  - **Bandwidth**: 1.9 TB/s
- **Key Principle**: Padding shifts memory access patterns to avoid systematic bank conflicts

---

# Reduction Kernel Case Study

## Reduction Problem Definition
- **Goal**: Apply associative operation across array elements
- **Examples**: Sum, Max/Min operations
- **Pattern**:
```
for elements in array:
    temp = op(temp, element)
```

## Parallel Reduction Strategy
Instead of sequential reduction, use tree-like parallel reduction:
- Step 1: 8 elements 	o 4 partial results
- Step 2: 4 partial results 	o 2 partial results
- Step 3: 2 partial results 	o 1 final result

## Reduction Implementation Variants

### Reduction #1: Interleaved Addressing
- **Pattern**: `threadID % 2^N == 0` does the work
- **Offset**: `2^(N-1)`
- **Problem**: Severe branch divergence

### Branch Divergence in CUDA
**Key Concept**: Threads in a warp always execute the same instructions
- GPU explores all code paths and uses masks to determine outputs
- **Divergent warps**: Some threads active, others idle
- **Performance Impact**: Redundant operations reduce efficiency

### Reduction #2: Sequential Access Pattern
- **Improvement**: Better access patterns
- **Still has**: Some branch divergence issues

### Reduction #3: Sequential Accesses
- **Key Insight**: Start with larger stride and work down
- **Benefit**: Eliminates bank conflicts
- **Access Pattern**: Stride 8 	o Stride 4 	o Stride 2 	o Stride 1

### Reduction #4: Load Two Elements
- **Optimization**: Each thread loads and processes multiple elements
- **Benefit**: Better memory utilization

### Reduction #5: Load More Elements
- **Trade-off**: Higher memory utilization vs. reduced GPU occupancy
- **Challenge**: Fewer blocks means lower overall GPU utilization

---

# GEMM (General Matrix Multiply) Optimization

## GEMM Memory Access Pattern
For matrices of size M	imesK and K	imesN:
- **Per output element**: Load one row + one column = 2K elements
- **Total memory loads**: 2MNK
- **Unique loads**: Only MK + NK
- **Problem**: Massive redundancy in memory access

## GEMM Tiling Strategy
**Load by Tiles**:
- Input tile: `TILE_M 	imes K`
- Weight tile: `K 	imes TILE_N`
- Output tile: `TILE_M 	imes TILE_N`

**Memory Load Reduction**:
$$L = \frac{Tile_M + Tile_N}{Tile_M \cdot Tile_N} \cdot MNK$$

**Key Benefit**: L2 cache access reduced by factor of tile dimensions

## Tensor Cores

**Definition**: Special hardware units that perform small GEMM operations
- **Usage**: One warp (32 threads) collectively uses tensor core
- **Shapes**: Various supported (16	imes8	imes16, 8	imes8	imes4, etc.)
- **Performance**: Up to 256	imes speedup over F32 CUDA cores for specific data types

### GEMM Hierarchy
- **Thread Block**: Handles large tile
- **Warp**: Handles medium tile
- **Tensor Core**: Handles small GEMM (e.g., 16	imes8	imes16)

---

# High-Performance Kernel Libraries

## Essential Libraries

### **cuBLAS**
- Closed-source GEMM library
- Highly optimized by NVIDIA

### **CUTLASS**
- Open-source template-based GEMM library
- Customizable and extensible

### **Raft**
- Vector Search, Clustering, Top-K, Sort operations

### **FlashInfer**
- Attention kernels (Fused Softmax, Discontinuous GEMV)

### **CUB**
- Templates for basic operations at Warp, Block, and Device level

---

# Python Integration

## Pybind11 for CUDA Kernels

**Basic Pattern**:
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

## Key Optimization Principles Summary

1. **Memory Coalescing**: Ensure contiguous memory access within warps
2. **Shared Memory**: Use as high-speed cache for frequently accessed data
3. **Bank Conflict Avoidance**: Pad shared memory arrays when necessary
4. **Branch Divergence Minimization**: Structure algorithms to keep warps synchronized
5. **Occupancy vs Efficiency**: Balance thread utilization with per-thread work
6. **Hierarchical Tiling**: Optimize for different levels of memory hierarchy