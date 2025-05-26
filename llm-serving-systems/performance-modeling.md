---
title: Performance Modeling for LLM Serving Systems
category: Machine Learning Systems
tags: performance, roofline, arithmetic intensity, machine learning
description: How do you model and optimize performance for LLM serving systems? What are the key metrics and techniques to ensure efficient inference? What really matters for end-to-end performance?
---

# Performance Modeling for LLM Serving Systems
> Disclaimer: These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025 instructed by both Prof. Baris Kasikci and TA Kan Zhu

### Performance Analysis

- **Roofline model** - Based on the Roofline paper and Google's scaling book
- **Detailed model of Transformer performance**

---

## The Roofline Model

### Core Concept

**Operational Intensity** = $\frac{\text{# of Operations}}{\text{# of Bytes Moved}}$

- **Operations**: E.g., FLOPs/Sec
- **Bytes Moved**: E.g., Bytes/sec (Memory or Network Bandwidth)

### Key Components

#### Computational Ceilings

- **Memory Bound**: Low operational intensity region
- **Compute Bound**: High operational intensity region
- **Roofline**: The boundary between memory and compute limitations

#### Performance Optimization Strategies

**Compute optimizations:**

- Multithreading
- ILP (Instruction-Level Parallelism)
- SIMD (Single Instruction, Multiple Data)

**Memory optimizations:**

- Stride accesses (HW prefetching)
- Memory affinity (NUMA effect)
- Software prefetching

### Critical Operational Intensity

$$\text{Intensity(Computation)} = \text{Intensity(Accelerator)}$$

$$\frac{\text{Computation FLOPs}}{\text{Communication Bytes}} = \frac{\text{Accelerator FLOPs/s}}{\text{Bandwidth Bytes/s}}$$

**Compute-Bound**: $\frac{\text{Computation FLOPs}}{\text{Communication Bytes}} > \frac{\text{Accelerator FLOPs/s}}{\text{Bandwidth Bytes/s}}$

**Memory-Bound**: $\frac{\text{Computation FLOPs}}{\text{Communication Bytes}} < \frac{\text{Accelerator FLOPs/s}}{\text{Bandwidth Bytes/s}}$

---

## Example: NVIDIA H100 Analysis

### Hardware Specifications

- **Peak FP16 Tensor TFLOPS**: 1000/2000 TFLOPs (with sparsity/no sparsity)
- **Memory bandwidth**: 3000 GB/s
- **Critical intensity**: $(1000 \times 10^{12}) / (3000 \times 10^9) = 333$ FLOPs/Byte

**Rule**: If kernel has higher operational intensity than 333 FLOPs/Byte 	o compute-bound, otherwise memory-bound

### Example Operations

#### FP32 Dot Product
**Compute**: $N$ multiplications, $N$ additions = $2N$ FLOPs

**Memory**: $2 \times 4N$ bytes read + $4$ bytes written back

**Operational Intensity**: $\frac{2N}{4N + 4} \approx \frac{1}{2}$

**Result**: FP32 dot product on H100 is **memory-bound**

#### Matrix Multiplication with FP16
For $[M,N] \times [N,K] \rightarrow [M,K]$:

**Memory**: $2MN + 2NK$ bytes read, $2MK$ bytes written back

**Compute**: $2MNK$ FLOPs

**Operational Intensity**: $\frac{2MNK}{2MN + 2NK + 2MK} \approx M$

**Result**: Matrix multiplication on H100 is compute-bound if $M > 333$

---

## NUMA Effect with GPUs

Modern GPU clusters show significant bandwidth variations:
- **GPU memory bandwidth**: 900 GB/s
- **Network bandwidth**: 200 Gb/s = 25 GB/s

This creates hierarchical memory access patterns affecting performance modeling.

---

## Performance Modeling Framework

### Key Hardware Factors

- **$N_{GPU}$**: number of GPUs
- **MemBW** (GB/s): aggregate GPU memory bandwidth
- **$GPU_{mem}$** (GB): aggregate GPU memory capacity
- **Compute** (GFLOPS/s): aggregate GPU compute capacity
- **NetBW** (GB/s): aggregate GPU interconnect bandwidth

### Key Model Configuration Factors

- **$D_{model}$**: hidden dimension size (hidden_dim)
- **$L$**: number of layers
- **$P_{model}$**: number of parameters
- **$R_{GQA}$**: group size of GQA (group_size)
- **$S_{Type}$**: Model parameters' data size in bytes (e.g., 2 for FP16)

### Key User Statistics

- **$p$**: average number of tokens in prompts to be prefilled
- **$d$**: average number of tokens in output to be decoded
- **$p + d$**: average number of tokens in user request (sequence length)
- **Per request throughput**: $\frac{\text{Throughput}_{total}}{p + d}$
- **Decoding throughput**: $d \frac{\text{Throughput}_{total}}{p + d}$

---

## Execution Time Models

### Memory-Centric Execution Time

$$T_{memory} = \frac{GPU_{mem}}{MemBW}$$

**Assumption**: Entire contents of GPU memory loaded once during one iteration

### Compute-Centric Execution Time

$$T_{compute} = \frac{2B_{dense}P_{model}}{Compute}$$

**Logic**: All dense operations require $2B_{dense}P_{model}$ FLOPs total

### Network-Centric Execution Time

$$T_{net} = \frac{4(N_{GPU} - 1)D_{model}B_{dense}S_{type}L}{NetBw}$$

**Components**:

- $(N_{GPU} - 1)$: number of hops
- $4$: All-Gathers per layer
- All-Reduce approx 2 	imes All-Gather

---

## Performance Analysis Results

### Compute vs Network

$$\frac{T_{net}}{T_{compute}} = 2(N_{GPU} - 1)\frac{D_{model}L}{P_{model}} \frac{S_{type} \cdot Compute}{NetBw}$$

**Key Finding**: LLM Serving is more **compute-bound** than **network-bound**

### Compute vs Memory

$$\frac{T_{memory}}{T_{compute}} = \frac{Compute \cdot GPU_{mem}}{MemBW \cdot 2B_{dense}P_{model}}$$

**Factors affecting the balance**:

- **GQA allows for larger batch size** 	o favors compute
- **Model sizes tend to increase** 	o favors compute
- **Batches with large decode requests increase memory accesses** 	o favors memory

**Key Finding**: LLM serving is more **compute-bound** than **memory-bound**

---

## Grouped Query Attention (GQA)

### Concept

- **Traditional**: Each attention head has its own Key-Value cache
- **GQA**: Multiple attention heads share Key-Value pairs
- **Group size**: Number of heads sharing the same K-V pairs

### Impact on Performance

- **Reduces KV cache memory requirements** by factor of group size
- **Allows increasing batch size** by factor of group size
- **Shifts workload toward compute-bound** rather than memory-bound

---

## Optimal Throughput Analysis

### Theoretical Maximum

$$\text{Throughput} = \frac{B_{dense}}{T_{compute}} = \frac{B_{dense}}{\frac{2B_{dense}P_{model}}{Compute}} = \frac{Compute}{2P_{model}}$$

**Example**: LLaMA 70B on A100 	o **1857 tokens/s/GPU**

### Performance Gap
Current serving frameworks show significant gaps to optimal throughput:
- **vLLM**: ~494-552 tokens/s
- **DeepSpeed-FastGen**: ~372-513 tokens/s
- **TensorRT-LLM**: ~636-817 tokens/s

**Key Insight**: There is a **large gap to optimal throughput** - high GPU compute utilization is critical for LLM serving performance.

---

## Key Takeaways

1. **Roofline model** provides framework for understanding compute vs memory bounds
2. **Critical operational intensity** determines performance bottlenecks
3. **LLM serving is primarily compute-bound** rather than memory or network bound
4. **GQA enables larger batch sizes** and improves compute utilization
5. **Significant optimization opportunities exist** - current frameworks achieve only ~25-45% of theoretical peak throughput
6. **High GPU compute utilization is the key** for effective LLM serving