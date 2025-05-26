---
title: Transformer Architecture and Implementation
category: Machine Learning Systems
tags: transformers, architecture, implementation, attention, prefill, decode, feedforward, normalization, machine learning
description: Overview of transformer architecture (specifically Llama) and its implementation details for LLM serving systems
---

## Transformer Architecture Overview

> Disclaimer: These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025 instructed by both Prof. Baris Kasikci and TA Kan Zhu

### Prefill vs. Decode Phases

**Prefill Phase:**

- Processes entire input prompt at once
- All tokens processed in parallel
- Compute-bound operation

**Decode Phase:**

- Generates one token at a time
- Sequential generation process
- Memory-bound operation (utilizes KV cache)

### Transformer Layers and Iterations

- **Inference Iteration:** Complete forward pass through all layers to generate one output token
- **Inference Layer:** Single transformer layer containing attention and FFN components
- **Activations:** Intermediate representations passed between layers

---

## Core Transformer Components

### 1. Embedding Layer

**Purpose:** Convert token IDs to dense vector representations

```python
input_ids: [The, University, ...]
embeddings: {
    The: [0, 1, 0, 1, ...],  # 4096 elements in Llama
    University: [0, 0, 0, ...]
}
```

### 2. Attention Mechanism

#### Self-Attention Formula
$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

Where:

- **Q (Query):** What the transformer is looking for
- **K (Key):** What's available in the sequence
- **V (Value):** What needs to be updated to assimilate context
- **$d_k$:** Head dimension for scaling

#### Causal Self-Attention

- **Causal Mask:** Prevents tokens from attending to future tokens
- Uses $-\infty$ values in attention matrix for future positions
- When $x_i \to -\infty$, $\text{softmax}(x_i) \to 0$

#### Grouped Query Attention (GQA)

- **Purpose:** Reduce KV cache memory usage
- **Mechanism:** Multiple query heads share the same key and value heads
- **Group Size:** Number of query heads per key/value head (e.g., group size = 4)
- **Benefit:** Allows increasing batch size by factor of group size

### 3. Multi-Head Attention

#### Head Separation Process
```python
# Original query tensor
q = [[1, 2, 3, 4, 5, 6],    # Token 1
     [7, 8, 9, 10, 11, 12]] # Token 2
# Shape: (seq_len, hidden_dim) = (2, 6)

# Separated into heads
sub_q = [[[1, 2, 3],   # Head 1 for Token 1
          [4, 5, 6]],  # Head 2 for Token 1
         [[7, 8, 9],   # Head 1 for Token 2
          [10, 11, 12]]] # Head 2 for Token 2
# Shape: (seq_len, num_heads, head_dim) = (2, 2, 3)
```

### 4. Feed Forward Network (FFN)

**Architecture:** Two linear transformations with activation function

- **Up Projection:** Expands hidden dimension
- **Gate Projection:** Controls information flow
- **Activation Function:** SwiGLU (Swish-Gated Linear Unit)
- **Down Projection:** Returns to original dimension

**Mathematical representation:**
$$\text{FFN}(x) = \text{Down}(\text{SwiGLU}(\text{Up}(x)) \odot \text{Gate}(x))$$

### 5. Normalization

#### RMSNorm (Root Mean Square Normalization)
$$\text{RMSNorm}(x) = \frac{x}{\sqrt{\frac{1}{n}\sum_{i=1}^n x_i^2 + \epsilon}} \odot g$$

Where:

- **x:** Input vector of size n
- **epsilon:** Small constant for numerical stability (e.g., $10^{-8}$)
- **g:** Learned scaling parameter (element-wise multiplication)

### 6. Residual Connections

- **Purpose:** Enable gradient flow in deep networks
- **Implementation:** Add input to output of each major component
- **Formula:** $\text{output} = \text{input} + \text{component}(\text{input})$

---

## Multi-GPU Implementation

### Tensor Parallelism

- **Weight Distribution:** Split weight matrices across GPUs
- **Query/Key/Value:** Distributed across different GPUs
- **Computation:** Parallel matrix multiplications

### Communication Operations

#### AllGather

- **Purpose:** Collect partial results from all GPUs
- **Usage:** After attention computation to gather all head outputs
- **Operation Type:** Network-bound

#### AllReduce

- **Purpose:** Sum partial results across GPUs
- **Composition:** ReduceScatter + AllGather
- **Usage:** After FFN down projection
- **Operation Type:** Network-bound

---

## Resource Utilization Patterns

### Compute-Bound Operations

- Query, Key, Value projections
- Up and Gate projections in FFN
- Output projections
- Prefill attention computation

### Memory-Bound Operations

- Decode attention (KV cache access)
- Reading cached key-value pairs

### Network-Bound Operations

- AllGather communications
- AllReduce communications

---

## Key Implementation Details

### KV Cache Management

- **Storage:** Unique per batch, shared across layers
- **Purpose:** Avoid recomputing key-value pairs during decode
- **Memory Impact:** Major contributor to GPU memory usage

### Rotary Positional Encoding

- **Application:** Applied to query and key vectors
- **Purpose:** Encode relative position information
- **Advantage:** Better handling of variable sequence lengths

### Softmax Computation
$$\text{softmax}(x_i) = \frac{e^{x_i}}{\sum_j e^{x_j}}$$
- **Numerical Stability:** Often implemented with temperature scaling
- **Attention Weights:** Output represents attention distribution

---

## Architecture Comparison

### Original Transformer vs. Llama Architecture

- **Original:** Encoder-decoder with cross-attention
- **Llama:** Decoder-only architecture
- **Normalization:** LayerNorm 	o RMSNorm
- **Activation:** ReLU 	o SwiGLU
- **Position Encoding:** Absolute 	o Rotary (RoPE)
- **Attention:** Multi-head 	o Grouped Query Attention

This architecture forms the foundation for modern large language models and understanding these components is crucial for optimizing LLM serving systems.