---
title: Quantization in LLM Serving Systems
aliases:
  - llm-serving-systems/quantization
category: Machine Learning Systems
tags:
  - quantization
  - low-precision
  - performance
  - memory-efficiency
  - machine-learning
date: 2025-05-25
updated: 2026-07-30
status: evergreen
description: Linear and non-linear quantization, PTQ vs QAT, the LLM outlier problem, and the main deployed methods (LLM.int8(), SmoothQuant, AWQ).
sources:
  - title: CSE 599K, LLM Serving Systems, University of Washington, Spring 2025 (lecture notes)
    type: lecture
  - title: "LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale"
    url: https://arxiv.org/abs/2208.07339
    type: paper
  - title: "SmoothQuant: Accurate and Efficient Post-Training Quantization for Large Language Models"
    url: https://arxiv.org/abs/2211.10438
    type: paper
  - title: "AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration"
    url: https://arxiv.org/abs/2306.00978
    type: paper
  - title: "Up or Down? Adaptive Rounding for Post-Training Quantization"
    url: https://arxiv.org/abs/2004.10568
    type: paper
---

## Purpose

This note covers how quantization works, why it is harder for LLMs than for small networks, and the methods that made low-precision LLM serving practical. Quantization changes both arithmetic throughput and model-memory demand, so its serving impact is best interpreted with [[ml/serving-systems/performance-modeling|Performance Modeling]] and [[ml/serving-systems/memory-management|Memory Management]].

These are notes for CSE 599K "LLM Serving Systems" at the University of Washington, Spring 2025, taught by Prof. Baris Kasikci with TA Kan Zhu.

## Core idea

Quantization maps high-precision numbers (FP32, BF16) to low-precision representations (INT8, INT4, FP8) while keeping accuracy acceptable. The payoff comes in memory footprint, latency, and energy. Energy is the underrated one: multiplier energy grows roughly quadratically with bit width, so 4x the bits costs around 16x the energy, and memory access dwarfs arithmetic anyway (a DRAM access costs about 640 pJ against 0.03 pJ for an 8-bit add, per Horowitz's ISSCC 2014 energy tables). Moving fewer bytes is worth more than doing cheaper math.

Quantization works at all because activation ranges in trained networks are well behaved: normalization and careful initialization keep distributions concentrated, so a small set of representable values covers almost everything that occurs.

The scale of the stakes for modern models: DeepSeek-V3 at 671B parameters is 1.3 TB in BF16 and 671 GB in FP8, the difference between two nodes and about five H200s.

## Number formats

FP32 spends 1 bit on sign, 8 on exponent, 23 on mantissa. FP16 spends 1/5/10. The exponent bits buy dynamic range (how far apart the smallest and largest representable numbers are), the mantissa bits buy precision (how close neighboring values sit). Training wants dynamic range because gradients span many magnitudes, which is why BF16 keeps FP32's 8 exponent bits. Inference tolerates less range, so integer formats work: INT8 covers only $[-127, 127]$ with a fixed step, trading range for uniform precision.

## Linear quantization

The affine map between real values $r$ and integers $q$ with scale $S$, zero point $Z$, and bit width $b$:

$$q = \text{clip}\left(\text{round}\left(\frac{r}{S} + Z\right),\; -2^{b-1},\; 2^{b-1}-1\right), \qquad r \approx S(q - Z)$$

with $S = \frac{r_{max} - r_{min}}{q_{max} - q_{min}}$. Error comes from two places: rounding error, bounded by $[-S/2, S/2]$, and clipping error for values outside the representable range. Choosing the range is a tradeoff between the two, since widening the range shrinks clipping but grows $S$ and with it the rounding error.

Symmetric quantization fixes $Z = 0$. The reason it matters shows up in matmul:

$$Y = S_W S_X \left[q_W q_X - q_W Z_X - q_X Z_W + Z_W Z_X\right]$$

With $Z_W = Z_X = 0$ the three correction terms vanish and the integer kernel is just $q_W q_X$. Asymmetric quantization keeps the flexibility for skewed distributions (ReLU outputs, for instance) at the cost of those terms.

Granularity is the other axis: one scale per tensor, per channel, or per group of channels. Finer granularity tracks the data better and stores more metadata; per-channel is the common middle ground for weights.

For genuinely skewed weight distributions there is non-linear quantization: cluster the weights (k-means), store a small codebook of centroids in full precision plus $\log_2(N)$-bit indices per weight, as in [Deep Compression](https://arxiv.org/abs/1510.00149). A 4-bit codebook version compresses about 3.2x once codebook overhead is counted.

## PTQ and QAT

Post-training quantization (PTQ) trains in full precision and quantizes afterward, possibly with a small calibration set. Simple, and the accuracy cost grows as bit width drops.

Quantization-aware training (QAT) simulates quantization in the forward pass (quantize then dequantize) so the network learns weights that survive rounding. The rounding step has zero gradient almost everywhere, so the backward pass uses the straight-through estimator: pretend $\frac{\partial}{\partial x}\text{quantize}(x) \approx 1$. QAT generally beats PTQ at the same bit width, at the cost of a training loop.

Rounding policy alone moves accuracy a lot at low bit width. The [AdaRound](https://arxiv.org/abs/2004.10568) experiments quantizing a ResNet's weights to 4 bits found nearest rounding at 52.29% accuracy, stochastic rounding at 52.06 ± 5.52% with the best draw reaching 63.06%, and ceil/floor collapsing to 0.10%. Rounding direction is worth optimizing, which is AdaRound's whole point.

## Why LLMs are special: outliers

Quantization recipes that work on small models fall apart on large ones. [LLM.int8()](https://arxiv.org/abs/2208.07339) traced the failure to outlier features: past roughly 6.7B parameters, a few activation dimensions systematically carry values orders of magnitude larger than the rest. One shared scale per tensor either clips the outliers or crushes the precision of everything else, and accuracy drops sharply.

The three deployed answers each handle outliers differently:

### LLM.int8() (W8A8, mixed precision)

Quantize per vector rather than per tensor, detect the outlier dimensions, and decompose the matmul: outlier columns run in FP16, everything else in INT8, results summed. Accuracy holds, at the price of a more complicated kernel.

### SmoothQuant (W8A8)

Outliers live in activations while weights are comparatively easy to quantize, so [SmoothQuant](https://arxiv.org/abs/2211.10438) migrates difficulty from activations to weights with a per-channel rescaling:

$$WX \rightarrow Q(W \cdot s)\,(s^{-1} \cdot X), \qquad s_j = \frac{\max(|X_j|)^\alpha}{\max(|W_j|)^{1-\alpha}}$$

The paper finds $\alpha = 0.5$ balances the two sides. Both weights and activations then quantize to INT8 with standard kernels.

### AWQ (W4, weight-only)

At low batch size, serving is memory bound (see [[ml/serving-systems/performance-modeling|Performance Modeling]]), so shrinking weights is what buys latency and activation quantization buys little. [AWQ](https://arxiv.org/abs/2306.00978) quantizes weights to 4 bits, identifies the salient weight channels by looking at activation magnitudes rather than weight magnitudes, and scales those channels up before quantization so they lose less precision, fusing the inverse scale into the preceding op (LayerNorm, for example). No retraining needed.

## How low can you go

INT8 is generally safe. INT4 works with outlier-aware methods like AWQ. INT3 and below remain a research problem, with high variance across models and tasks. As a rule the accuracy cost is model-specific, so any deployment needs its own evaluation rather than a bit-width rule of thumb.

## Related notes

- [[ml/serving-systems/performance-modeling|Performance Modeling]]
- [[ml/serving-systems/memory-management|Memory Management]]
- [[ml/serving-systems/sparsity-and-pruning|Sparsity and Pruning]]
