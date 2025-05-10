---
title: Scaling with the Roofline Model
category: Machine Learning Systems
tags: roofline, performance, optimization, gpu, bandwidth, compute
description: How do you characterize performance and bottlenecks when balancing compute and memory bandwidth? How can you quantify the intensity of a workload, and how well an algorithm can utilize resources? What are the scaling challenges of deploying large models for inference?
---

# Scaling with the Roofline Model

> *"When we run algorithms on hardware, we're bounded by three things: how fast it can do math (OPs/second), the bandwidth available for moving data around (bytes/second), and the total memory available to store data (bytes). These “roofline” constraints let us upper and lower bound the time of a given computation." - [How to Scale Your Model - All About Rooflines](https://jax-ml.github.io/scaling-book/roofline/)*

---

## Arithmetic Intensity

> Definition: the arithmetic intensity of an algorithm is given by the ratio of the total FLOPs it performs to the number of bytes it needs to communicate — either within a chip or between chips.

$$
\text{Arithmetic Intensity} = \frac{\text{Computation FLOPs}}{\text{Communication Bytes}}
$$

At a high level, we want to push our models to be as compute-bound as possible, meaning that the arithmetic intensity's demand matches the hardware's supply. This drives utilization up, as opposed to when our model is memory-bound, meaning we have unmatched supply and therefore underutilized hardware.

### Example: Dot-Product

$$
\text{Dot Product} = \sum_{i=1}^{n} a_i b_i
$$

For two vectors $a, b \in \mathbb{R}^n$, we need to load $2n$ elements, write one element, and perform $n$ multiplications and $n-1$ additions (FLOPs). Assuming our datatype is 2 bytes (e.g., float16), we have:

$$
\text{Intensity (dot product)} = \frac{\text{FLOPs}}{\text{Bytes}} = \frac{2n + 1}{2n + 2n + 2} = \frac{2n + 1}{4n + 2}
$$

Then, as $n \to \infty$, we have $\text{Intensity} \to \frac{1}{2}$.

This is *bad*. Modern accelerators can achieve much higher intensity, e.g. NVIDIA H100 ~315 FLOPS/B. The dot-product is thus a memory-bound operation, meaning GPUs will spend most of their time waiting for data to be loaded from memory.

## Roofline Model

![plot](assets/roofline.png)