---
title: Modeling, Architecture, and Data
category: Deep Learning
tags:
  - deep learning
  - modeling
  - architecture
  - data
  - regularization
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: How to choose a model class, objective, data representation, and training setup, with emphasis on matching architectural bias to structure in the data.
sources:
  - title: Deep Residual Learning for Image Recognition
    url: https://arxiv.org/abs/1512.03385
    type: paper
  - title: Attention Is All You Need
    url: https://arxiv.org/abs/1706.03762
    type: paper
  - title: Batch Normalization
    url: https://arxiv.org/abs/1502.03167
    type: paper
  - title: Scaling Laws for Neural Language Models
    url: https://arxiv.org/abs/2001.08361
    type: paper
  - title: Dropout
    url: https://www.cs.toronto.edu/~rsalakhu/papers/srivastava14a.pdf
    type: paper
---

## Purpose

Before choosing a specific architecture, it helps to ask a harder question: what is the structure of the problem? This note is about those choices. The model is only one part of the design. The data representation, target, augmentation, normalization, and evaluation setup can dominate the outcome.

## Start from the Prediction Interface

Every supervised model needs the same declarations:

- input space $x$
- output space $y$
- loss $\mathcal{L}(\hat{y}, y)$
- deployment constraints

The first question is not "CNN or transformer?" It is "what is the prediction object?"

Examples:

- class label
- token sequence
- dense image
- scalar score
- graph-level property

The output type should determine the head and the loss. Classification wants cross-entropy. Regression often wants mean squared error or a distributional loss. Autoregressive generation wants next-token log likelihood.

## Match the Inductive Bias to the Data

Architectures are guesses about structure.

| Data structure | Common inductive bias | Typical architecture |
| --- | --- | --- |
| fixed-width vectors | dense interactions | MLP |
| spatial locality | local receptive fields, translation equivariance | CNN |
| temporal dependence | state carried through time | RNN / LSTM / GRU |
| long-range token interactions | content-based routing | Transformer |
| graph neighborhoods | message passing over edges | GNN |

The point is not that one family is universally better. The point is that parameter sharing and connectivity should follow the problem when possible.

## Architecture Choices That Matter

### Depth Versus Width

Depth composes features. Width increases the number of features learned at one stage. Within a reasonable range, both matter less than a bad inductive bias or bad data. Scaling-law results are useful here: performance often follows broad power-law trends with parameter count, data, and compute, while many smaller architectural tweaks matter only at second order.

### Residual Connections

Residual blocks learn

$$
y = x + F(x)
$$

instead of asking a stack to learn $H(x)$ directly. This changes optimization a lot because the identity path keeps signal and gradients moving even when $F$ is small early in training.

### Normalization

BatchNorm, LayerNorm, and RMSNorm all stabilize training in slightly different ways. The broad effect is that they make scale less fragile.

### Regularization

Dropout, weight decay, augmentation, label smoothing, and early stopping all change generalization in different ways. If the training loss looks great and the validation loss drifts upward, architecture is rarely the first suspect.

## Data Choices Are Model Choices

A model only sees the world through the tensors you hand it.

Important choices include:

- tokenization or feature extraction
- target construction
- negative sampling
- train/validation split
- augmentation
- deduplication
- balancing or reweighting

For many modern systems, especially in language and recommendation, the boundary between data design and model design is blurry. A weak target can waste a strong architecture.

## A Practical Design Loop

I usually want to answer these in order:

1. What is the downstream decision that consumes the model?
2. What invariances or symmetries does the problem have?
3. What is expensive at training time and at serving time?
4. Which errors are acceptable and which are not?
5. What data is abundant, and what data is noisy or biased?

That often narrows the architecture quickly.

## Example: Image Classification

- data has local spatial structure
- translation matters more than absolute position
- parameter sharing is valuable

That points toward CNNs or vision transformers rather than a plain MLP over flattened pixels.

## Example: Autoregressive Text

- output is a sequence
- future tokens must be hidden at training and inference
- long-range context matters
- training should be parallel over positions if possible

That points toward a decoder-only transformer rather than a vanilla RNN.

## Example: Low-Data Scientific Prediction

If labeled data is scarce and structure is known, a smaller architecture with a stronger inductive bias is often better than a fashionable large one. The main failure mode in these settings is variance, not lack of expressivity.

## A Small PyTorch Design Skeleton

This is not a full training loop. It is the interface I want to make explicit before getting fancy.

```python
from dataclasses import dataclass
import torch
import torch.nn as nn

@dataclass
class Spec:
    input_dim: int
    output_dim: int
    task: str  # "classification", "regression", "autoregressive"

def make_head(spec: Spec) -> nn.Module:
    if spec.task == "classification":
        return nn.Linear(spec.input_dim, spec.output_dim)
    if spec.task == "regression":
        return nn.Linear(spec.input_dim, spec.output_dim)
    if spec.task == "autoregressive":
        return nn.Linear(spec.input_dim, spec.output_dim, bias=False)
    raise ValueError(f"unknown task: {spec.task}")

def make_loss(spec: Spec):
    if spec.task == "classification":
        return nn.CrossEntropyLoss()
    if spec.task == "regression":
        return nn.MSELoss()
    if spec.task == "autoregressive":
        return nn.CrossEntropyLoss()
    raise ValueError(f"unknown task: {spec.task}")
```

The interesting part is not the code. It is the discipline of deciding the contract before touching the model body.

## Failure Modes

- model too expressive for the data, so it memorizes
- model too rigid for the task, so bias dominates
- loss mismatched to the real objective
- input pipeline leaks future information
- evaluation split does not reflect deployment
- compute budget spent on depth or width when data quality is the real bottleneck

## Related Notes

- [[ml/deep-learning/neural-networks-from-scratch|Neural Networks from Scratch]]
- [[ml/deep-learning/convolutional-neural-networks|Convolutional Neural Networks]]
- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]

## Sources

- [He et al. (2015), Deep Residual Learning for Image Recognition](https://arxiv.org/abs/1512.03385)
- [Vaswani et al. (2017), Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Ioffe and Szegedy (2015), Batch Normalization](https://arxiv.org/abs/1502.03167)
- [Kaplan et al. (2020), Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361)
- [Srivastava et al. (2014), Dropout](https://www.cs.toronto.edu/~rsalakhu/papers/srivastava14a.pdf)
