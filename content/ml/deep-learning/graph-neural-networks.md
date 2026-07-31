---
title: Graph Neural Networks
category: Deep Learning
tags:
  - deep learning
  - graph neural networks
  - gnn
  - message passing
  - gcn
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Graph neural networks from message passing upward, with special focus on GCN and GAT, their update equations, and the assumptions they make about graph neighborhoods.
sources:
  - title: Kipf and Welling (2016), Semi-Supervised Classification with Graph Convolutional Networks
    url: https://arxiv.org/abs/1609.02907
    type: paper
  - title: Velickovic et al. (2017), Graph Attention Networks
    url: https://arxiv.org/abs/1710.10903
    type: paper
---

## Purpose

Graphs break the assumptions behind both sequences and images. There is no fixed left-to-right order and no regular lattice. GNNs solve this by learning over neighborhoods.

## Message Passing View

A generic message-passing layer updates node $i$ by aggregating over its neighbors:

$$
h_i^{(\ell+1)}
=
\operatorname{UPDATE}^{(\ell)}
\left(
h_i^{(\ell)},
\operatorname{AGG}^{(\ell)}
\left(
\{
\operatorname{MSG}^{(\ell)}(h_i^{(\ell)}, h_j^{(\ell)}, e_{ij})
:
j \in \mathcal{N}(i)
\}
\right)
\right)
$$

Most named GNN architectures are concrete instantiations of `MSG`, `AGG`, and `UPDATE`.

## GCN from Spectral Approximation

Kipf and Welling motivate GCN as a localized first-order approximation to spectral graph convolutions. The resulting propagation rule is:

$$
H^{(\ell+1)}
=
\sigma\left(
\tilde{D}^{-1/2}\tilde{A}\tilde{D}^{-1/2}
H^{(\ell)}W^{(\ell)}
\right)
$$

where

$$
\tilde{A} = A + I
$$

adds self-loops and

$$
\tilde{D}_{ii} = \sum_j \tilde{A}_{ij}
$$

is the corresponding degree matrix.

The paper explicitly introduces this as a **renormalization trick** to avoid numerical instability and exploding/vanishing gradients in deeper stacks.

## What the GCN Layer Is Doing

The GCN update can be read in three steps:

1. add each node to its own neighborhood
2. average or normalize neighbor information
3. apply a learned linear map

This makes GCN very simple, though the simplicity comes with a bias: all neighbors are treated symmetrically after normalization.

## Datasets and Setting

The paper evaluates on citation-network benchmarks:

- **Cora**
- **Citeseer**
- **Pubmed**

and also on NELL. The problem is semi-supervised node classification with few labels.

This framing matters because it is one reason GCN became popular so quickly. The update rule is short, scalable, and effective on a benchmark family many people cared about.

## GAT

Velickovic et al. replace fixed normalized averaging with learned attention over neighborhoods.

First compute unnormalized attention score

$$
e_{ij}
=
\operatorname{LeakyReLU}
\left(
\vec{a}^{\,T}
[W\vec{h}_i \,\|\, W\vec{h}_j]
\right)
$$

then normalize over the neighborhood:

$$
\alpha_{ij}
=
\operatorname{softmax}_j(e_{ij})
=
\frac{\exp(e_{ij})}{\sum_{k \in \mathcal{N}_i}\exp(e_{ik})}
$$

and update:

$$
\vec{h}'_i
=
\sigma\left(
\sum_{j \in \mathcal{N}_i}
\alpha_{ij}W\vec{h}_j
\right)
$$

The paper uses **LeakyReLU** with negative slope **0.2** inside the attention mechanism.

## Multi-Head Attention on Graphs

Like transformers, GAT stabilizes learning with multi-head attention. The paper says explicitly that extending the mechanism to **multi-head attention** was beneficial.

This allows either:

- concatenation of head outputs in hidden layers
- averaging of head outputs at the final layer

depending on the stage of the network.

## Why GAT Was Interesting

GAT addresses a limitation of GCN. In GCN, every neighbor contributes through the same normalized operator. In GAT, the model can assign different weights to different neighbors without expensive global matrix operations or requiring a fixed spectral basis.

The paper evaluates on:

- **Cora**
- **Citeseer**
- **Pubmed**
- **PPI**

The PPI result matters because it shows the method in an inductive setting where test graphs are unseen during training.

## NumPy GCN Layer

```python
import numpy as np

def gcn_layer(A, H, W):
    A_hat = A + np.eye(A.shape[0], dtype=A.dtype)
    D_hat = np.diag(np.sum(A_hat, axis=1))
    D_inv_sqrt = np.linalg.inv(np.sqrt(D_hat))
    A_norm = D_inv_sqrt @ A_hat @ D_inv_sqrt
    return np.maximum(0.0, A_norm @ H @ W)
```

## PyTorch GCN Module

```python
import torch
import torch.nn as nn

class GCNLayer(nn.Module):
    def __init__(self, d_in: int, d_out: int):
        super().__init__()
        self.proj = nn.Linear(d_in, d_out, bias=False)

    def forward(self, A: torch.Tensor, H: torch.Tensor) -> torch.Tensor:
        A_hat = A + torch.eye(A.size(0), device=A.device, dtype=A.dtype)
        D = A_hat.sum(dim=1)
        D_inv_sqrt = torch.diag(torch.rsqrt(D))
        A_norm = D_inv_sqrt @ A_hat @ D_inv_sqrt
        return torch.relu(A_norm @ self.proj(H))
```

## What to Watch For

GNNs often run into:

- oversmoothing
- oversquashing
- noisy neighborhoods
- weak or missing node features

The papers here do not solve all of that. They just establish two key design points:

- fixed normalized neighborhood mixing
- learned attention-weighted neighborhood mixing

## Related Notes

- [[ml/deep-learning/modeling-architecture-and-data|Modeling, Architecture, and Data]]
- [[ml/recommender-systems/sequential-recommendation|Sequential and Graph Recommenders]]

## Sources

- [Kipf and Welling (2016), Semi-Supervised Classification with Graph Convolutional Networks](https://arxiv.org/abs/1609.02907)
- [Velickovic et al. (2017), Graph Attention Networks](https://arxiv.org/abs/1710.10903)
