---
title: Checking Manual Gradients Against Autodiff on MNIST
category: Deep Learning
tags:
  - deep learning
  - autodiff
  - gradients
  - mnist
  - pytorch
date: 2026-07-31
description: Compare a hand-derived softmax regression gradient against PyTorch autograd on a real MNIST minibatch.
sources:
  - "https://huggingface.co/datasets/ylecun/mnist"
  - "https://docs.pytorch.org/tutorials/beginner/basics/autogradqs_tutorial.html"
---

<!-- Generated from content/deep-learning/checking-manual-gradients-against-autodiff-on-mnist.ipynb -->

## Goal

The shortest path to trusting autodiff is to catch it agreeing with a derivation you can inspect. We will use a real minibatch from [MNIST](https://huggingface.co/datasets/ylecun/mnist), derive the gradient of softmax regression by hand, and compare it against `torch.autograd`.

For logits \(Z = XW + b\), probabilities \(P = \\text{softmax}(Z)\), and one-hot targets \(Y\), the cross-entropy derivative is

$$
\\frac{\\partial \\mathcal{L}}{\\partial Z} = \\frac{P - Y}{B}.
$$

The weight gradient follows immediately:

$$
\\frac{\\partial \\mathcal{L}}{\\partial W} = X^\\top \\frac{P - Y}{B}.
$$

```python
## %pip install -q datasets torch numpy matplotlib

import numpy as np
import torch
import torch.nn.functional as F
from datasets import load_dataset
```

```text
/Users/elimelt/Documents/Codex/2026-07-30/github-plugin-github-openai-curated-remote-2/work/notes/.venv/lib/python3.12/site-packages/tqdm/auto.py:21: TqdmWarning: IProgress not found. Please update jupyter and ipywidgets. See https://ipywidgets.readthedocs.io/en/stable/user_install.html
  from .autonotebook import tqdm as notebook_tqdm
```

```python
ds = load_dataset("ylecun/mnist")
train_subset = ds["train"].select(range(1024))
test_subset = ds["test"].select(range(1024))

x = np.stack([np.array(example["image"], dtype=np.float32).reshape(-1) for example in train_subset]) / 255.0
y = np.array(train_subset["label"], dtype=np.int64)

batch_x = x[:256]
batch_y = y[:256]

print(batch_x.shape, batch_y.shape)
```

```text
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
```

```text
(256, 784) (256,)
```

```python
def softmax_numpy(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def manual_gradients(xb: np.ndarray, yb: np.ndarray, W: np.ndarray, b: np.ndarray):
    logits = xb @ W + b
    probs = softmax_numpy(logits)
    one_hot = np.zeros_like(probs)
    one_hot[np.arange(len(yb)), yb] = 1.0
    dz = (probs - one_hot) / len(yb)
    dW = xb.T @ dz
    db = dz.sum(axis=0, keepdims=True)
    loss = -np.log(probs[np.arange(len(yb)), yb] + 1e-9).mean()
    return loss, dW, db
```

```python
torch.manual_seed(7)

W_np = np.random.randn(784, 10).astype(np.float32) * 0.01
b_np = np.zeros((1, 10), dtype=np.float32)

manual_loss, manual_dW, manual_db = manual_gradients(batch_x, batch_y, W_np, b_np)

xb_t = torch.tensor(batch_x, dtype=torch.float32)
yb_t = torch.tensor(batch_y, dtype=torch.long)
W_t = torch.tensor(W_np, dtype=torch.float32, requires_grad=True)
b_t = torch.tensor(b_np, dtype=torch.float32, requires_grad=True)

logits_t = xb_t @ W_t + b_t
loss_t = F.cross_entropy(logits_t, yb_t)
loss_t.backward()

max_abs_dW = np.abs(manual_dW - W_t.grad.detach().numpy()).max()
max_abs_db = np.abs(manual_db - b_t.grad.detach().numpy()).max()

print("manual loss:", manual_loss)
print("autodiff loss:", float(loss_t))
print("max |dW_manual - dW_autodiff| =", max_abs_dW)
print("max |db_manual - db_autodiff| =", max_abs_db)
```

```text
manual loss: 2.3231063
autodiff loss: 2.323106527328491
max |dW_manual - dW_autodiff| = 1.4901161e-08
max |db_manual - db_autodiff| = 1.8626451e-08
```

```text
/var/folders/89/s5_6m3_s753b66rwdjt2g1lw0000gn/T/ipykernel_20654/2719728609.py:21: UserWarning: Converting a tensor with requires_grad=True to a scalar may lead to unexpected behavior.
Consider using tensor.detach() first. (Triggered internally at /Users/runner/work/pytorch/pytorch/torch/csrc/autograd/generated/python_variable_methods.cpp:823.)
  print("autodiff loss:", float(loss_t))
```

## Finite Difference Sanity Check

Autodiff and the symbolic derivation can still agree on the same bug. A cheap extra check is finite differences on a few random coordinates:

$$
\\frac{\\partial \\mathcal{L}}{\\partial \\theta_j} \\approx \\frac{\\mathcal{L}(\\theta_j + \\varepsilon) - \\mathcal{L}(\\theta_j - \\varepsilon)}{2\\varepsilon}.
$$

```python
def loss_only(xb: np.ndarray, yb: np.ndarray, W: np.ndarray, b: np.ndarray) -> float:
    logits = xb @ W + b
    probs = softmax_numpy(logits)
    return float(-np.log(probs[np.arange(len(yb)), yb] + 1e-9).mean())


eps = 1e-4
checks = [(0, 0), (123, 3), (511, 7)]

for i, j in checks:
    W_pos = W_np.copy()
    W_neg = W_np.copy()
    W_pos[i, j] += eps
    W_neg[i, j] -= eps
    fd = (loss_only(batch_x, batch_y, W_pos, b_np) - loss_only(batch_x, batch_y, W_neg, b_np)) / (2 * eps)
    print((i, j), "finite-diff =", fd, "manual =", manual_dW[i, j])
```

```text
(0, 0) finite-diff = 0.0 manual = 0.0
(123, 3) finite-diff = -0.00476837158203125 manual = -0.004906716
(511, 7) finite-diff = 0.015497207641601562 manual = 0.01614688
```

```python
class SoftmaxRegressor(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(784, 10)

    def forward(self, x):
        return self.linear(x)


model = SoftmaxRegressor()
opt = torch.optim.Adam(model.parameters(), lr=1e-3)

x_train = torch.tensor(x[:1024], dtype=torch.float32)
y_train = torch.tensor(y[:1024], dtype=torch.long)
x_test = torch.tensor(
    np.stack([np.array(example["image"], dtype=np.float32).reshape(-1) for example in test_subset]) / 255.0,
    dtype=torch.float32,
)
y_test = torch.tensor(test_subset["label"], dtype=torch.long)

history = []
batch_size = 256

for epoch in range(10):
    perm = torch.randperm(len(x_train))
    for start in range(0, len(x_train), batch_size):
        idx = perm[start : start + batch_size]
        logits = model(x_train[idx])
        loss = F.cross_entropy(logits, y_train[idx])
        opt.zero_grad()
        loss.backward()
        opt.step()

    with torch.no_grad():
        train_acc = (model(x_train).argmax(dim=1) == y_train).float().mean().item()
        test_acc = (model(x_test).argmax(dim=1) == y_test).float().mean().item()
        history.append((train_acc, test_acc))
        print(f"epoch={epoch:02d} train_acc={train_acc:.4f} test_acc={test_acc:.4f}")
```

```text
epoch=00 train_acc=0.3193 test_acc=0.2715
epoch=01 train_acc=0.5527 test_acc=0.4365
epoch=02 train_acc=0.6621 test_acc=0.5186
epoch=03 train_acc=0.7275 test_acc=0.6084
epoch=04 train_acc=0.7646 test_acc=0.6396
epoch=05 train_acc=0.7842 test_acc=0.6758
epoch=06 train_acc=0.8018 test_acc=0.6895
epoch=07 train_acc=0.8115 test_acc=0.7002
epoch=08 train_acc=0.8125 test_acc=0.7090
epoch=09 train_acc=0.8164 test_acc=0.7168
```

## Takeaway

The interesting result is not that `autograd` works. The interesting result is that a short derivation, finite differences, and the framework implementation all agree on the same real minibatch. Once that is in place, the rest of deep learning code becomes much less mysterious.
