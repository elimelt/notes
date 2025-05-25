---
title: Speculative Decoding in LLM Serving Systems
category: Machine Learning Systems
tags: speculative decoding, llm, performance, machine learning
description: Using speculative decoding to accelerate large language model inference, including algorithm details, performance analysis, and advanced techniques like Medusa and SpecInfer.
---

## Overview

**Speculative Decoding** is a technique to accelerate large language model inference by using a smaller, faster model to generate candidate tokens that are then verified by the larger target model in parallel.

### Key References
- Chen et al., "Accelerating Large Language Model Decoding with Speculative Sampling" (2023)
- Leviathan et al., "Fast Inference from Transformers via Speculative Decoding" (2022)

## Core Concept

### Speculative Decoding in a Nutshell
- **Small LM (Draft Model)**: Generates multiple tokens quickly
  - Can be obtained via quantization, pruning, training from scratch, etc.
- **Large LM (Target Model)**: Verifies the generated tokens for accuracy
- **Analogy**: Similar to speculative execution in CPUs - the small model may quickly generate many tokens that are mostly accurate

### Key Enabling Observations
1. **Compute vs Memory Bound**:
   - LLM serving is **compute-bound** at large batch sizes
   - At lower batch sizes, LLM serving becomes **memory-bound**
   - A batch of quickly generated tokens can be verified in parallel at once

2. **Draft Model Accuracy**:
   - Small (draft) LLMs are quite accurate for most "easy" tokens
   - Most of the time, a large (target) LLM is not needed
   - Example: "Geoffrey Hinton did his PhD at the University of..." 	o "Edinburgh" (easy) vs more complex completions (difficult)

## Algorithm Details

### Two-Step Process

1. **Draft Generation**: Run the draft model N iterations (e.g., 5)
   ```
   p1(x) = Mp(prefix) 	o x1
   pz(x) = Mp(prefix, x1) 	o xz
   ...
   p5(x) = Mp(prefix, x1, xz, xepsilon, x4) 	o x5
   ```

2. **Parallel Verification**: Run the target model once to verify all tokens
   ```
   q1(x), qz(x), qepsilon(x), q4(x), q5(x), q6(x) = Mq(prefix, x1, xz, xepsilon, x4, x5)
   ```

**Important**: Target model only produces distributions; sampling is only done from the draft model.

### Rejection Sampling Process

For each generated token, compare draft probability `p(x)` with target probability `q(x)`:

- **Case 1**: If `q(x) ge p(x)` 	o **Accept** the token
  - Target model is even more confident than draft model
- **Case 2**: If `q(x) < p(x)` 	o **Accept with probability `q(x)/p(x)`**

### Handling Rejections

When a token is rejected:
- Sample from the **corrected distribution**: `(q(x) - p(x))+`
- The `+` notation means we won't sample from negative probabilities
- This ensures the final distribution matches what the target model would produce

### Token Generation Outcomes

- **Best case**: All tokens accepted 	o K+1 tokens generated
- **Worst case**: First token rejected 	o 1 token generated
- **Key insight**: The worst case doesn't slow down the algorithm since a forward pass normally generates only one token

## Performance Analysis

### Speedup Factors
- **alpha**: Measure of how accurately the draft model represents the target model
- **gamma**: Number of draft model predictions before verification

### Speedup Results
The effectiveness shows:
- Higher accuracy (alpha) leads to better speedup
- Optimal gamma values exist (diminishing returns from too many draft predictions)
- Typical speedups: 1.4x to 3.4x depending on model size and task

## Advanced Techniques

### Medusa
**Key Innovation**: Add multiple prediction heads to a single model instead of using separate draft/target models.

**Architecture**:
- Add a few additional heads to predict tokens
- Easy to train the new heads with basic GPU
- Easy to serve (same parallelism patterns)
- Good speedup (~3x)

**Tree Attention**:
- Heads provide different token candidates, forming different candidate sequences
- Each sequence becomes a branch in the tree
- Tree attention mask allows each token to attend only to its predecessors
- Multiple sequences can be batched and verified in one forward pass

**Variants**:
- **Medusa-1**: Medusa heads fine-tuned on top of frozen backbone LLM
- **Medusa-2**: Medusa heads fine-tuned together with backbone LLM (requires special training recipe)

### SpecInfer
**Problem**: Single draft model may not provide enough "coverage"

**Solution**: Use multiple draft models simultaneously
- Creates a tree of sequences
- Can be verified simultaneously
- Leverages memory-bound regime for batched verification

**Token Tree Verification**:
- Uses topology-aware causal mask
- Applies attention in a manner aware of tree topology
- Enables batching of verification requests

## Implementation Details

### Parallel Token Probability Computation
```python
# Project to vocabulary
# I: (seq_len, hidden_dim): (seq_len, 4096)
# O: (seq_len, vocab_size): (seq_len, 128256)
logits = model_output.matmul(lm_head_weight.t())
# Pick the next token with highest probability
sample_output = torch.argmax(logits, dim=1)
# Return the next token following the last token in input sequence
return sample_output[-1].item()
```

This gives **next token probabilities for each token in the sequence in one pass**.

### Benefits Timeline Comparison
- **Base**: Sequential token generation
- **Sequence-based Speculative**: Alternating speculation and verification phases
- **Tree-based Speculative**: More efficient with parallel tree verification

## Results Summary

### Performance Gains
- **T5-Small**: 2.6x - 3.4x speedup
- **T5-Base**: 2.4x - 3.0x speedup  
- **T5-Large**: 1.4x - 2.2x speedup
- **Medusa**: Consistent ~2.5x - 3.6x across different task categories

### Key Insight
Diminishing returns from increased gamma (number of draft predictions) - there's an optimal balance between speculation depth and verification overhead.

## Practical Applications

Speculative decoding is particularly effective for:
- **Memory-bound serving scenarios** (lower batch sizes)
- **Tasks with predictable patterns** where draft models can be reasonably accurate
- **Scenarios requiring maintained output quality** (lossless acceleration)
- **Real-time applications** where latency reduction is critical