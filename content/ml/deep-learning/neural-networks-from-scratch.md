---
title: Neural Networks from Scratch
category: Deep Learning
tags:
  - deep learning
  - neural networks
  - backpropagation
  - numpy
  - pytorch
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Neural networks from first principles, including affine layers, nonlinearities, cross-entropy, backpropagation derivations, and small implementations in NumPy and PyTorch.
sources:
  - title: Rumelhart, Hinton, and Williams (1986), Learning Representations by Back-Propagating Errors
    url: https://www.nature.com/articles/323533a0
    type: paper
  - title: He et al. (2015), Delving Deep into Rectifiers
    url: https://www.cv-foundation.org/openaccess/content_iccv_2015/papers/He_Delving_Deep_into_ICCV_2015_paper.pdf
    type: paper
  - title: Batch Normalization (2015)
    url: https://arxiv.org/abs/1502.03167
    type: paper
---

## Purpose

This note rebuilds the feedforward neural network from the scalar neuron upward. The key objects are simple:

- affine maps
- nonlinearities
- a scalar loss
- gradients passed backward with the chain rule

Once those are clear, most later architectures look like structured ways to choose the affine maps and parameter sharing.

## One Neuron

For input $x \in \mathbb{R}^{d_{in}}$, weights $W \in \mathbb{R}^{d_{out} \times d_{in}}$, and bias $b \in \mathbb{R}^{d_{out}}$, the affine map is

$$
z = Wx + b
$$

and a hidden layer applies a nonlinearity elementwise:

$$
a = \phi(z)
$$

If every layer were affine, the whole network would collapse into one affine map:

$$
W_2(W_1x + b_1) + b_2 = (W_2W_1)x + (W_2b_1 + b_2)
$$

That is why nonlinearity is not decorative. It is the thing that keeps depth from degenerating into one linear model.

## A Two-Layer Network

For classification with hidden width $h$ and $K$ classes:

$$
\begin{aligned}
z_1 &= W_1x + b_1 \\
a_1 &= \phi(z_1) \\
z_2 &= W_2a_1 + b_2 \\
\hat{y} &= \text{softmax}(z_2)
\end{aligned}
$$

The softmax is

$$
\hat{y}_k = \frac{\exp(z_{2,k})}{\sum_{j=1}^{K} \exp(z_{2,j})}
$$

and the cross-entropy loss for one-hot target $y$ is

$$
\mathcal{L} = -\sum_{k=1}^{K} y_k \log \hat{y}_k
$$

For one example whose correct class is $c$, this reduces to

$$
\mathcal{L} = -\log \hat{y}_c
$$

## Why the Softmax Gradient Is Nice

For softmax followed by cross-entropy, the output-layer gradient simplifies to

$$
\frac{\partial \mathcal{L}}{\partial z_2} = \hat{y} - y
$$

That is one of the most useful algebraic cancellations in deep learning.

The hidden-layer gradients then follow by the chain rule:

$$
\begin{aligned}
\frac{\partial \mathcal{L}}{\partial W_2} &= \left(\hat{y} - y\right)a_1^\top \\
\frac{\partial \mathcal{L}}{\partial b_2} &= \hat{y} - y \\
\frac{\partial \mathcal{L}}{\partial a_1} &= W_2^\top(\hat{y} - y) \\
\frac{\partial \mathcal{L}}{\partial z_1} &= \frac{\partial \mathcal{L}}{\partial a_1} \odot \phi'(z_1) \\
\frac{\partial \mathcal{L}}{\partial W_1} &= \frac{\partial \mathcal{L}}{\partial z_1}x^\top \\
\frac{\partial \mathcal{L}}{\partial b_1} &= \frac{\partial \mathcal{L}}{\partial z_1}
\end{aligned}
$$

For ReLU,

$$
\phi'(z) = \mathbf{1}[z > 0]
$$

so gradients flow only through active units.

## Mini-Batch Form

For a batch matrix $X \in \mathbb{R}^{B \times d_{in}}$:

$$
\begin{aligned}
Z_1 &= XW_1^\top + b_1 \\
A_1 &= \phi(Z_1) \\
Z_2 &= A_1W_2^\top + b_2 \\
\hat{Y} &= \text{softmax}(Z_2)
\end{aligned}
$$

The batch loss is usually the mean over rows.

## Initialization and Optimization

Bad initialization can destroy training before optimization has a chance. If the variance shrinks each layer, activations and gradients vanish. If it grows, they explode.

For ReLU networks, He initialization uses

$$
W_{ij} \sim \mathcal{N}\left(0, \frac{2}{d_{in}}\right)
$$

which keeps signal scale more stable through depth.

SGD updates parameters by

$$
\theta \leftarrow \theta - \eta \nabla_\theta \mathcal{L}
$$

and Adam keeps exponential moving averages of the first and second moments of the gradient.

## NumPy Implementation

This version does the forward pass, backpropagation, and SGD update explicitly.

```python
import numpy as np

def relu(x):
    return np.maximum(x, 0.0)

def relu_grad(x):
    return (x > 0).astype(x.dtype)

def softmax(logits):
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)

class MLP:
    def __init__(self, d_in, d_hidden, d_out, seed=0):
        rng = np.random.default_rng(seed)
        self.W1 = rng.normal(0.0, np.sqrt(2 / d_in), size=(d_hidden, d_in))
        self.b1 = np.zeros(d_hidden)
        self.W2 = rng.normal(0.0, np.sqrt(2 / d_hidden), size=(d_out, d_hidden))
        self.b2 = np.zeros(d_out)

    def forward(self, X):
        z1 = X @ self.W1.T + self.b1
        a1 = relu(z1)
        z2 = a1 @ self.W2.T + self.b2
        probs = softmax(z2)
        cache = (X, z1, a1, z2, probs)
        return probs, cache

    def loss_and_grads(self, X, y):
        probs, (X, z1, a1, z2, probs) = self.forward(X)
        B = X.shape[0]

        one_hot = np.zeros_like(probs)
        one_hot[np.arange(B), y] = 1.0
        loss = -np.log(probs[np.arange(B), y] + 1e-12).mean()

        dz2 = (probs - one_hot) / B
        dW2 = dz2.T @ a1
        db2 = dz2.sum(axis=0)

        da1 = dz2 @ self.W2
        dz1 = da1 * relu_grad(z1)
        dW1 = dz1.T @ X
        db1 = dz1.sum(axis=0)

        grads = {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}
        return loss, grads

    def step(self, grads, lr=1e-2):
        for name, grad in grads.items():
            setattr(self, name, getattr(self, name) - lr * grad)
```

## PyTorch Implementation

PyTorch will differentiate this automatically, though the math is the same.

```python
import torch
import torch.nn as nn

class TorchMLP(nn.Module):
    def __init__(self, d_in: int, d_hidden: int, d_out: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, d_hidden),
            nn.ReLU(),
            nn.Linear(d_hidden, d_out),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

model = TorchMLP(d_in=128, d_hidden=256, d_out=10)
logits = model(torch.randn(32, 128))
loss = nn.CrossEntropyLoss()(logits, torch.randint(0, 10, (32,)))
loss.backward()
```

## What Changes in Larger Models

The basic backpropagation story does not change. Larger architectures mostly change:

- which parameters are shared
- which inputs are local or global
- what inductive bias the affine map encodes
- what loss the model is trained against

CNNs constrain the affine map to local shared filters. RNNs reuse the same transition over time. Transformers let each position build a data-dependent affine mixture over other positions.

## Related Notes

- [[ml/deep-learning/modeling-architecture-and-data|Modeling, Architecture, and Data]]
- [[ml/deep-learning/recurrent-neural-networks|Recurrent Neural Networks]]
- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]

## Sources

- [Rumelhart, Hinton, and Williams (1986), Learning Representations by Back-Propagating Errors](https://www.nature.com/articles/323533a0)
- [He et al. (2015), Delving Deep into Rectifiers](https://www.cv-foundation.org/openaccess/content_iccv_2015/papers/He_Delving_Deep_into_ICCV_2015_paper.pdf)
- [Ioffe and Szegedy (2015), Batch Normalization](https://arxiv.org/abs/1502.03167)
