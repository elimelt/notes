---
title: Quantization in LLM Serving Systems
category: Machine Learning Systems
tags: quantization, low precision, performance, memory efficiency
description: Overview of quantization techniques for LLM serving systems, focusing on theoretical foundations and practical applications.
---

# Quantization

## Fundamentals

### What is Quantization?
**Quantization** is the process of reducing the precision of numerical representations to achieve:
- **Reduced memory footprint**
- **Lower latency**
- **Decreased energy consumption**
- **Compact representation**

### Key Idea
Convert high-precision floating-point numbers (FP32) to lower-precision representations (INT4, INT8) while maintaining acceptable accuracy.

### Energy Motivation
- **Energy scales quadratically** with bit-width
- **4x bit width** 	o **~16x energy consumption**
- **Memory access costs** (DRAM: 640pJ vs 8b Add: 0.03pJ)

### Why Quantization Works
- **Activation ranges are well-defined** in neural networks
- **Even distributions** lead to better training outcomes
- **Proper initialization** prevents activation divergence and gradient instability

---

## Floating Point Representations

### FP32 (Full Precision)
- **Sign**: 1 bit
- **Exponent**: 8 bits
- **Significand/Mantissa**: 23 bits
- **Total**: 32 bits

### FP16 (Half Precision)
- **Sign**: 1 bit
- **Exponent**: 5 bits
- **Significand/Mantissa**: 10 bits
- **Total**: 16 bits

### Dynamic Range vs Precision Trade-offs
- **Dynamic Range**: Range of representable numbers (better for training)
- **Precision**: Distance between neighboring values (better for inference)
- **INT8**: Limited dynamic range (-127 to 127) but consistent precision

---

## Linear Quantization

### Mathematical Formulation
**Quantization**: $q = \text{clip}(\text{round}(r/S + Z), -2^{b-1}, 2^{b-1})$

**Dequantization**: $r = S(q - Z)$

Where:
- $S = \frac{r_{max} - r_{min}}{q_{max} - q_{min}}$ (scaling factor)
- $Z$ = zero point
- $b$ = bit width

### Sources of Error
1. **Rounding Error**: Bounded by [-S/2, S/2]
2. **Clipping Error**: Values outside representable range

### Symmetric vs Asymmetric Quantization
- **Symmetric**: Zero point Z = 0 (simpler computation)
- **Asymmetric**: Non-zero Z (more flexible, better for skewed distributions like ReLU outputs)

### Matrix Multiplication with Quantization
$$Y = S_W S_X [q_W q_X - q_W Z_X - q_X Z_W + Z_W Z_X]$$

**Symmetric quantization** eliminates the overhead terms when $Z_W = Z_X = 0$.

---

## Non-Linear Quantization

### Clustering-Based Approach
- **Use case**: Skewed weight distributions
- **Method**: K-means clustering to determine quantization levels
- **Storage**:
  - Indices: $\log_2(N)$ bits per weight
  - Codebook: N centroids in original precision
  - **Example**: 3.2x compression for 4-bit quantization

### Granularity Options
1. **Per-Tensor**: Single scale/zero-point for entire tensor
2. **Per-Channel/Vector**: Scale per channel (more precise)
3. **Per-Group**: Intermediate granularity

**Trade-off**: Finer granularity 	o Higher precision but increased overhead

---

## Training Workflows

### Post-Training Quantization (PTQ)
- **Training**: Uses full precision (FP32/BF16)
- **Inference**: Applies quantization to weights and/or activations
- **Simplest approach** but may have accuracy degradation

### Quantization-Aware Training (QAT)
- **Training**: Simulates quantization effects during training
- **Method**: Quantize 	o Dequantize in forward pass
- **Backpropagation**: Uses Straight-Through Estimator (STE) for differentiability
- **Results**: Generally outperforms PTQ

### Straight-Through Estimator (STE)
- **Problem**: Step function derivative is 0 or infty
- **Solution**: Use identity function gradient: $\frac{\partial}{\partial x}\text{quantize}(x) \approx 1$

---

## LLM-Specific Quantization Challenges

### Outlier Problem
- **Observation**: Quantization accuracy drops significantly for large models (>6.7B parameters)
- **Cause**: Emergence of outlier features in activations
- **Impact**: Sharp accuracy degradation with standard quantization

### Modern LLM Context
**Example - DeepSeek V3**:
- **FP8 quantization**: 671B parameters 	imes 1 byte = 671 GB (fits ~5 H200s)
- **BF16 weights**: 671B parameters 	imes 2 bytes = 1.3 TB

---

## Advanced LLM Quantization Methods

### LLM.int8()
**Key Ideas**:
1. **Vector-wise quantization** for better outlier handling
2. **Mixed precision**: Keep outliers in FP16, quantize regular values to INT8
3. **Decomposition**: Separate outlier and regular computations

### SmoothQuant (W8A8)
**Motivation**: Outliers typically in activations, not weights

**Core Concept**: Migrate quantization difficulty
- **Formula**: $s_j = \frac{\max(|X_j|)^\alpha}{\max(|W_j|)^{1-\alpha}}$
- **Process**: $WX \rightarrow Q(W \cdot s)(s^{-1} \cdot X)$
- **Optimal alpha**: Empirically found to be 0.5

**Benefits**: Balances quantization difficulty between weights and activations

### AWQ (Activation-Aware Weight-Only Quantization)
**Target**: Low-batch scenarios where activation quantization is prohibitive

**Key Insights**:
1. **Weight-only quantization** (W4) for memory efficiency
2. **Salient weight identification** using activation magnitudes
3. **Per-channel scaling** to protect important weights

**Method**: $WX \rightarrow Q(W \cdot s)(s^{-1} \cdot X)$
- Scale important channels up before quantization
- Fuse inverse scaling with previous operations (e.g., LayerNorm)

---

## Quantization Performance Impact

### Accuracy vs Bit-width
- **High variance** across models and quantization levels
- **INT8**: Generally acceptable accuracy loss
- **INT4**: Requires careful techniques (AWQ, etc.)
- **INT3/INT2**: Significant accuracy challenges

### Rounding Schemes Impact
| Scheme | Accuracy |
|--------|----------|
| Nearest | 52.29% |
| Stochastic | 52.06plusequal5.52% |
| Stochastic (best) | 63.06% |
| Ceil/Floor | 0.10% |

---

## Summary

**Quantization** is essential for efficient LLM serving, providing:
- **Memory reduction** (2-8x compression)
- **Energy savings** (quadratic with bit-width)
- **Inference speedup** through specialized hardware

**Key techniques for LLMs**:
- **Handle outliers** through mixed precision or smoothing
- **Choose appropriate granularity** (per-tensor vs per-channel)
- **Balance accuracy vs efficiency** based on deployment requirements

**Modern approaches** (LLM.int8(), SmoothQuant, AWQ) address LLM-specific challenges while maintaining practical deployability.