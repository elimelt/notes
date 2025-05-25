---
title: Memory Management in LLM Serving Systems
category: Machine Learning Systems
tags: memory management, kv cache, prefix sharing, paged attention, flash attention
description: Overview of memory management techniques in LLM serving systems, performance optimization strategies for serving serving systems, particularly on KV cache methods.
---

# Memory Management in LLM Serving Systems

## KV Cache Size Calculation

### Key Components
The KV cache size depends on:
- **Num KV heads**: Number of key-value attention heads
- **Head Dim**: Dimension of each attention head
- **2**: Stores both K and V matrices
- **Stype**: Data type size (e.g., 2 bytes for FP16)
- **Seqlen**: Sequence length
- **Layer**: Number of transformer layers

### Example Calculation - Llama3-8B on H100
- **Total GPU memory**: 80GB
- **Model weights**: 2	imes8=16GB (assuming FP16)
- **Activations**: Negligible during serving
- **Input/Output**: 1024 input tokens, 1024 output tokens

**KV cache per request**:
```
(1024 + 1024/2) 	imes 2 	imes 2 	imes 8 	imes 128 	imes 32 / 1024 / 1024 = 192 MB
```

**Maximum batch size**:
```
(80 - 16) / (192/1024) = 341 requests
```

Note: Batch size of 333 was needed to reach compute-bound regime on H100.

## Memory Allocation Challenges

### Variable-Length Requests
When serving requests with different output lengths:
- **Min KV cache**: 192 MB (1024 output tokens)
- **Max KV cache**: 384 MB (4096 output tokens)

**Key Question**: How to efficiently allocate KV cache for requests with different lengths?

## Allocation Methods

### Method 1: Fixed Max Sequence Length

**Approach**: Allocate KV cache using maximum sequence length the model supports

**Problems**:
- **Low utilization**: Significant internal fragmentation
- **Wasted memory**: Short requests don't use full allocated space
- **Reduced batch size**: Max batch size = (80-16)/(384/1024) = 170

### Method 2: std::vector-style Allocation

**Approach**: 
- Start with small size allocation
- Double the size when fully occupied
- Similar to dynamic array growth

**Characteristics**:
- **Internal waste**: ~75% average utilization within requests
- **External fragmentation**: Memory gaps between requests
- **Copy overhead**: Acceptable for the flexibility gained

### Method 3: PagedAttention

**Core Innovation**: Chunk global memory space into small pages

**Key Features**:
- **Page size**: 16 tokens' KV = 16	imes2	imes2	imes8	imes128 = 64 KB
- **No fragmentation**: Pages can be allocated non-contiguously
- **Efficient bandwidth**: Each page large enough for good utilization

## PagedAttention Implementation

### Multi-Level Page Table Structure

```
kv_indptr:  [0, 2, 3, 6, 10]  # NumReq + 1 elements
kv_indices: [1, 4, 8, 2, 5, 0, 6, 10, 15, 17]  # NumPage elements
kv_data:    [actual KV cache data...]  # Max Page elements
```

**How it works**:
- `kv_indptr[i]` to `kv_indptr[i+1]` indicates page range for request i
- `kv_indices[kv_indptr[i]:kv_indptr[i+1]]` contains page IDs for request i
- `kv_data[page_id]` stores the actual KV cache data

### Prefix Sharing

**Concept**: Share common prefixes across multiple requests

**Benefits**:
- **Reduced prefill computation**: n	imesp 	o p (where p = prefix length, n = requests)
- **Reduced KV cache size**: n	imesp 	o p
- **Reduced memory bandwidth**: n	imesp 	o p during decoding
- **Asynchronous matching**: Can be performed in background

**Drawbacks**:
- **Memory overhead**: Must store prefix chunks even when not reused

### Use Cases for Prefix Sharing

#### Multi-round Conversations
```
1. "You are a helpful assistant. User:Hello, Assistant:Hi!"
2. "You are a helpful assistant. User:Hello, Assistant:Hi!, User: Solve this problem..."
3. "You are a helpful assistant. User:What can you do?"
```

#### Multi-request Scenarios
- Same system prompts across different user queries
- Shared conversation contexts
- Common document prefixes

### Performance Benefits

Performance gains vary with:
- **Shared prefix length**: Longer prefixes = greater benefits
- **Batch size**: Higher batch sizes see more improvement
- **Unique suffix length**: Shorter unique parts = better gains

Typical improvements: **2-32x speedup** depending on configuration.

## Memory Management Strategies

### Eviction Policies: Recomputing vs Load/Offload

When GPU memory insufficient for full radix tree:

#### Recomputation Approach
**Time cost**: 
$$T_{recompute} = \frac{2pP_{model}}{Compute}$$

#### Load/Offload Approach  
**Time cost**:
$$T_{load} = \frac{2 \times dtype \times \frac{D_{model}}{GQA} \times L \times p}{PCIE\_Bandwidth}$$

#### Comparison Ratio
$$\frac{T_{recompute}}{T_{load}} = \frac{PCIE\_Bandwidth \times P_{compute}}{dtype \times \frac{D_{model}}{GQA} \times L \times Compute}$$

**Example calculation for A100**:
```
30GB/s 	imes 8 	imes 10^9 / (2 	imes 1024 	imes 32 	imes 300T) = 12
```

**Conclusion**: Loading from CPU memory is ~12x faster than recomputation.

## FlashAttention: Memory-Efficient Attention

### Problem with Standard Attention
- **Large intermediate matrices**: Seq_len 	imes Seq_len attention scores
- **Memory bottleneck**: Quadratic memory growth with sequence length

### Softmax Numerical Stability
**Standard softmax**:
$$sm(x_i) = \frac{e^{x_i}}{\sum_{j=1}^d e^{x_j}}$$

**Numerically stable version**:
$$sm(x_i) = \frac{e^{x_i-c}}{\sum_{j=1}^d e^{x_j-c}}$$

Where c = max(x_i) prevents overflow.

### FlashAttention Algorithm

**Key Innovation**: Tile-based computation with online softmax

**Steps**:
1. **Tiling**: Divide Q, K, V into blocks that fit in SRAM
2. **Block-wise computation**: Compute attention for each block pair
3. **Online aggregation**: Maintain running statistics (max, sum) across blocks
4. **Rescaling**: Properly combine results from different blocks

**Memory hierarchy utilization**:
- **SRAM**: Fast, limited capacity for active blocks
- **Global memory**: Slower, larger capacity for full matrices
- **Registers**: Fastest, smallest capacity for running statistics

### Causal Masking in FlashAttention
- **Implementation**: Set masked positions to -infty before softmax
- **Effect**: Masked positions contribute 0 to attention weights
- **Integration**: Seamlessly handled within block-wise computation

### Grouped Query Attention (GQA)
- **Shared KV heads**: Multiple query heads share same key-value heads
- **Memory savings**: Reduces KV cache size significantly
- **Implementation**: Process multiple query blocks with same KV block

## Key Takeaways

1. **KV cache dominates memory usage** in LLM serving, limiting batch sizes
2. **PagedAttention eliminates fragmentation** through page-based allocation
3. **Prefix sharing provides significant speedups** for common use cases
4. **Loading is much faster than recomputation** for evicted cache entries
5. **FlashAttention enables long sequences** through memory-efficient tiled computation
6. **Proper memory management is crucial** for maximizing GPU utilization in LLM serving