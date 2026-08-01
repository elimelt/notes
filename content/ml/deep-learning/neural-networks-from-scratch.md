---
title: Neural Networks from Scratch
aliases:
  - /ml/deep-learning/mlp-from-scratch-on-mnist
  - /deep-learning/mlp-from-scratch-on-mnist
  - /ml/deep-learning/checking-manual-gradients-against-autodiff-on-mnist
  - /deep-learning/checking-manual-gradients-against-autodiff-on-mnist
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
description: Neural networks from first principles, including backpropagation derivations, initialization, normalization, regularization, and small implementations in NumPy and PyTorch.
sources:
  - title: Rumelhart, Hinton, and Williams (1986), Learning Representations by Back-Propagating Errors
    url: https://www.nature.com/articles/323533a0
    type: paper
  - title: He et al. (2015), Delving Deep into Rectifiers
    url: https://www.cv-foundation.org/openaccess/content_iccv_2015/papers/He_Delving_Deep_into_ICCV_2015_paper.pdf
    type: paper
  - title: Ioffe and Szegedy (2015), Batch Normalization
    url: https://arxiv.org/abs/1502.03167
    type: paper
  - title: Srivastava et al. (2014), Dropout
    url: https://www.cs.toronto.edu/~rsalakhu/papers/srivastava14a.pdf
    type: paper
---

## Purpose

This note is the foundation under the rest of the deep-learning section. The goal is to make the standard neural-network training loop feel mechanical rather than mysterious:

- define a computation
- define a scalar loss
- differentiate it with the chain rule
- update parameters

Rumelhart, Hinton, and Williams made the key move in 1986. Once the network is a composition of differentiable operations, the gradient can be pushed backward one local Jacobian at a time.

## One Affine Layer

For input $x \in \mathbb{R}^{d_{in}}$, weights $W \in \mathbb{R}^{d_{out} \times d_{in}}$, and bias $b \in \mathbb{R}^{d_{out}}$:

$$
z = Wx + b
$$

This is just an affine map. If a network were only a stack of affine maps, the whole composition would still be affine:

$$
W_2(W_1x + b_1) + b_2 = (W_2W_1)x + (W_2b_1 + b_2)
$$

That is why hidden-layer nonlinearities are necessary. They prevent depth from collapsing into one linear classifier.

## A Two-Layer Classifier

For hidden width $h$ and $K$ classes:

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
\hat{y}_k = \frac{e^{z_{2,k}}}{\sum_{j=1}^{K} e^{z_{2,j}}}
$$

and for one-hot target $y$ the cross-entropy loss is

$$
\mathcal{L}(\hat{y}, y) = -\sum_{k=1}^{K} y_k \log \hat{y}_k
$$

If the correct class is $c$, this reduces to

$$
\mathcal{L} = -\log \hat{y}_c
$$

## Backpropagation Derivation

The output-layer derivative is the standard identity:

$$
\frac{\partial \mathcal{L}}{\partial z_2} = \hat{y} - y
$$

This falls out of differentiating the softmax and cross-entropy together. The rest is the chain rule.

### Output Layer

Because $z_2 = W_2a_1 + b_2$:

$$
\frac{\partial \mathcal{L}}{\partial W_2}
=
\frac{\partial \mathcal{L}}{\partial z_2}
\frac{\partial z_2}{\partial W_2}
=
(\hat{y} - y)a_1^\top
$$

and

$$
\frac{\partial \mathcal{L}}{\partial b_2} = \hat{y} - y
$$

The hidden activation receives

$$
\frac{\partial \mathcal{L}}{\partial a_1}
=
W_2^\top(\hat{y} - y)
$$

### Hidden Layer

Since $a_1 = \phi(z_1)$:

$$
\frac{\partial \mathcal{L}}{\partial z_1}
=
\frac{\partial \mathcal{L}}{\partial a_1} \odot \phi'(z_1)
$$

For ReLU,

$$
\phi(z) = \max(0, z),
\qquad
\phi'(z) = \mathbf{1}[z > 0]
$$

so only active hidden units pass gradient.

Now

$$
\frac{\partial \mathcal{L}}{\partial W_1}
=
\frac{\partial \mathcal{L}}{\partial z_1}x^\top,
\qquad
\frac{\partial \mathcal{L}}{\partial b_1}
=
\frac{\partial \mathcal{L}}{\partial z_1}
$$

This is the whole backpropagation pattern in miniature. Every later architecture is the same story, only with more structured Jacobians.

## Batch Form

For batch matrix $X \in \mathbb{R}^{B \times d_{in}}$:

$$
\begin{aligned}
Z_1 &= XW_1^\top + b_1 \\
A_1 &= \phi(Z_1) \\
Z_2 &= A_1W_2^\top + b_2 \\
\hat{Y} &= \text{softmax}(Z_2)
\end{aligned}
$$

In practice the loss is averaged over the batch.

## Why Initialization Matters

Very deep networks fail easily if activations or gradients change scale too aggressively across layers.

He et al. derive an initialization for rectifier networks that keeps the forward variance roughly stable:

$$
\operatorname{Var}[W_{ij}] = \frac{2}{n_{in}}
$$

so one common choice is

$$
W_{ij} \sim \mathcal{N}\left(0, \frac{2}{n_{in}}\right)
$$

That is the standard He initialization. The factor of $2$ appears because ReLU zeroes about half the mass.

The same paper also proposes PReLU:

$$
f(y_i) =
\begin{cases}
y_i & y_i > 0 \\
a_i y_i & y_i \le 0
\end{cases}
$$

with learned negative slope $a_i$. The paper reports **4.94%** top-5 test error on ImageNet 2012, a **26% relative improvement** over GoogLeNet's **6.66%**.

## Batch Normalization

Ioffe and Szegedy normalize each activation dimension over the current mini-batch:

$$
\hat{x}^{(k)} = \frac{x^{(k)} - \mathbb{E}_{\mathcal{B}}[x^{(k)}]}
{\sqrt{\operatorname{Var}_{\mathcal{B}}[x^{(k)}] + \epsilon}}
$$

then restore learnable scale and shift:

$$
y^{(k)} = \gamma^{(k)} \hat{x}^{(k)} + \beta^{(k)}
$$

The point is not to clamp everything permanently to zero mean and unit variance. The point is to stabilize optimization while still letting the model learn whatever affine reparameterization it needs.

The BatchNorm paper reports the same accuracy in **14 times fewer training steps** on a strong ImageNet model, and an ensemble reaching **4.9%** top-5 validation error.

## Dropout

Dropout randomly removes units during training. If $m$ is a Bernoulli mask:

$$
\tilde{h} = m \odot h
$$

The paper's framing is useful. Training samples an exponential family of "thinned" subnetworks, and test-time inference approximates their average with one full network.

Srivastava et al. describe dropout as a way to prevent units from **co-adapting too much**. In several experiments they found dropping **20% of input units** and **50% of hidden units** worked well.

## NumPy Implementation

This version does the forward pass, gradient calculation, and SGD update explicitly.

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
        cache = (X, z1, a1, probs)
        return probs, cache

    def loss_and_grads(self, X, y):
        probs, (X, z1, a1, probs) = self.forward(X)
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
        self.W1 -= lr * grads["W1"]
        self.b1 -= lr * grads["b1"]
        self.W2 -= lr * grads["W2"]
        self.b2 -= lr * grads["b2"]
```

## PyTorch Implementation

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

model = TorchMLP(128, 256, 10)
logits = model(torch.randn(32, 128))
loss = nn.CrossEntropyLoss()(logits, torch.randint(0, 10, (32,)))
loss.backward()
```

This is shorter because autograd is doing exactly the backpropagation derivation from above.

## Executable Experiments

The first notebook trains the NumPy model on MNIST and exposes the loss curve, predictions, and failure cases discussed above.

[Run the MLP-from-scratch experiment](/ml/deep-learning/mlp-from-scratch-on-mnist.ipynb)

The second isolates softmax regression so the symbolic gradient, finite differences, and PyTorch autograd can be compared on the same real minibatch.

[Check manual gradients against autodiff](/ml/deep-learning/checking-manual-gradients-against-autodiff-on-mnist.ipynb)

## What to Carry Forward

- Backpropagation is just repeated local application of the chain rule.
- Initialization is part of the model, not a clerical detail.
- Normalization layers often change optimization more than small architecture tweaks do.
- Dropout is an ensemble-style regularizer implemented inside one training loop.

## Related Notes

- [[ml/deep-learning/modeling-architecture-and-data|Modeling, Architecture, and Data]]
- [[ml/deep-learning/convolutional-neural-networks|Convolutional Neural Networks]]
- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
- [[ml/deep-learning/recurrent-neural-networks|Recurrent Neural Networks]]

## Sources

- [Rumelhart, Hinton, and Williams (1986), Learning Representations by Back-Propagating Errors](https://www.nature.com/articles/323533a0)
- [He et al. (2015), Delving Deep into Rectifiers](https://www.cv-foundation.org/openaccess/content_iccv_2015/papers/He_Delving_Deep_into_ICCV_2015_paper.pdf)
- [Ioffe and Szegedy (2015), Batch Normalization](https://arxiv.org/abs/1502.03167)
- [Srivastava et al. (2014), Dropout](https://www.cs.toronto.edu/~rsalakhu/papers/srivastava14a.pdf)
