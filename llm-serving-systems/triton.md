---
title: GPU Kernel Programming with Triton and CUDA
category: Systems
tags: gpu, triton, cuda
description: Overview of programming GPU kernels with Triton and CUDA
---

# Triton

Avoids allocating and deallocating lots of memory, and instead uses a single memory pool for all allocations and uses register file for temporary storage.

```py
import torch
import triton
import triton.language as tl

@triton.jit # JIT compile the function
def add_with_triton(a, b, output, n_elements, BLOCK_SIZE: tl.constexpr):
    DIM = 0
    block_id = yl.program_id(DIM)
    start = block_id * BLOCK_SIZE

    offset = tl.arrange(DIM, BLOCK_SIZE) + start
    mask = offset < n_elements

    a_seg = tl.load(a + offset, mask=mask)
    b_seg = tl.load(b + offset, mask=mask)
    output_seg = a_seg + b_seg

    tl.store(output + offset, output_seg, mask=mask)

@triton.jit
def add_with_triton_grid(a, b, output, n_elements, BLOCK_SIZE: tl.constexpr):
    output = torch.empty_like(a)


num = 100000000
a = torch.rand(num, device='cuda')
b = torch.rand(num, device='cuda')

output_torch = a + b
output_triton = add_with_triton(a, b, num, BLOCK_SIZE=1024)

assert torch.allclose(output_torch, output_triton)

start = torch.cuda.Event(enable_timing=True)
end = torch.cuda.Event(enable_timing=True)
start.record()
for i in range(100):
    output_triton = add_with_triton(a, b, num, BLOCK_SIZE=1024)
end.record()

torch.cuda.synchronize()
time_total = start.elapsed_time(end) / 1000
print("with triton")
print(f'bandwidth: {num * 4 * 3 / time_total / 1000)} MB/s')
print(f'total time: {time_total} s')
```
# CUDA

```py

- Memory allocation and deallocation is done explicitly
    - cudaMalloc, cudaFree, cudaMallocHost
- Memory movement and setting
    - cudaMemcpy, cudaMemcpyAsync, cudaMemsset, cudaMemsetAsync

## CUDA Kernels

- Declare a kernel: `__global__ void kernel_name(args...)`
- Declare device "helper" function: `__device__ void helper_name(args...)`
- Args are on host, pointers to device memory also on host

## Launching Kernels

- Define block shapes, e.g. `dim3 block(dim_x, dim_y, dim_z)`
- Define thread shapes, e.g. `dim3 thread(thread_x, thread_y, thread_z)`
- Launch kernel: `kernel_name<<<block, thread>>>(args...)`

## Synchronization and Error Handling

- Thread synchronization: `__syncthreads()` -> device function
- Block synchronization: usually not feasible, except for "cooperative launch"
- Device synchronization: `cudaDeviceSynchronize()` -> host function
- Error handling: `cudaGetLastError()`, `cudaGetErrorString()`



## CUDA Addition Kernel

```cu
#include <cuda_runtime.h>
#include <stdio.h>

#define BLOCK_SIZE 256

// copied num_blocks * num_threads from Triton example
__global__ void addition(int *a, int *b, int *c, int num) {
    int start = blockIdx.x * blockDim.x + threadIdx.x;
    if (start < num) {
        c[start] = a[start] + b[start];
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

### Compile

use `nvcc` to compile the CUDA code

```sh
# compile
nvcc addition.cu -o addition

# run
./addition
```

## tuning

Some things you can try to tune your CUDA code:
- Increase block size
- Increase number of blocks
- Load more things per thread

## Additional CUDA features on modern GPUs

- Unified memory addressing (P100+)
- NvLink (P100+)
- Clusters (H100+)
- TMA (H100+)
- NVSHART (H100+)
- FP4 & FP6 (B100+)
