---
title: Intro to Mixture of Experts (MoE) in LLM Serving Systems
category: Machine Learning Systems
tags: mixture of experts, MoE, performance optimization, memory efficiency, machine learning
description: How do Mixture of Experts (MoE) models achieve these crazy performance improvements?
---

# Mixture of Experts (MoE)
> Disclaimer: These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025 instructed by both Prof. Baris Kasikci and TA Kan Zhu

## Overview

**Mixture of Experts (MoE)** is an architecture that replaces large feedforward networks with multiple expert networks and a selector/routing layer. The key advantage is that **you can increase the number of experts without affecting FLOPs**, enabling massive parameter scaling with constant computational cost.

### Popular MoE Models

- **GPT-4** (rumored to use MoE)
- **Mixtral** by Mistral AI
- **Grok** by xAI
- **DeepSeek MoE** series (v1, v2, v3)
- **Qwen MoE**
- **OlMoE** (open source)

## Why MoEs Are Getting Popular

### 1. Same FLOP, More Parameters = Better Performance

- MoE models achieve better performance with the same computational cost
- **Switch Transformers** showed clear scaling benefits with more experts
- **8x more parameters** for same accuracy using MoE

### 2. Faster Training

- **7x speedup** compared to dense models
- More efficient parameter utilization during training
- **DeepSpeed-MoE**: 5x lower training cost vs dense models for same accuracy

### 3. Competitive Performance

- **DeepSeek V2** demonstrates MoE models can match or exceed dense model performance
- **Mixtral 8x7B**: Matches LLaMA 2 70B performance with 5x fewer active parameters
- Efficient scaling to very large parameter counts (600B+ total parameters)

## Core MoE Architecture

### Dense vs Sparse Model Comparison
```
Dense Model: FFN 	o Single large feedforward network
Sparse Model: MoE Layer 	o Multiple expert FFNs + Router
```

### Key Components

- **Router/Gating Function**: Decides which expert(s) to use for each token
- **Expert Networks**: Multiple specialized feedforward networks
- **Routing Strategy**: How tokens are assigned to experts

### Architecture Variations

#### What Varies Across MoE Models
1. **Routing Function**: How tokens are assigned to experts
2. **Expert Sizes**: Size and number of expert networks
3. **Training Objectives**: Load balancing and auxiliary losses

#### Common Patterns

- **Most Common**: Replace MLP layers with MoE layers
- **Less Common**: MoE for attention heads (e.g., JetMoE)

## Routing Mechanisms

### Top-K Routing (Most Popular)
**Formula**: For each token, select top-k experts based on routing scores

$$h_t^l = \sum_{i=1}^{N} g_{i,t} \cdot \text{FFN}_i^{(l)}(u_t) + u_t$$

Where:
- $g_{i,t}$ = gating weight for expert $i$ and token $t$
- $s_{i,t} = \text{Softmax}_i(u_t^T W_g)$ (routing scores)

### Routing Strategies
1. **Token Choice**: Each token selects top-k experts
2. **Expert Choice**: Each expert selects which tokens to process

### Popular Routing Configurations
| Model | Total Experts | Active Experts | Shared Experts | Top-K |
|-------|---------------|----------------|----------------|--------|
| Mixtral | 8 | 2 | 0 | 2 |
| DBRX | 16 | 4 | 0 | 4 |
| DeepSeek v1 | 64 | 6 | 2 | 6 |
| DeepSeek v3 | 256 | 8 | 1 | 8 |
| Qwen 1.5 | 60 | 4 | 4 | 4 |

## Training Challenges and Solutions

### Major Challenge: Non-Differentiable Routing
**Problem**: Sparse gating decisions break gradient flow - only selected experts receive gradients.

### Solutions:
1. **Reinforcement Learning**: Use REINFORCE to optimize routing policies
2. **Stochastic Perturbations**: Add noise to make routing more robust
3. **Heuristic Balancing Losses**: Force balanced expert usage

### Load Balancing Loss
**Critical Issue**: Without load balancing, models collapse to using only 2 experts.

#### Switch Transformer Load Balancing Loss
**Purpose**: Systems efficiency requires using experts evenly to avoid bottlenecks.

$$\mathcal{L}_{\text{aux}} = \alpha \cdot N \cdot \sum_{i=1}^{N} f_i \cdot P_i$$

Where:
- $f_i$ = fraction of tokens dispatched to expert $i$: $f_i = \frac{1}{T}\sum_{x \in B} \mathbf{1}\{\text{argmax } p(x) = i\}$
- $P_i$ = fraction of router probability allocated for expert $i$: $P_i = \frac{1}{T}\sum_{x \in B} p_i(x)$
- $N$ = number of experts
- $T$ = number of tokens in batch $B$

**Key insight**: The derivative with respect to $P_i$ is $\frac{\alpha N}{T}\sum \mathbf{1}_{\text{argmax } p(x)=i}$, so more frequent use leads to stronger downweighting.

### DeepSeek MoE Balancing Variations

#### DeepSeek v1-v2: Dual Balancing

- **Per-expert balancing**: Same as Switch Transformer
- **Per-device balancing**: Aggregates the objective by device to balance communication

Per-device balancing loss:
$$\mathcal{L}_{\text{DevBal}} = \alpha_2 \sum_{i=1}^{D} f_i^d P_i^d$$

Communication balancing loss (v2):
$$\mathcal{L}_{\text{CommBal}} = \alpha_3 \sum_{i=1}^{D} f_i^{in} P_i^{out}$$

#### DeepSeek v3: Auxiliary Loss-Free Balancing

- Uses **per-expert biases** with online learning
- Adjusts routing scores: $g'_{i,t} = \begin{cases} s_{i,t}, & \text{if } s_{i,t} + b_i \in \text{TopK} \\ 0, & \text{otherwise} \end{cases}$
- **Sigmoid+Softmax routing**: $s_{i,t} = \text{Sigmoid}(u_t^T e_i)$

## DeepSeek MoE Architecture Evolution

### DeepSeek v1 (16B total, 2.8B active)

- **Architecture**: Shared (2) + Fine-grained (64/4) experts, 6 active
- **Routing**: Standard top-k routing
- **Balancing**: Standard auxiliary loss (Expert + Device)

### DeepSeek v2 (236B total, 21B active)

- **Architecture**: Shared (2) + Fine-grained (160/10) experts, 6 active
- **New features**:
  - **Top-M device routing**: Limits tokens to at most M devices
  - **Communication balancing loss**: Balances both inbound and outbound communication

### DeepSeek v3 (671B total, 37B active)

- **Architecture**: Shared (1) + Fine-grained (258) experts, 8 active
- **New features**:
  - **Sigmoid+Softmax routing**
  - **Aux-loss-free**: No auxiliary balancing losses needed
  - **Top-M device routing**: Enhanced routing strategy

#### Fine-Grained Expert Architecture

- **DeepSeek/Qwen approach**: Many small experts + shared experts
- **Shared experts**: Always active for all tokens
- **Routed experts**: Conditionally activated based on routing

## Training Methods: Upcycling

**Concept**: Initialize MoE models from pre-trained dense language models.

### Process
1. Take a pre-trained dense model
2. Copy weights to initialize multiple experts
3. Add routing mechanism from scratch
4. Continue training with additional data

### Qwen MoE Example

- **Base**: Initialized from Qwen 1.8B model
- **Configuration**: Top-k=4, 60 experts with 4 shared
- **Results**: One of the first confirmed successful upcycling approaches
- **Performance**: Achieves competitive results with significantly fewer active parameters

## System Optimizations

### Training Optimizations

#### Expert Parallelism

- **Expert parameters**: Partitioned across devices (like model parallelism)
- **Communication**: Two All-to-All operations per forward/backward pass
  1. **Dispatch**: Route tokens to their assigned experts
  2. **Combine**: Gather results back to original positions

#### All-to-All Communication Pattern
**Purpose**: Scatter/gather distinct messages from each participant to every other participant.

```
GPU0: [A0, A1, A2, A3] 	o GPU0: [A0, B0, C0, D0]
GPU1: [B0, B1, B2, B3] 	o GPU1: [A1, B1, C1, D1]
GPU2: [C0, C1, C2, C3] 	o GPU2: [A2, B2, C2, D2]
GPU3: [D0, D1, D2, D3] 	o GPU3: [A3, B3, C3, D3]
```

**Process**:
1. **Dispatch phase**: Layout transformation 	o Group tokens by target expert 	o First All-to-All
2. **Expert compute**: Each expert processes its assigned tokens
3. **Combine phase**: Second All-to-All 	o Layout transformation 	o Restore original positions

### Communication Bottlenecks

**Problem**: All-to-All operations consume significant time:

- Average **34.1%** of total step time in DeepSeek V3
- Synchronous and blocking operation with large data transfers
- Slowdown varies: Median 2x, Maximum ~4x when overlapping with other operations

### Training Optimizations: Lina

#### Core Strategy
**Intuition**: Always prioritize All-to-All and avoid bandwidth sharing.

**Techniques**:
1. **Tensor Partitioning**: Break AllReduce into micro-operations
2. **Priority Scheduling**: Give All-to-All operations higher priority
3. **Pipelining**: Overlap computation with All-to-All communication

**Results**: Up to 2.4x speedup in MoE layer execution

## Deployment Strategies

### Memory Requirements
**Mixtral 8x7B Example**:

- Attention layers: ~3.5GB
- Expert layers: ~90GB
- **Total**: ~93.5GB (doesn't fit on single GPU)

### Inference Optimizations

#### 1. Offloading Approaches

- **FlexGen**: Throughput-oriented datacenter solution
- **Mixtral-Offload**: Caching and prefetching focused
- **DeepSpeed Zero-Offload**: Training-focused
- **Problem**: High overhead from frequent weight copying (>50ms vs ~2ms execution)

#### 2. CPU Compute (Fiddler)
**Core Idea**: Compute experts on CPU instead of copying weights to GPU.

**Strategy**:
1. **Initialization**: Keep attention weights on GPU, profile expert popularity
2. **Placement**: Popular experts on GPU, others on CPU
3. **Execution**: Decide per token whether to compute on CPU or GPU
4. **Optimization**: Activation copying <0.1ms vs Weight copying >50ms

**Latency Model**:
$$\arg\min_{\text{cpu\_expert,gpu\_expert}} \max\left(\sum_{i \in \text{cpu\_expert}} (n\_\text{input}_i \times \text{latency}_{\text{cpu}}), \sum_{i \in \text{gpu\_expert}} ((1 - \text{is\_on\_gpu}_i) \times \text{latency}_{\text{gpu}})\right)$$

**Performance**: 8.2-10.1x faster than Mixtral-Offloading, 19.4-22.5x faster than DeepSpeed MII

#### 3. Expert Popularity Profiling
**Challenge**: During inference, expert popularity differs from training due to load balancing losses.

**Solution**:
1. Collect expert selection patterns during training (after load balancing converges)
2. Create expert selection paths across layers
3. Use this profile to predict resource allocation during inference
4. Allocate more resources to popular experts

### DeepSeek V3 Deployment

#### Training Infrastructure

- **32-way Expert Parallelism** (8 experts per GPU)
- **All-to-all communication** optimizations
- **Redundant experts** for load balancing

#### Prefill Stage (32-way Expert Parallelism)

- **Total experts**: 256 (8 experts per GPU)
- **Communication optimization**: Reduce InfiniBand traffic by limiting node transmission
- **Redundancy**: Each GPU hosts one additional redundant expert for high-load experts

#### Decode Stage (320 GPUs across 40 nodes)

- **Attention**: TP4+SP, DP80
- **Experts**: EP320 (each GPU stores only one expert)
- **Redundancy**: 64 GPUs handle redundant and shared experts
- **Optimization**: Overlap attention micro-batches with expert layer micro-batches

### Batching MoE Computation

#### GroupGemm Approach
**Process**:
1. **Routing**: Determine expert assignments for each token
2. **Permutation**: Group tokens by target expert using prefix sum
3. **Computation**: Use GroupGemm for efficient batched computation
4. **Un-permutation**: Restore tokens to original positions
5. **Mixing**: Combine expert outputs with routing weights

**Efficiency**: Single GPU kernel with batching benefits across all experts.

#### Permutation Index Generation
**Method**: Use prefix sum (scan) operations for efficient parallel permutation index calculation:

- Convert expert selection to binary mask
- Apply cumsum to flattened transpose
- Reshape to get permutation indices
- Highly parallelizable on GPU

## Performance Results

### Training Efficiency

- **DeepSpeed-MoE**: 5x lower training cost vs dense models for same accuracy
- **Switch Transformers**: Clear scaling benefits with more experts
- **Mixtral 8x7B**: 5x lower training cost for same accuracy as LLaMA 2 70B

### Inference Improvements

- **Fiddler**: 8.2x faster than Mixtral-Offloading
- **Lina**: Up to 2.4x speedup in MoE layer execution
- **Expert popularity prediction**: Approaches ideal performance with perfect knowledge

### Benchmark Performance
**Mixtral 8x7B vs Dense Models**:

- Matches LLaMA 2 70B performance with 5x fewer active parameters
- Competitive or superior performance across MMLU, Knowledge, Reasoning, and Comprehension tasks
- Demonstrates substantial efficiency gains in both parameter count and training cost

## Key Takeaways

1. **MoEs enable parameter scaling without proportional FLOP increases**
2. **Load balancing is critical** - models collapse without it
3. **Communication is the bottleneck** in distributed MoE training (34.1% of training time)
4. **System optimizations are essential** for practical deployment
5. **Recent models (DeepSeek V3) achieve competitive performance** with massive scale
6. **Upcycling from dense models** is a viable initialization strategy
7. **CPU-GPU hybrid approaches** can dramatically improve inference efficiency
8. **Expert popularity profiling** enables better resource allocation during inference