---
title: Batching in LLM Serving Systems
category: Machine Learning Systems
tags: batching, performance, throughput, latency, llm, serving systems, machine learning
description: Overview of batching techniques in LLM serving systems,
---

# Batching in LLM Serving Systems
> Disclaimer: These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025 instructed by both Prof. Baris Kasikci and TA Kan Zhu

## Overview

Batching is critical for LLM serving performance. The H100 needs **333 batch size** to reach peak performance. Batching involves two key considerations:
1. **User Experience** - maintaining response quality and latency
2. **Throughput** - maximizing system efficiency

## User Experience Metrics

### Key Latency Metrics
- **Time to First Token (TTFT)**: Time between user request submission and first token generation
  - TTFT = Queuing time + Prefill time
- **Time Per Output Token (TPOT/ITL/IBT)**: Time between each output token
- **Average TPOT**: Average time to produce one output token
- **End-to-end time**: Total time to queue, prefill, and decode entire request
- **Normalized Latency**: End-to-end time / number of output tokens

### Service Level Objectives (SLO)

Common SLO types in order of difficulty:
1. **End-to-end time** (easiest)
2. **TTFT + Average TPOT**
3. **TTFT + Maximum TPOT** (hardest)

**SLO Difficulty**: TTFT + TPOT_max > TTFT + TPOT_avg > E2E

### Deadline-Based SLO Management

- Can use **delay strategies** to smooth token generation when deadlines allow
- **TTFT + TPOT_max ge DDL > TTFT + TPOT_avg > E2E**
- Delaying token output can help meet consistent TPOT requirements

## Batching Strategies

### 1. Simple Batching
- **Characteristics**:
  - Lowest throughput
  - Short TTFT and TPOT
  - Low infrastructure complexity
- **Limitation**: Bottlenecked by longest decode request

### 2. Continuous Batching (Orca)

**Key Insight**: Admit new requests when decode requests finish

**Benefits**:
- **Higher throughput**: No waiting for longest decode request
- **Stabilized GEMM batch size**: Better GPU utilization
- **Reduced queuing time**: Requests enter at token granularity

**Drawbacks**:
- **Higher prefill latency**: Prefill batched with decode requests
- **Higher decode latency**: Prefill slows concurrent decode

#### Batch Size Calculation
For continuous batching with:
- Decode length `d`
- Prefill length `p`
- Request batch size `B`

**GEMM batch size** = $$\frac{p+d}{d+1}B = B + \frac{p-1}{d+1}B$$

**Key relationships**:
- Increasing prefill length 	o increases GEMM batch size
- Increasing decode length 	o decreases GEMM batch size
- For large `d`: GEMM batch size approx $(1 + \frac{p}{d})B$

**Example**: Batch size = 512, p/d = 2 	o GEMM batch size = 512	imes3 = 1536

### 3. Chunked Prefill

**Problem**: Simple continuous batching creates generation stalls due to variable prefill sizes

**Solution**: Break prefill into fixed-size chunks

**Benefits**:
- **Highest throughput**: Further stabilized batch size
- **Controlled decode latency**: Eliminates generation stalls
- **Consistent GEMM batch size**: Better performance predictability

**Drawbacks**:
- **Longest TTFT**: More cycles needed for prefill
- **Higher infrastructure complexity**: Chunking management overhead

#### Fixed Token Budget Approach
- Allocate fixed token budget per iteration
- Mix decode requests with prefill chunks
- Maintains constant GEMM batch size

### 4. Prefill-Decode Disaggregation

**Architecture**: Separate clusters for prefill and decode operations

**Process**:
1. Prefill server processes input tokens
2. KV cache transferred to decode server
3. Decode server handles token generation

**Benefits**:
- **Short TTFT and TPOT**: Decoupled operations
- **Optimal latency**: Can scale to one request per machine

**Drawbacks**:
- **Low throughput**: Prefill cluster fully utilized, decode underutilized
- **High infrastructure complexity**: KV cache transfer overhead
- **Network overhead**: KV transfer can be significant (160ms for 16K tokens)

#### KV Transfer Optimization
- Use **chunked prefill** + **layer-wise transfer** to overlap KV movement
- Transfer last layer of last chunk when prefill completes

## Batching Limitations

### 1. SLO Constraints

**For PD Disaggregation**:
- Prefill batch limit 	o TTFT constraint
- Decode batch limit 	o TPOT constraint: `B*attn + GEMM(B) + C < TPOT`

**For Chunked Prefill**:
- Cycle Time = GEMM(B_dense) + $\frac{d}{p+d}B_{dense}$ 	imes attn
- Constraints: Cycle time < TPOT, $\frac{p+d}{B_{dense}}$ 	imes Cycle Time < TTFT

### 2. GPU Memory Capacity

**KV Cache Limitations**:
- For 8B model on H100: ~512K tokens max
- **Challenge**: Output length unknown, KV cache grows over time

#### Batch Size Formulas

**For constant lengths**:
$$B = \frac{C}{p + \frac{1}{2}d}$$

**For variable lengths**:
$$B = \frac{d_{avg}C}{(pd)_{avg} + \frac{1}{2}(d^2)_{avg}}$$

Where:
- `C` = KV cache capacity
- `p` = prefill length
- `d` = decode length
- Longer requests occupy cache longer, reducing effective batch size

**Example**: 1K input, uniform 0-4K output 	o effective batch size approx 220

### 3. Memory Management Strategies

**Prediction-Based Control**:
- Use small encoder models to predict output length
- Stop prefill when KV cache predicted to exceed capacity
- Add decode pending queues for PD disaggregation

**Out-of-Memory Handling**:
- Similar to prefix sharing eviction
- Offload KV cache to CPU memory (faster than recomputation)
- Evict least recently used requests

## Performance Comparison

| Method | Throughput | TTFT | TPOT | Infra Complexity |
|--------|------------|------|------|------------------|
| Simple | Lowest | Short | Short | Low |
| Continuous Batching | High | Longer | Long, Unstable | Low |
| Chunked Prefill | Highest | Longest | Long, Controlled | Medium |
| PD Disaggregation | Low | Short | Short | High |

## Advanced Considerations

### SLO Attainment Strategies
- **95% SLO targets** may require:
  - Dropping long input/output requests
  - Infinite delay for predicted SLO violations
  - Prioritizing high-SLO requests

### Fairness Constraints
- All requests should make progress
- Equal throughput share per user
- SLO violation "badness" metrics vs binary attain/violate

### Output Length Impact
- Longer requests stay in KV cache longer
- Creates memory pressure and batch size oscillations
- Prediction accuracy critical for optimal performance