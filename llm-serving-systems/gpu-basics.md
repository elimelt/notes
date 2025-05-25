---
title: GPU Architecture and Programming
category: Machine Learning Systems
tags: gpu, architecture, programming, cuda, nvidia, pytorch, triton
description: Overview of GPU architecture and context behind GPUs for LLM serving systems
---

# GPU Architecture and Introduction to GPU Programming

---

### Training vs Inference
- **Training**: Learning from existing data
- **Inference**: Applying capability to new data

### Serving
**ML model serving** is about building a system to efficiently and scalably perform inference with:
- High throughput
- Low latency
- Compliance with diverse Service Level Objectives (SLOs)


## LLM Applications and Market Context

### Applications Enabled by LLMs
- **AI Assistants** (ChatGPT, Google Bard)
- **Text-to-Image** (DALLcdotE, MidJourney)
- **Creative Writing** (Jasper, Copy.ai)
- **AI Coding Tools** (GitHub Copilot, Replit)
- **Text-to-Speech & Audio** (Descript, Synthesia)

**Key principle**: Batching user requests and aiming for optimal throughput are key

### Market Demand
- ChatGPT monthly visits grew from ~500M (Dec 2022) to ~2000M (Jan 2024)
- Users frequently encounter "We're experiencing exceptionally high demand" messages

### Infrastructure Costs
**Large-scale H100 investments in 2024:**
- Meta: 300K units
- Google: 150K units
- Microsoft: 150K units
- X: 85K units

**NVIDIA H200 HGX Server specs:**
- Cost: ~$250,000
- High operating cost: Up to ~10,000W
- Long lead time


## GPU Fundamentals

### What is a GPU?
- **Graphics Processing Unit**
- Originally designed for accelerated graphics rendering
- Now handles scientific computing and machine learning
- Come with software stacks: CUDA (NVIDIA), ROCm (AMD)

### CPU vs GPU Architecture

| Aspect | CPU | GPU |
|--------|-----|-----|
| **Design Focus** | Control logic (good with branching) | Computation/loading |
| **Performance** | Single thread performance | Parallel processing |
| **Cores** | Few powerful cores | Many simpler cores |
| **Memory** | Large cache hierarchy | High bandwidth memory |

### Example Specifications

| Specification | AMD EPYC 9555 (CPU) | NVIDIA H200 (GPU) |
|---------------|---------------------|-------------------|
| **Cores/Threads** | 64 Cores / 128 Threads | 16,896 CUDA Cores |
| **Frequency** | 4.4 GHz | 1.980 GHz |
| **TFLOPs** | ~10-20 TFLOPs | 989 TFLOPs |
| **Memory Size** | Up to 6 TB | 144GB |
| **Memory Bandwidth** | 576 GB/s | 4800 GB/s |
| **Memory Latency** | ~70ns | ~110ns |

**Key difference:**
- **CPU DRAM**: Low latency random access
- **GPU HBM**: Higher bandwidth, structured batch access

---

## GPU Hardware Architecture

### Data Center Context
- GPUs are deployed in server clusters
- Connected via high-speed networks (NVLink: 900 GB/s)
- Network connectivity: 200 Gb/s = 25 GB/s to data center network

### GPU Memory Hierarchy
- **Global Memory (HBM)**: 80 GB, 3TB/s bandwidth
- **L2 Cache**: 50MB, ~10TB/s bandwidth
- **Shared Memory ("Smem")**: 228 KB per SM, ~20TB/s bandwidth
- **Registers**: 64K 	imes 32 Bit per SM, ~600TB/s bandwidth

### Streaming Multiprocessors (SMs)
**Components:**
- **CUDA Cores**: Scalar computation
- **Tensor Cores**: Matrix (dense) computation
- **Shared/Constant Memory**: High bandwidth temp buffer

---

## GPU Programming Model

### Hierarchy of Execution Units

| Concept | Definition | Architecture | Communication | Limits |
|---------|------------|--------------|---------------|--------|
| **Thread** | Minimal units that execute instructions | Function units | Local | Up to 255 registers |
| **Warp** | Group of Threads | "SM tiles" | Register File | 32 threads |
| **Thread Blocks** | Group of Warps | SM | Shared Memory | Up to 32 warps (1024 threads) |
| **Kernel** | Function on GPU | GPU | L2/Global memory | Up to (2epsilonz-1)epsilon Blocks |

### Key Concepts
- **32 threads form a warp**
- **Threads in a warp run in parallel** with:
  - Same instructions
  - Same pace
  - Different data at register level
- **4 warps run on one SM simultaneously**
- **Scheduler swaps warps on and off SM**
- **Blocks operate independently**
- **Block-Block communication via L2/Global memory**

---

## GPU Programming Approaches

### 1. PyTorch (Easiest)
```python
import torch

def add_tensors(a, b):
    return a + b

if __name__ == "__main__":
    num_elements = 10**9
    
    # Create tensors on CPU
    tensor1 = torch.rand(num_elements, device='cpu')
    tensor2 = torch.rand(num_elements, device='cpu')
    
    # Move to GPU
    tensor1 = tensor1.to('cuda')
    tensor2 = tensor2.to('cuda')
    
    # Compute addition
    for i in range(10):
        result = add_tensors(tensor1, tensor2)
    
    # Move back to CPU
    result = result.cpu()
    print("Result of addition:", result)
```

### 2. Triton (Intermediate)
- **Compiler framework from OpenAI**
- **Python interface with automated thread management**
- **Higher performance than PyTorch for complex kernels**
- **Operates at block level**

```python
@triton.jit
def add_kernel(x_ptr, y_ptr, output_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    
    tl.store(output_ptr + offsets, output, mask=mask)
```

### 3. CUDA (Most Control)
- **Bare-bone, one-to-one mapping to hardware**
- **Highest performance**
- **Heavy implementation burden**

#### CUDA Memory Management
```cpp
// Memory allocation
cudaMalloc          // device memory allocation  
cudaMallocHost      // pinned host memory allocation
cudaFree            // free memory

// Memory operations
cudaMemcpy          // synchronous copy
cudaMemcpyAsync     // asynchronous copy
cudaMemset          // synchronous set
cudaMemsetAsync     // asynchronous set
```

#### CUDA Kernel Structure
```cpp
// Kernel declaration
__global__ void kernel_name(args...)

// Device helper function  
__device__ T helper_name(args...)

// Example addition kernel
__global__ void add(int *a, int *b, int *c, size_t num) {
    int block_start = blockIdx.x * blockDim.x;
    int thread_id = threadIdx.x;
    int index = block_start + thread_id;
    if (index < num) {
        c[index] = a[index] + b[index];
    }
}
```

#### CUDA Kernel Launch
```cpp
// Define block and thread dimensions
dim3 block(x, y, z);
dim3 thread(x, y, z);

// Launch kernel
kernel_name<<<block, thread>>>(args);
```

#### CUDA Synchronization
```cpp
__syncthreads()           // Thread synchronization (device function)
cudaDeviceSynchronize()   // Device synchronization (host function)

// Error checking
cudaGetLastError()        // Get last error
cudaGetErrorString()      // Get error description
```

---

## Performance Analysis

### Timing Considerations
- **PyTorch dispatches kernels non-blocking**
- CPU continues execution before GPU finishes
- **Must use CUDA events for accurate GPU timing**

### Profiling Tools
- **Torch.profiler**: Good at showing CPU activity, slow processing
- **Nsight Systems (nsys)**: High performance system-level profiling
- **Nsight Compute (ncu)**: Tailored for intra-kernel profiling

### CUDA Streams
- **Multiple streams may execute in parallel**
- Depends on kernels and schedulers
- **Use cudaEvents to synchronize between streams**
- Events act as "flags" between kernels
- `cudaStreamWaitEvent` for synchronization

---

## Modern GPU Features

### Advanced CUDA Features
- **Unified memory address** (P100+)
- **NvLink** (P100+)
- **Clusters** (H100+)
- **TMA (Tensor Memory Accelerator)** (H100+)
- **NVSHARP** (H100+)
- **FP4 and FP6 precision** (B100+)

---

## Summary

### Key Takeaways
1. **GPU Architecture Understanding**
   - Parallel processing focus
   - SMs, blocks, threads hierarchy
   
2. **Programming Approaches**
   - **PyTorch**: Easiest, high-level
   - **Triton**: Balance of control and ease
   - **CUDA**: Maximum control and performance
   
3. **Performance Analysis**
   - Proper timing with CUDA events
   - Profiling tools for optimization
   - Understanding memory hierarchy impact

**Core Principle**: Batching user requests and aiming for optimal throughput are key to effective LLM serving systems.