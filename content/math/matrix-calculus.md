---
title: Matrix Calculus for Machine Learning
category: Mathematics
tags:
  - matrix calculus
  - gradients
  - jacobians
  - hessians
  - optimization
  - backpropagation
date: 2026-08-01
status: draft
description: Reference for gradients, Jacobians, and the matrix-calculus identities behind backpropagation, with derivations for affine layers, quadratic forms, least squares, and softmax cross-entropy, verified against PyTorch autograd.
sources:
  - title: Parr and Howard, The Matrix Calculus You Need For Deep Learning
    url: https://explained.ai/matrix-calculus/index.html
    type: paper
  - title: Cardal, Matrix Calculus notes (UW)
    url: https://atmos.washington.edu/~dennis/MatrixCalculus.pdf
    type: lecture
  - title: Petersen and Pedersen, The Matrix Cookbook
    url: https://www.math.uwaterloo.ca/~hwolkowi/matrixcookbook.pdf
    type: book
  - title: Baydin et al. (2018), Automatic Differentiation in Machine Learning - a Survey
    url: https://arxiv.org/abs/1502.05767
    type: paper
---

## Purpose

A reusable derivation note for the handful of matrix-calculus facts that carry nearly all of deep learning: layout conventions, the core identities, the four gradients that appear in every training loop (affine, quadratic, least squares, softmax cross-entropy), and the JVP/VJP framing that autodiff systems actually implement. [[ml/deep-learning/neural-networks-from-scratch|Neural Networks from Scratch]] and [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]] use these identities implicitly; this is where they are derived.

## Notation and layout

Vectors are columns. For $f: \mathbb{R}^n \to \mathbb{R}^m$ the Jacobian follows numerator layout, the convention in [Parr and Howard](https://explained.ai/matrix-calculus/index.html):

$$
J = \frac{\partial f}{\partial x} \in \mathbb{R}^{m \times n}, \qquad J_{ij} = \frac{\partial f_i}{\partial x_j}.
$$

Row $i$ is the transposed gradient of output $f_i$. For a scalar loss $L: \mathbb{R}^n \to \mathbb{R}$, the Jacobian is a row vector, and the gradient $\nabla L \in \mathbb{R}^n$ is its transpose, a column the same shape as $x$. The shape-matching rule does most of the error catching: a gradient always has the shape of the thing you differentiate with respect to, so $\partial L/\partial W$ has the shape of $W$. The Hessian $\nabla^2 L \in \mathbb{R}^{n \times n}$ is the Jacobian of the gradient, symmetric when $L$ is twice continuously differentiable.

> [!warning] Layout conventions differ by a transpose
> There are two incompatible conventions in the literature. Numerator layout (used here and in Parr and Howard) makes $\partial(Ax)/\partial x = A$; denominator layout (common in statistics texts and parts of the Matrix Cookbook) makes it $A^T$, transposing every identity. Mixing sources without checking their convention is the classic way to end up with a chain rule that multiplies in the wrong order or a gradient that is secretly a row vector. Two defenses: fix one convention per derivation, and lean on the shape rule, $\partial L/\partial W$ must have the shape of $W$, since a shape mismatch exposes a convention mix-up immediately.

## Core identities

Each identity below can be checked by writing out components; sources are [Parr and Howard](https://explained.ai/matrix-calculus/index.html), the [UW matrix calculus notes](https://atmos.washington.edu/~dennis/MatrixCalculus.pdf), and the [Matrix Cookbook](https://www.math.uwaterloo.ca/~hwolkowi/matrixcookbook.pdf).

| Expression | Derivative | Notes |
|---|---|---|
| $a^T x$ | $\partial/\partial x = a^T$, gradient $a$ | linear form |
| $Ax$ | $\partial/\partial x = A$ | Jacobian of a linear map is the matrix |
| $x^T A x$ | gradient $(A + A^T)\,x$ | $2Ax$ when $A$ symmetric |
| $a^T X b$ | $\partial/\partial X = a b^T$ | rank-one gradient |
| $\mathrm{tr}(AX)$ | $\partial/\partial X = A^T$ | trace trick |
| $\log \det X$ | $\partial/\partial X = X^{-T}$ | $X$ invertible; Gaussian log-likelihoods |
| $u(x) \odot v(x)$ | $J = \mathrm{diag}(v)\,J_u + \mathrm{diag}(u)\,J_v$ | elementwise product |
| elementwise $\phi(x)$ | $J = \mathrm{diag}(\phi'(x))$ | activations: ReLU, tanh, sigmoid |

The chain rule composes Jacobians by matrix product, outermost first: for $y = f(u(x))$, $\frac{\partial y}{\partial x} = \frac{\partial f}{\partial u} \frac{\partial u}{\partial x}$. Because elementwise activations have diagonal Jacobians, their factor in the chain collapses to an elementwise multiply, which is why backprop code is full of `*` rather than matrix products with explicit diagonals.

## The four gradients that matter

**Quadratic form.** $L = x^T A x$ has gradient $(A + A^T)x$: differentiate $\sum_{ij} A_{ij} x_i x_j$ with respect to $x_k$ and collect the two sums where $k$ appears as row or column index.

**Least squares.** $L = \lVert Ax - b \rVert^2 = (Ax-b)^T(Ax-b)$. Chain rule with inner function $r = Ax - b$ (Jacobian $A$) and outer $\lVert r \rVert^2$ (gradient $2r$):

$$
\nabla_x L = 2 A^T (Ax - b),
$$

which is where the normal equations in [[math/linear-algebra/orthogonality-projections-least-squares|Orthogonality, Projections, and Least Squares]] come from: set it to zero.

**Affine layer.** For $z = Wx + b$ with upstream gradient $\delta = \partial L/\partial z$:

$$
\frac{\partial L}{\partial W} = \delta\, x^T, \qquad
\frac{\partial L}{\partial x} = W^T \delta, \qquad
\frac{\partial L}{\partial b} = \delta.
$$

Derivation for $W$: $z_i = \sum_j W_{ij} x_j + b_i$, so $\partial z_i / \partial W_{ij} = x_j$ and $\partial L/\partial W_{ij} = \delta_i x_j$, the outer product. In batched code with row-vector samples $X \in \mathbb{R}^{B \times n}$ the same identities transpose to $\partial L/\partial W = \Delta^T X$ and the bias gradient sums over the batch, which is the version in [[ml/deep-learning/neural-networks-from-scratch|Neural Networks from Scratch]].

**Softmax cross-entropy.** With logits $z$, softmax $s_i = e^{z_i} / \sum_j e^{z_j}$, and one-hot target $y$, the softmax Jacobian is $\partial s/\partial z = \mathrm{diag}(s) - s s^T$. Multiplying by the cross-entropy gradient $\partial L/\partial s = -y/s$ (elementwise) and using $\sum_i y_i = 1$ collapses the whole thing:

$$
\frac{\partial L}{\partial z} = s - y.
$$

This cancellation is why frameworks fuse softmax and cross-entropy into one op: the fused gradient is simpler, cheaper, and numerically safer than composing the two Jacobians.

## JVPs, VJPs, and why backprop runs backward

Autodiff never materializes Jacobians. It computes Jacobian products ([Baydin et al. 2018](https://arxiv.org/abs/1502.05767)):

- Forward mode computes $Jv$, a Jacobian-vector product: push one input direction through the chain. Cost of one forward pass per input direction, so $n$ passes for a full gradient.
- Reverse mode computes $v^T J$, a vector-Jacobian product: pull one output sensitivity backward through the chain. Cost of one backward pass per output.

Training minimizes a scalar loss, $m = 1$, so reverse mode gets the entire gradient with respect to millions of parameters in a single backward pass, while forward mode would need one pass per parameter. That asymmetry is the whole reason backprop is reverse-mode AD. The affine-layer identities above are exactly the VJP rules: given $\delta$, produce $W^T\delta$ for the input and $\delta x^T$ for the weights.

## Verification

Every identity above, checked against autograd:

```python
import torch

torch.manual_seed(0)
n, m = 5, 4
A = torch.randn(n, n)
x = torch.randn(n, requires_grad=True)

(x @ A @ x).backward()
assert torch.allclose(x.grad, (A + A.T) @ x)          # quadratic form

M = torch.randn(m, n)
b = torch.randn(m)
x.grad = None
((M @ x - b) @ (M @ x - b)).backward()
assert torch.allclose(x.grad, 2 * M.T @ (M @ x - b))  # least squares

W = torch.randn(m, n, requires_grad=True)
xd = torch.randn(n)
delta = torch.randn(m)
(W @ xd @ delta).backward()                            # L = delta^T (W x)
assert torch.allclose(W.grad, torch.outer(delta, xd))  # affine: delta x^T

z = torch.randn(n, requires_grad=True)
y = torch.zeros(n); y[2] = 1.0
torch.nn.functional.cross_entropy(z, torch.tensor(2)).backward()
assert torch.allclose(z.grad, torch.softmax(z.detach(), 0) - y)  # s - y

X = torch.randn(n, n, requires_grad=True)
Xs = X @ X.T + n * torch.eye(n)                        # make it positive definite
torch.logdet(Xs).backward()
assert torch.allclose(X.grad, 2 * torch.inverse(Xs) @ X, atol=1e-5)  # chain of logdet
print("all identities verified")
```

## Sources

- [Parr and Howard, The Matrix Calculus You Need For Deep Learning](https://explained.ai/matrix-calculus/index.html) ([arXiv:1802.01528](https://arxiv.org/abs/1802.01528))
- [UW Matrix Calculus notes](https://atmos.washington.edu/~dennis/MatrixCalculus.pdf)
- [Petersen and Pedersen, The Matrix Cookbook](https://www.math.uwaterloo.ca/~hwolkowi/matrixcookbook.pdf)
- [Baydin et al. (2018), Automatic Differentiation in Machine Learning: a Survey](https://arxiv.org/abs/1502.05767)

## Related notes

- [[math/linear-algebra/orthogonality-projections-least-squares|Orthogonality, Projections, and Least Squares]]
- [[ml/deep-learning/neural-networks-from-scratch|Neural Networks from Scratch]]
- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
- [[math/linear-algebra/cheatsheet|Matrix Theory]]
