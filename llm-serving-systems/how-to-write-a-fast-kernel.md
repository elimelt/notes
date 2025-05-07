---
title: How to write a fast kernel
category: Machine Learning Systems
tags: cuda, gpu, pytorch, kernel
description: Techniques to write fast CUDA kernels, including coalesced memory access and shared memory usage.
---

# How to write a fast kernel?

## Matrix Transpose Kernel

### Basic way with Torch

```py
import torch

num_rows = num_cols = 8192
a = torch.randn(num_rows, num_cols)

res = a.t().contiguous()

start = torch.cuda.Event(enable_timing=True)
end = torch.cuda.Event(enable_timing=True)

start.record()

for i in range(100):
    res = a.t().contiguous()

end.record()
torch.cuda.synchronize()

elapsed_time = start.elapsed_time(end)
time_per_iter = elapsed_time / 100

print(f"Elapsed time: {elapsed_time} ms")
print(f"Time per iteration: {time_per_iter} ms")
```

### How can we optimize?

Row-based partitioning in a CUDA kernel? But arrays can be very long. We can't load all the data into the shared memory. So, we need to partition the data into smaller chunks per-thread (since we have at most 1024 threads per block).

### CUDA Kernel

```cpp
#include <torch/extension.h>
#include <stdio.h>

__global__ void transpose(float* input, float* output, int num_rows, int num_cols) {
    int row = blockIdx.x;
    int col_start = threadIdx.x * (num_cols / blockDim.x);
    int col_end = col_start + (num_cols / blockDim.x);

    for (int col = col_start; col < col_end; ++col) {
        if (col < num_cols) {
            output[col * num_rows + row] = input[row * num_cols + col];
        }
    }
}

```


## Coallesced Memory Access

- Inside one warp, if memory accesses are coalesced, then the memory access is fast because it can be batched
- Data can then be retrieved in a single memory transaction
