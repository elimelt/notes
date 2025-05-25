
---
title: Parallelism in LLM Serving Systems
category: Machine Learning Systems
tags: parallelism, performance, throughput, latency, llm, serving systems, machine learning
description: Overview of parallelism techniques in LLM serving systems, focusing on theoretical foundations and practical applications.
---

# Parallelism in LLM Serving Systems

## Introduction & Motivation

### Limits to GPU-based Scaling

#### Compute Limitations

* GPU improvements have included:

  * Number formats (FP32 	o FP16 	o Int8)
  * Specialized instructions (DP4A, HMMA, IMMA)
  * Process nodes (28nm 	o 5nm)
  * Sparsity support
* Still, single GPU performance remains fundamentally limited.
* Supercomputers can reach **exaflop** scales, but LLMs continue to push hardware constraints.

#### Memory Limitations

* Model sizes are growing exponentially:
  ELMo (94M) 	o GPT-2 (1.5B) 	o GPT-3 (175B) 	o MT-NLG (530B)
* **A single GPU cannot hold full model weights or intermediate activations.**

### Solution: Multi-GPU, Multi-Machine Parallelism

#### Network Infrastructure

* **Intra-node (within machine)**:

  * NVLink 3.0: 600 GB/s
  * PCIe 4.0: 32 GB/s
* **Inter-node (between machines)**:

  * InfiniBand HDR: 25 GB/s

**Goal**: Distribute compute and memory across devices efficiently.

---

## Collective Communication Primitives

### Key Operations

* **AllReduce**: Aggregates data across devices.
* **Broadcast**: Sends data from one device to all others.
* **AllGather**: Each device collects data from all others.
* **ReduceScatter**: Combines reduction and scatter.

**AllReduce can be implemented as ReduceScatter + AllGather**, which is bandwidth-optimal.

---

## Key Concepts in ML Training/Serving

### State Classifications

* **Model Parameters**: Learned weights (used in both training & serving).
* **Gradients**: For updating parameters during training.
* **Activations**: Intermediate results from forward pass (used in both).
* **Optimizer State**: Momentum, variance, etc. for training.
* **KV Cache**: Used in serving for autoregressive models to avoid recomputing past tokens.

---

## Parallelism Strategies

### Goals

* Scale with **batch size** (data)
* Scale with **model size** (parameters)

---

## Data Parallelism

### Concept

* Each GPU has a **full model copy**.
* Batches split across GPUs.
* Gradients are **aggregated** post-backward.

### Implementations

#### Parameter Server (Centralized)

* Gradients sent to central server; updated params broadcast.
* **Scalability bottleneck**: Central point of failure and bandwidth.

#### AllReduce-based (Decentralized)

* Peer-to-peer gradient aggregation:

  * Ring, Tree, Butterfly, or ReduceScatter + AllGather.

### Limitations

* Full model + gradients + optimizer state on each GPU.
* Does **not scale** to models larger than a single GPU's memory.

---

## Pipeline Parallelism

### Concept

* Split model **vertically** across layers into pipeline stages.
* Each stage runs on a separate GPU.

### Execution

* Forward pass: left to right
* Backward pass: right to left
* GPUs exchange **activations**, not parameters.

### Scheduling Strategies

#### GPipe

* Microbatching to improve utilization.
* **Trade-off**: More memory needed to store microbatches.

#### 1F1B (One Forward, One Backward)

* Keeps pipeline full during steady state.
* Phases: warm-up 	o alternating 	o drain.

#### Zero Bubble Pipeline (ZBP)

* Splits backward pass into:

  1. Activation gradients
  2. Weight gradients (can be delayed)
* Eliminates pipeline idle time.

### Analysis

#### Bubble Ratio

* \$(p - 1)/m\$ where \$p\$ = stages, \$m\$ = microbatches
* Larger \$m\$ reduces bubble size.

### Characteristics

**Advantages**:

* Shards model (less memory per GPU)
* Point-to-point activation communication

**Disadvantages**:

* **Batch-size sensitive**
* **Pipeline bubbles** without careful scheduling

---

## Tensor Parallelism

### Concept

* Split model **horizontally**: partition within layers.
* Each GPU holds **part of a layer**.

### Matrix Ops Decomposition

#### MLP Example:

\$Z = \text{Dropout}(\text{GeLU}(XA)B)\$

* **Column-split A**: \$Y\_i = \text{GeLU}(XA\_i)\$
  	o No communication
* **Row-split B**: \$Z\_i = Y\_i B\_i\$
  	o **AllReduce** to combine \$Z = \sum Z\_i\$

#### Self-Attention Example

* Split heads: \$Q = \[Q\_1, Q\_2]\$, etc.
* Each GPU processes subset of heads.
* **AllReduce** after attention for combined output.

### Communication Patterns

* Forward: Identity 	o AllReduce
* Backward: AllReduce 	o Identity

### Characteristics

**Advantages**:

* No pipeline bubbles
* Doesn't require large batches
* High utilization with fast interconnects

**Disadvantages**:

* High communication volume:

  * Pipeline: \$bsh\$ (point-to-point)
  * Tensor: \~\$8bsh\$ (AllReduce-heavy)
* Needs fast intra-node links (e.g., NVLink)

---

## Memory Optimization: Activations

### Formula

$\text{Memory per layer} = sbh\left(34 + 5\frac{as}{h}\right)$

Where:

* \$s\$ = sequence length
* \$b\$ = batch size
* \$h\$ = hidden size
* \$a\$ = attention heads

### Optimization Techniques

#### Checkpointing vs Stashing

* **Stashing**: Stores all activations (high memory, faster)
* **Checkpointing**: Stores minimal; recomputes during backward pass
  	o **Memory savings** at cost of \~33% throughput hit
  	o Enables larger batch sizes

### Tensor Parallelism Impact

With \$t\$ tensor-parallel units:
$\text{Memory per layer} = sbh\left(10 + \frac{24}{t} + 5\frac{as}{ht}\right)$

* LayerNorm (4sbh) + Dropout (2sbh) + Inputs (4sbh) = **10sbh**
* Remaining terms shrink with larger \$t\$

---

## Sequence Parallelism

### Motivation

* The 10sbh term includes pointwise ops 	o **can be split along sequence**

### Implementation

* Split LayerNorm, Dropout, and Input activations along sequence
* All-Gather before MLP to reassemble
* Results in **true linear memory scaling** with device count

### Memory Scaling Comparison

| Configuration     | Activations per Layer                       |
| ----------------- | ------------------------------------------- |
| No parallelism    | \$sbh(34 + 5\frac{as}{h})\$                 |
| Tensor only       | \$sbh(10 + \frac{24}{t} + 5\frac{as}{ht})\$ |
| Tensor + Sequence | \$sbh(\frac{34}{t} + 5\frac{as}{ht})\$      |

---

## ZeRO Optimization / FSDP

### Memory Breakdown (for \$\Psi\$ params)

* FP16 params: \$2\Psi\$
* Gradients: \$2\Psi\$
* FP32 optimizer: \$16\Psi\$
  	o Total per GPU (naive): \$20\Psi\$

### ZeRO Stages

* **Stage 1**: Shard optimizer state

* **Stage 2**: Shard gradients

* **Stage 3**: Shard model parameters
  	o Total memory: \$\frac{(2 + 2 + K)\Psi}{N\_d}\$

* Reduces memory linearly with number of devices \$N\_d\$

* Used in **Fully Sharded Data Parallel (FSDP)**

---

## 3D Parallelism Strategy

### Deployment Phases

1. **Fit model on memory**

   * Use **tensor parallel** within node
   * Use **pipeline parallel** across nodes

2. **Scale compute**

   * Add **data parallelism**
   * Use gradient accumulation to improve communication efficiency

### Example: 8	imes8 GPU nodes

* Tensor: 8-way intra-node
* Pipeline: 8-way across nodes
* Data: Across groups of nodes

### Considerations

* Batch size must be large enough for efficient pipeline use
* Tensor size should align with bandwidth (avoid over-splitting)
* Best setup depends on model, hardware, and latency/bandwidth topology

---

## Summary

### Takeaways

1. **Three main parallelism forms**:

   * Data: scale batch size
   * Pipeline: scale model depth
   * Tensor: scale width

2. **Communication varies**:

   * Data: gradient AllReduce
   * Pipeline: point-to-point activations
   * Tensor: AllReduce per layer

3. **Memory optimization is essential**:

   * Activation dominates for large models
   * Checkpointing and sequence parallel reduce cost

4. **Hardware-aware deployment**:

   * Use fast interconnects for tensor parallel
   * Use pipeline across slower links
   * Match parallel strategy to topology

5. **Combine all three (3D parallelism)** for optimal scale and efficiency.
