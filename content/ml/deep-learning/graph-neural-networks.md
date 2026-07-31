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
description: Graph neural networks from message passing upward, including graph convolution, neighborhood aggregation, oversmoothing, and small implementations in NumPy and PyTorch.
sources:
  - title: Semi-Supervised Classification with Graph Convolutional Networks
    url: https://arxiv.org/abs/1609.02907
    type: paper
  - title: Graph Attention Networks
    url: https://arxiv.org/abs/1710.10903
    type: paper
---

## Purpose

Graphs break the assumptions behind sequences and grids. There is no fixed left-to-right order, and neighborhoods have variable size. GNNs handle this by learning over edges and aggregating local neighborhoods.

## Message Passing View

A generic message-passing layer updates node $i$ by collecting messages from its neighbors:

$$
h_i^{(\ell + 1)} = \text{UPDATE}^{(\ell)}
\left(
h_i^{(\ell)},
\text{AGG}^{(\ell)}\left(\{ \text{MSG}^{(\ell)}(h_i^{(\ell)}, h_j^{(\ell)}, e_{ij}) : j \in \mathcal{N}(i)\}\right)
\right)
$$

That looks abstract because it is abstract. Most named GNN layers are concrete choices for `MSG`, `AGG`, and `UPDATE`.

## GCN Layer

The classic graph convolutional network uses normalized adjacency:

$$
H^{(\ell+1)} = \sigma\left(\hat{D}^{-1/2}\hat{A}\hat{D}^{-1/2}H^{(\ell)}W^{(\ell)}\right)
$$

where:

- $\hat{A} = A + I$ adds self-loops
- $\hat{D}_{ii} = \sum_j \hat{A}_{ij}$

This means: average a node with its neighbors, then apply a learned linear map.

## Why Normalization Matters

Without degree normalization, high-degree nodes dominate the aggregation. The symmetric normalization rescales messages so the layer does not explode or collapse just because some nodes have many neighbors.

## Oversmoothing

Repeated neighborhood averaging can make node representations too similar. That is the oversmoothing problem. It is one reason very deep plain GCN stacks often underperform shallower ones unless residual paths or other changes are added.

## NumPy GCN Layer

```python
import numpy as np

def gcn_layer(A, H, W):
    # A: (N, N), H: (N, Din), W: (Din, Dout)
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

## GATs

Graph attention networks replace fixed normalized averaging with learned neighbor weights. Instead of treating all neighbors equally after normalization, they learn an attention score over edges.

That makes the aggregation more flexible, though also more expensive.

## Where GNNs Fit

GNNs are natural when:

- the graph itself is the object
- relational structure matters more than an arbitrary serialization
- neighborhoods are informative and not too noisy

They are less attractive when the graph is weakly informative or when the task can be solved more cleanly by another structure.

## Related Notes

- [[ml/deep-learning/modeling-architecture-and-data|Modeling, Architecture, and Data]]
- [[ml/recommender-systems/sequential-recommendation|Sequential and Graph Recommenders]]

## Sources

- [Kipf and Welling (2016), Semi-Supervised Classification with Graph Convolutional Networks](https://arxiv.org/abs/1609.02907)
- [Velickovic et al. (2017), Graph Attention Networks](https://arxiv.org/abs/1710.10903)
