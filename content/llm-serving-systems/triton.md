---
title: GPU Kernel Programming with Triton and CUDA
category: Machine Learning Systems
tags:
  - gpu
  - triton
  - cuda
date: 2025-04-02
updated: 2026-07-30
status: draft
description: A vector addition kernel written twice, once in Triton and once in CUDA, with launch, timing, and synchronization mechanics for each.
sources:
  - title: CSE 599K, LLM Serving Systems, University of Washington, Spring 2025 (lecture notes)
    type: lecture
  - title: Triton documentation
    url: https://triton-lang.org
    type: docs
  - title: CUDA C++ Programming Guide
    url: https://docs.nvidia.com/cuda/cuda-c-programming-guide/
    type: docs
---

## Purpose

This note implements the same vector addition kernel in Triton and in CUDA to make the two programming models concrete. Triton exposes the kernel concepts from [[llm-serving-systems/gpu-basics|GPU Architecture and Programming]] at the block level and manages threads for you; [[llm-serving-systems/optimizing-gpu-kernels|Optimizing GPU Kernels]] covers how to tune the resulting programs. The code in the original lecture capture had several transcription bugs; the versions below are corrected.

## Triton

Triton programs are written per block: you compute which slice of the data your program instance owns, load it with a mask, operate, and store. The compiler handles thread mapping within the block. The runtime also pools memory rather than allocating per call, and temporaries live in the register file.

```python
import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(a_ptr, b_ptr, output_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    block_id = tl.program_id(axis=0)
    start = block_id * BLOCK_SIZE

    offsets = start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements

    a_seg = tl.load(a_ptr + offsets, mask=mask)
    b_seg = tl.load(b_ptr + offsets, mask=mask)

    tl.store(output_ptr + offsets, a_seg + b_seg, mask=mask)


def add(a, b, BLOCK_SIZE=1024):
    output = torch.empty_like(a)
    n = output.numel()
    grid = (triton.cdiv(n, BLOCK_SIZE),)
    add_kernel[grid](a, b, output, n, BLOCK_SIZE=BLOCK_SIZE)
    return output


num = 100_000_000
a = torch.rand(num, device='cuda')
b = torch.rand(num, device='cuda')

assert torch.allclose(a + b, add(a, b))

start = torch.cuda.Event(enable_timing=True)
end = torch.cuda.Event(enable_timing=True)
start.record()
for i in range(100):
    output_triton = add(a, b)
end.record()

torch.cuda.synchronize()
time_total = start.elapsed_time(end) / 1000  # seconds
# 3 global accesses per element (2 reads + 1 write), 4 bytes each
bandwidth_gbs = num * 4 * 3 * 100 / time_total / 1e9
print(f'bandwidth: {bandwidth_gbs:.1f} GB/s')
print(f'total time: {time_total} s')
```

Two mechanics worth noticing. The mask handles the ragged final block, so `n_elements` need not divide evenly by `BLOCK_SIZE`. And timing uses CUDA events with an explicit synchronize, because kernel launches return before the GPU finishes.

## CUDA

CUDA gives the same program with every decision made manually.

Memory management is explicit: `cudaMalloc`, `cudaFree`, and `cudaMallocHost` for pinned host memory; `cudaMemcpy`/`cudaMemcpyAsync` to move data and `cudaMemset`/`cudaMemsetAsync` to set it.

Kernel basics:

- Declare a kernel: `__global__ void kernel_name(args...)`
- Declare a device helper: `__device__ void helper_name(args...)`
- Arguments live on the host; pointers to device memory are host-side values that the kernel dereferences on the device.

Launching:

- Block shape: `dim3 block(dim_x, dim_y, dim_z)`
- Thread shape: `dim3 thread(thread_x, thread_y, thread_z)`
- Launch: `kernel_name<<<block, thread>>>(args...)`

Synchronization and errors:

- Thread synchronization within a block: `__syncthreads()` (device function)
- Block-to-block synchronization: generally not possible inside a kernel, except with cooperative launch
- Device synchronization: `cudaDeviceSynchronize()` (host function)
- Error handling: `cudaGetLastError()`, `cudaGetErrorString()`

The full addition program:

```cpp
#include <cuda_runtime.h>
#include <stdio.h>

#define BLOCK_SIZE 256

__global__ void addition(int *a, int *b, int *c, int num) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < num) {
        c[idx] = a[idx] + b[idx];
    }
}

int main() {
    int num = 100000000;
    int *a, *b, *c;
    int *d_a, *d_b, *d_c;

    int size = num * sizeof(int);

    a = (int *)malloc(size);
    b = (int *)malloc(size);
    c = (int *)malloc(size);

    cudaMalloc(&d_a, size);
    cudaMalloc(&d_b, size);
    cudaMalloc(&d_c, size);

    for (int i = 0; i < num; i++) {
        a[i] = i;
        b[i] = i;
    }

    cudaMemcpy(d_a, a, size, cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, b, size, cudaMemcpyHostToDevice);

    // Launch kernel
    dim3 grid((num + BLOCK_SIZE - 1) / BLOCK_SIZE);
    dim3 block(BLOCK_SIZE);
    addition<<<grid, block>>>(d_a, d_b, d_c, num);
    cudaDeviceSynchronize();

    // check for errors
    cudaError_t error = cudaGetLastError();
    if (error != cudaSuccess) {
        fprintf(stderr, "ERROR: %s\n", cudaGetErrorString(error));
        return 1;
    }

    // Copy output
    cudaMemcpy(c, d_c, size, cudaMemcpyDeviceToHost);

    // validate output
    for (int i = 0; i < num; i++) {
        if (c[i] != a[i] + b[i]) {
            printf("Error at %d\n", i);
            break;
        }
    }
}
```

Compile and run with `nvcc`:

```sh
# compile
nvcc addition.cu -o addition

# run
./addition
```

## Tuning knobs

Things to try when the naive version is slow: larger block sizes, more blocks, and more elements per thread. The systematic treatment of these tradeoffs (coalescing, shared memory, bank conflicts, occupancy) is in [[llm-serving-systems/optimizing-gpu-kernels|Optimizing GPU Kernels]].

## Newer CUDA features

By hardware generation: unified memory addressing and NVLink (P100+), thread block clusters and TMA (H100+), NVLink SHARP (H100+), FP4 and FP6 (B100+).

## Related notes

- [[llm-serving-systems/gpu-basics|GPU Architecture and Programming]]
- [[llm-serving-systems/optimizing-gpu-kernels|Optimizing GPU Kernels]]
- [[llm-serving-systems/how-to-write-a-fast-kernel|How to write a fast kernel]]
