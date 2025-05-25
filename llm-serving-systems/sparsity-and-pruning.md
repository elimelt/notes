---
title: Sparsity and Pruning in LLM Serving Systems
category: Machine Learning Systems
tags: sparsity, pruning, performance optimization, machine learning
description: Overview of techniques in LLM serving systems using sparsity and pruning to optimize performance and reduce model size.
---

# Sparsity and Pruning in LLM Serving Systems

## Introduction

### Types of Sparsity
- **Weights**: Model parameter sparsity
- **Activations**: Runtime computation sparsity
- **KV-Cache**: Attention cache sparsity

## Sparsity Enables Pruning

### Core Concepts
- **Pruning**: Removing synapses, neurons, weights, or reducing hidden dimension size
- **Granularity matters**: Different levels of pruning have different accuracy impacts
- **Pruning + fine-tuning**: Common approach to recover accuracy
- Can sometimes achieve **higher accuracy** than the original model

### Accuracy Impact
- Pruning alone causes gradual accuracy degradation
- Pruning + fine-tuning maintains accuracy better across higher sparsity levels
- Sharp accuracy drop occurs around 80-90% sparsity even with fine-tuning

## Weight Sparsity Approaches

### Magnitude-Based Weight Pruning
- **Method**: Remove weights based on their magnitude
- **Optimal Brain Damage**: Theoretical foundation
  - Shows pruning weights with least impact is optimal
  - Requires computing Hessian of weights (expensive)
  - **Weight magnitude serves as simple proxy**

### The Lottery Ticket Hypothesis
**Core Hypothesis**: "In a large, randomly initialized neural network, there exist small sparse subnetworks - the 'winning tickets' - that, when trained from scratch (with their original initial weights), can match the full model's performance."

**Key Insights**:
- Over-parametrization is useful - gives many chances for good initializations
- Explains why pruning works: winning tickets exist from the start
- Can prune after training because winning subnetworks were present initially

### Weight Sparsity Types

#### Structured Sparsity
- Removes entire pre-defined blocks of weights
- Examples: complete rows, columns, channels, attention heads, layers
- Easy to implement efficiently

#### Semi-structured Sparsity
- **2:4 pattern**: Two non-zero weights out of every 4 weights
- Hardware-friendly (NVIDIA Ampere support)
- Balance between flexibility and efficiency

#### Unstructured Sparsity
- Maximum flexibility in weight removal
- **Hard to implement efficiently** due to irregular patterns

## Advanced Pruning Techniques

### Wanda (Weight and Activation Pruning)
**Key Features**:
- Prunes weights on per-output basis
- Uses product of **weight magnitudes** and **input activation norms**
- **No retraining required**

**Algorithm**:
```python
def prune(W, X, s):
    metric = W.abs() * X.norm(p=2, dim=0)  # Wanda pruning metric
    _, sorted_idx = torch.sort(metric, dim=1)  # sort per output
    pruned_idx = sorted_idx[:, :int(C_in * s)]  # get indices to prune
    W.scatter_(dim=1, index=pruned_idx, src=0)  # zero out weights
    return W
```

**Performance**:
- Comparable to SparseGPT but simpler (no intensive weight updates)
- Maintains good accuracy across different sparsity levels (50%, 4:8, 2:4)

### DEJAVU: Contextual Sparsity
**Core Concept**: Input-dependent sparsity patterns
- Dynamically selects which attention heads and FFN parameters to activate
- **Query-aware**: Sparsity patterns adapt to current input context

**Key Innovation**:
- Uses **lookahead predictors**:
  - Attention layer at block k 	o predicts MLP sparsity at block k
  - MLP at block k 	o predicts attention sparsity at block k+1
- Implemented via hardware-aware sparse matrix multiplication

**Results**:
- **No accuracy drop until 75% sparsity**
- **1.8-6x speedup** compared to state-of-the-art
- Preserves long-dependency task performance

## KV Cache Sparsity

### Sparsity in Attention
- **Attention matrices are >95% sparse** at inference time
- Only **<1% of attention weights are relatively large**
- Motivates KV cache compression techniques

### Quest: Query-Aware Sparsity
**Problem with Previous Methods**:
- Evict "unimportant" KV cache based on historical information
- **Challenge**: Evicted tokens might be important for future tokens

**Quest Solution**:
- **Preserve all KV cache** in storage
- **Reduce memory movement** by selecting only top-K relevant pages
- Two-stage process:
  1. **Stage 1**: Identify most relevant KV cache pages for current query
  2. **Stage 2**: Compute sparse attention only on selected pages

**Performance**:
- **7.03x speedup** at 32k sequence length with 2k token budget
- Maintains high accuracy on long-dependency tasks
- Quest estimation policy aligns closely with oracle selection

### DeepSeek Multi-Head Latent Attention (MLA)
**Key Innovation**: Matrix-level KV cache compression
- **15x smaller KV cache** in DeepSeek-V2 vs V1
- **5.7x throughput improvement**

**Approach**:
- Store compressed **latent vector** instead of full keys & values
- **7% of original size** through learned matrix projections
- Exploits redundancy in high-dimensional vectors

**Integration with RoPE**:
- Standard RoPE makes compression harder (position-dependent rotations)
- **MLA trick**: Keep Q&K unrotated, concatenate RoPE information separately

### KV Cache Comparison

| Attention Mechanism | KV Cache per Token | Capability |
|-------------------|-------------------|------------|
| Multi-Head Attention (MHA) | $2n_h d_h l$ | Strong |
| Grouped-Query Attention (GQA) | $2n_g d_h l$ | Moderate |
| Multi-Query Attention (MQA) | $2d_h l$ | Weak |
| **MLA** | $(d_c + d_h^R)l \approx \frac{3}{2}d_h l$ | **Stronger** |

## Activation Sparsity

### Core Concept
- **Skip computation dynamically** based on activation values
- Focus on ~zero values at activation function outputs
- When activations are zero, corresponding weights become unnecessary

### Motivation
Activation distributions in LLMs are **centered around zero**, making magnitude-based pruning effective across:
- MLP up/down projections
- Attention Q, K, V weights
- Attention output weights

### TEAL (Threshold-based Activation Pruning)
**Method**:
- During decoding, threshold low-magnitude activations to 0
- Skip moving associated weight channels to registers
- Provides speedup by reducing memory movement

**Performance**:
- **25% sparsity**: Minimal accuracy loss, 1.2-1.3x speedup
- **50% sparsity**: Small accuracy degradation, 1.6-1.8x speedup
- Works across different model sizes (8B to 70B parameters)

## Implementation Considerations

### Hardware Support
- **NVIDIA Ampere 2:4 sparsity**: Hardware acceleration for semi-structured patterns
- **Structured formats**: Enable efficient compressed storage and computation
- **Memory bandwidth**: Key bottleneck addressed by activation sparsity

### Practical Deployment
- **Zero-shot methods** (Wanda, TEAL) require no retraining
- **Fine-tuning approaches** offer better accuracy recovery
- **Hardware-aware implementation** crucial for realizing speedups
- **Granularity trade-offs** between flexibility and efficiency

## Key Takeaways

1. **Sparsity is pervasive** in LLMs across weights, activations, and attention
2. **Multiple sparsity types** serve different optimization goals
3. **Contextual/dynamic sparsity** often outperforms static approaches
4. **Hardware support** is crucial for practical speedups
5. **Accuracy-efficiency trade-offs** can be managed through careful technique selection
6. **Combination approaches** (weight + activation sparsity) show promise for maximum efficiency