---
title: Memory Management in LLM Serving Systems
aliases:
  - llm-serving-systems/memory-management
category: Machine Learning Systems
tags:
  - memory-management
  - kv-cache
  - prefix-sharing
  - paged-attention
  - flash-attention
  - machine-learning
date: 2025-05-25
updated: 2026-07-30
status: needs-review
description: KV cache sizing, allocation strategies (max-length, vector-style, PagedAttention), prefix sharing, eviction tradeoffs, and FlashAttention, with worked calculations for Llama3-8B on an H100.
sources:
  - title: CSE 599K, LLM Serving Systems, University of Washington, Spring 2025 (lecture notes)
    type: lecture
  - title: "Efficient Memory Management for Large Language Model Serving with PagedAttention"
    url: https://arxiv.org/abs/2309.06180
    type: paper
  - title: "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness"
    url: https://arxiv.org/abs/2205.14135
    type: paper
---

## Purpose

This note covers how serving systems size, allocate, share, and evict the KV cache, plus the FlashAttention algorithm that keeps attention itself from blowing up memory. KV-cache allocation directly constrains [[ml/serving-systems/batching|batching]], and [[ml/serving-systems/inf-llm|InfLLM]] explores an external-memory approach for extremely long contexts.

These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025, taught by Prof. Baris Kasikci with TA Kan Zhu. The prefix-sharing speedup range quoted below comes from lecture slides without a full benchmark setup, so I mark it as unverified.

## KV cache sizing

Per token, the KV cache stores one key vector and one value vector per layer per KV head:

$$\text{KV bytes per token} = \underbrace{2}_{K \text{ and } V} \times \text{num\_kv\_heads} \times \text{head\_dim} \times \text{num\_layers} \times \text{dtype bytes}$$

Worked example from lecture, Llama3-8B on an 80 GB H100 in FP16. Weights take $2 \times 8 = 16$ GB, and serving-time activations are negligible next to that. Take requests with 1024 input tokens and 1024 output tokens. A request's decode allocation grows from 0 to 1024 tokens, so on average it holds $1024 + \frac{1024}{2} = 1536$ token slots. With 8 KV heads, head dim 128, 32 layers, FP16:

$$1536 \times 2 \times 2 \times 8 \times 128 \times 32 \text{ bytes} = 192 \text{ MB per request (average)}$$

Maximum average batch size is then $(80 - 16) / 0.1875 \approx 341$ requests. Compare this against the batch size of 333 needed to reach the compute-bound regime on the H100 (see [[ml/serving-systems/performance-modeling|Performance Modeling]]): the KV cache budget barely covers the batch the compute wants. Per token the cache costs $2 \times 2 \times 8 \times 128 \times 32 = 128$ KB, so the 64 GB budget holds about 512K tokens.

## The allocation problem

Output lengths vary and are unknown at admission. A request that stops at 1024 output tokens needs 192 MB on average; one that runs to 4096 needs 384 MB. The allocator has to reserve space without knowing which case it is holding.

### Method 1: allocate for the maximum

Reserve the model's maximum sequence length per request. Utilization craters from internal fragmentation, and the max batch size drops to $(80-16)/0.375 \approx 170$ even though most requests never touch the reserved space.

### Method 2: grow like std::vector

Start small and double the allocation when it fills. Average utilization within a request sits around 75% (the classic doubling-array bound), external fragmentation appears between requests, and growth requires copies. Workable, and better than max-length reservation, but the fragmentation still costs real batch slots.

### Method 3: PagedAttention

[PagedAttention](https://arxiv.org/abs/2309.06180) (the vLLM paper) applies virtual memory's trick: chunk KV storage into small fixed pages and map logical token positions to physical pages through an indirection table. A page holding 16 tokens' KV for one layer costs $16 \times 2 \times 2 \times 8 \times 128 = 64$ KB, big enough that reading a page uses memory bandwidth efficiently, small enough that internal fragmentation is capped at one partial page per request. Pages need not be contiguous, so external fragmentation disappears.

The page table is a flat multi-level structure:

```text
kv_indptr:  [0, 2, 3, 6, 10]                   # NumReq + 1 elements
kv_indices: [1, 4, 8, 2, 5, 0, 6, 10, 15, 17]  # NumPage elements
kv_data:    [actual KV cache data...]          # MaxPage elements
```

Request $i$ owns pages `kv_indices[kv_indptr[i]:kv_indptr[i+1]]`, and `kv_data[page_id]` holds the actual KV entries. The attention kernel walks this table during decode.

## Prefix sharing

Requests frequently share a prefix: the same system prompt across users, or the accumulated history in a multi-round conversation.

```text
1. "You are a helpful assistant. User: Hello, Assistant: Hi!"
2. "You are a helpful assistant. User: Hello, Assistant: Hi!, User: Solve this problem..."
3. "You are a helpful assistant. User: What can you do?"
```

Storing the shared prefix once turns $n$ copies of a length-$p$ prefix into one: prefill compute, KV cache space, and decode-time memory reads for the prefix all drop from $n \times p$ to $p$. Prefix matching can run asynchronously in the background. The cost is that cached prefix chunks occupy memory even when no live request reuses them, so the cache needs an eviction policy. Gains scale with prefix length, batch size, and how short the unique suffixes are; the lecture quotes 2-32x speedups across configurations, without the underlying benchmark setup, so treat the range as indicative.

## Eviction: recompute or offload?

When GPU memory cannot hold the whole prefix tree, evicted entries can later be rebuilt two ways: recompute them from the tokens, or reload them from CPU memory over PCIe.

Recomputing $p$ tokens through a model with $P_{model}$ parameters costs

$$T_{recompute} = \frac{2pP_{model}}{Compute}$$

Loading the same KV entries over PCIe costs

$$T_{load} = \frac{2 \times \text{dtype} \times \frac{D_{model}}{GQA} \times L \times p}{PCIe_{BW}}$$

where $\frac{D_{model}}{GQA}$ is the KV width after grouped-query sharing and $L$ is the layer count. The ratio is

$$\frac{T_{recompute}}{T_{load}} = \frac{PCIe_{BW} \times P_{model}}{\text{dtype} \times \frac{D_{model}}{GQA} \times L \times Compute}$$

Plugging in an 8B model on an A100 (30 GB/s PCIe, 300 TFLOPs, FP16, KV width 1024, 32 layers):

$$\frac{30 \times 10^9 \times 8 \times 10^9}{2 \times 1024 \times 32 \times 300 \times 10^{12}} \approx 12$$

Loading from CPU memory beats recomputation by roughly 12x for this configuration, which is why serving systems offload rather than drop evicted KV entries.

## FlashAttention

Standard attention materializes the $\text{seqlen} \times \text{seqlen}$ score matrix in global memory, so memory grows quadratically with sequence length and the kernel spends its time moving that matrix around. [FlashAttention](https://arxiv.org/abs/2205.14135) computes exact attention without ever materializing it.

The obstacle is softmax, which normalizes over a full row. The numerically stable form subtracts the row max before exponentiating:

$$sm(x_i) = \frac{e^{x_i - c}}{\sum_{j=1}^d e^{x_j - c}}, \quad c = \max_i x_i$$

Subtracting $c$ prevents overflow and leaves the result unchanged, since the factor $e^{-c}$ cancels between numerator and denominator. FlashAttention exploits the fact that the row max and the normalizing sum can be maintained incrementally. The algorithm tiles Q, K, V into blocks that fit in shared memory, computes attention block pair by block pair, keeps running max and sum statistics in registers, and rescales previously accumulated output whenever a new block raises the running max. Global memory only ever sees the inputs and the final output.

Causal masking drops in cleanly: masked positions get $-\infty$ before the softmax, contribute $e^{-\infty} = 0$ to the running sum, and blocks that are entirely masked are skipped. Grouped-query attention also fits naturally, since multiple query heads sharing one KV head means the kernel processes several query blocks against the same KV block, cutting KV cache size and KV reads by the group factor.

## Related notes

- [[ml/serving-systems/batching|Batching]]
- [[ml/serving-systems/performance-modeling|Performance Modeling]]
- [[ml/serving-systems/inf-llm|InfLLM]]
- [[ml/serving-systems/transformers|Transformer Architecture]]
