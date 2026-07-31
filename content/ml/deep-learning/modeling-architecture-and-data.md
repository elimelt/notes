---
title: Modeling, Architecture, and Data
category: Deep Learning
tags:
  - deep learning
  - modeling
  - architecture
  - data representation
  - regularization
  - attention
  - resnet
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: How to choose a model class, objective, data representation, and training setup, with emphasis on inductive bias, optimization stability, and compute-data tradeoffs.
sources:
  - title: Deep Residual Learning for Image Recognition
    url: https://arxiv.org/abs/1512.03385
    type: paper
  - title: Attention Is All You Need
    url: https://arxiv.org/abs/1706.03762
    type: paper
  - title: Ioffe and Szegedy (2015), Batch Normalization
    url: https://arxiv.org/abs/1502.03167
    type: paper
  - title: Kaplan et al. (2020), Scaling Laws for Neural Language Models
    url: https://arxiv.org/abs/2001.08361
    type: paper
  - title: Srivastava et al. (2014), Dropout
    url: https://www.cs.toronto.edu/~rsalakhu/papers/srivastava14a.pdf
    type: paper
---

## Purpose

Choosing an architecture is usually not the first hard decision. The first hard decision is deciding what the model is supposed to predict, what structure the data has, and what resource is actually scarce. This note is about that layer of design.

## Start from the Interface

A supervised learning problem is not defined by its model class. It is defined by:

- input space $x$
- output space $y$
- loss $\mathcal{L}(\hat{y}, y)$
- deployment constraints

Examples:

- token sequence to next token
- image to class label
- image to dense segmentation mask
- graph to node labels
- feature vector to scalar score

The head and the loss should follow from that interface. Classification wants cross-entropy. Regression wants a real-valued loss. Autoregressive generation wants a factorized log-likelihood.

## Architecture Is an Inductive Bias

Different architectures encode different assumptions.

| Data structure | Bias | Typical architecture |
| --- | --- | --- |
| tabular or fixed vectors | dense interactions | MLP |
| 2D grids | locality and translation equivariance | CNN |
| ordered sequences | state evolution through time | RNN / LSTM / GRU |
| long-range relational sequences | content-based routing | Transformer |
| irregular graphs | neighborhood message passing | GNN |

The architecture is a guess about which symmetries matter. A good guess saves parameters and data. A bad guess makes optimization work harder for no gain.

## The Bias-Variance Question Shows Up as Architecture

A high-capacity model can fit strange functions. That is not the same thing as learning the right one under finite data and finite compute.

If structure is known, it is often wise to encode it:

- local convolutions instead of a fully connected image classifier
- causal masking instead of unconstrained sequence attention
- message passing instead of flattening a graph into arbitrary order

This is one of the few genuinely transferable design heuristics in deep learning.

## Optimization Choices Are Architectural Choices

Several famous papers are often described as "training tricks." They are better understood as changes to the effective architecture.

### Residual Connections

ResNet reframes a block as

$$
y = x + F(x)
$$

instead of asking the block to learn $H(x)$ directly. The paper's motivation is the **degradation problem**: deeper plain nets can have higher training error than shallower ones even though a deeper model contains the shallower solution as a special case via identity layers.

Residual connections matter because they preserve an easy signal path. The identity path carries both activations and gradients.

### Normalization

BatchNorm inserts

$$
\hat{x}^{(k)} = \frac{x^{(k)} - \mu_\mathcal{B}^{(k)}}{\sqrt{(\sigma_\mathcal{B}^{(k)})^2 + \epsilon}},
\qquad
y^{(k)} = \gamma^{(k)} \hat{x}^{(k)} + \beta^{(k)}
$$

into the network. This changes what parameter scales are easy to optimize. In practice it often permits larger learning rates and makes initialization less fragile.

### Regularization

Dropout changes the training distribution itself. Instead of one deterministic hidden layer, training samples many subnetworks. Weight decay changes which solutions are cheap. Data augmentation changes which invariances are rewarded.

These are not afterthoughts. They often dominate the outcome when the architecture is already reasonable.

## Data Choices Are Model Choices

A model only sees the world through the tensors you provide. Important choices include:

- tokenization
- feature extraction
- target construction
- balancing or reweighting
- negative sampling
- train/validation split
- augmentation
- deduplication

For sequence models this can change the task completely. Bahdanau attention was motivated by the failure of fixed-length sentence encodings. GPT-style language modeling depends heavily on tokenization and context length. Recommender training depends heavily on how negatives are sampled.

## Compute, Data, and Scale

Kaplan et al. study how language-model loss changes with model size, dataset size, and compute. The main conclusion is that loss follows broad **power-law** trends over a large range, while width-versus-depth choices matter relatively little inside a reasonable regime.

Two consequences from that paper are worth remembering:

- larger models are more sample-efficient
- compute-optimal training may involve stopping before full convergence

The paper explicitly says that optimally compute-efficient training means training **very large models on a relatively modest amount of data and stopping significantly before convergence**.

That is useful because it changes how to reason about "the best architecture." Once the architecture family is competent, data quality and compute allocation may matter more than small structural edits.

## A Practical Decision Order

When starting a model, I want answers to these:

1. What downstream decision consumes the model output?
2. Which invariances or constraints should the model obey?
3. Is training compute scarce, inference latency scarce, or labeled data scarce?
4. What kinds of errors are expensive?
5. What part of the data pipeline is policy-shaped, biased, or weakly labeled?

That usually narrows the design space quickly.

## Example: Translation

A translation model has:

- one fully observed source sequence
- one generated target sequence
- alignment between them

That points naturally toward an encoder-decoder architecture with cross-attention. The original transformer is exactly that design.

## Example: Long-Context Language Modeling

A language model needs:

- causal dependence
- parallel training over positions
- long-range interaction

That points toward a decoder-only transformer rather than a vanilla RNN.

## Example: Small Scientific Dataset

If data is scarce and structure is known, a smaller model with a stronger prior is often better than a huge flexible one. In that regime, the main failure mode is variance.

## Minimal PyTorch Spec

```python
from dataclasses import dataclass
import torch.nn as nn

@dataclass
class Spec:
    input_dim: int
    output_dim: int
    task: str

def make_head(spec: Spec) -> nn.Module:
    if spec.task == "classification":
        return nn.Linear(spec.input_dim, spec.output_dim)
    if spec.task == "regression":
        return nn.Linear(spec.input_dim, spec.output_dim)
    if spec.task == "autoregressive":
        return nn.Linear(spec.input_dim, spec.output_dim, bias=False)
    raise ValueError(spec.task)
```

This is simple on purpose. Good modeling work starts by pinning down the interface before indulging architecture taste.

## Failure Modes

- loss mismatched to the downstream objective
- architecture blind to known structure
- evaluation split not representative of deployment
- target leakage in preprocessing
- over-investing in parameter count when the bottleneck is noisy or biased data
- over-investing in architectural novelty when the bottleneck is compute or token budget

## Related Notes

- [[ml/deep-learning/neural-networks-from-scratch|Neural Networks from Scratch]]
- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
- [[ml/deep-learning/convolutional-neural-networks|Convolutional Neural Networks]]

## Sources

- [He et al. (2015), Deep Residual Learning for Image Recognition](https://arxiv.org/abs/1512.03385)
- [Vaswani et al. (2017), Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Ioffe and Szegedy (2015), Batch Normalization](https://arxiv.org/abs/1502.03167)
- [Kaplan et al. (2020), Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361)
- [Srivastava et al. (2014), Dropout](https://www.cs.toronto.edu/~rsalakhu/papers/srivastava14a.pdf)
