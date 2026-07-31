#!/usr/bin/env python3

from __future__ import annotations

import json
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def lines(text: str) -> list[str]:
    normalized = textwrap.dedent(text).strip("\n")
    return [line + "\n" for line in normalized.split("\n")]


def md(text: str) -> dict[str, object]:
    return {
        "cell_type": "markdown",
        "id": "",
        "metadata": {},
        "source": lines(text),
    }


def code(text: str) -> dict[str, object]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": "",
        "metadata": {},
        "outputs": [],
        "source": lines(text),
    }


def notebook(cells: list[dict[str, object]]) -> dict[str, object]:
    for idx, cell in enumerate(cells):
        cell["id"] = f"cell-{idx:03d}"
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write_notebook(relative_path: str, cells: list[dict[str, object]]) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(notebook(cells), indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)}")


def deep_learning_mlp() -> list[dict[str, object]]:
    return [
        md(
            r"""
            ---
            title: MLP from Scratch on MNIST
            category: Deep Learning
            tags:
              - deep learning
              - mlp
              - backpropagation
              - mnist
              - numpy
            date: 2026-07-31
            description: Implement a small multilayer perceptron with NumPy and train it on real handwritten digit data.
            sources:
              - https://huggingface.co/datasets/ylecun/mnist
              - https://numpy.org/numpy-tutorials/tutorial-deep-learning-on-mnist/
            ---

            ## Goal

            Build a small multilayer perceptron from scratch with NumPy, train it on the real [MNIST dataset](https://huggingface.co/datasets/ylecun/mnist), and inspect where the implementation earns its accuracy. The main point is not raw leaderboard performance. The point is to expose each tensor in the forward and backward pass.

            ## Why This Dataset

            MNIST is small enough to train on a laptop and still rich enough to show the shape of supervised learning. The input is a \(28 \times 28\) image flattened into \(784\) features. The target is one of \(10\) classes.

            We will fit

            $$
            x \\in \\mathbb{R}^{784} \\rightarrow h = \\text{ReLU}(x W_1 + b_1) \\rightarrow \\hat{y} = \\text{softmax}(h W_2 + b_2).
            $$

            The loss for a minibatch of size \(B\) is

            $$
            \\mathcal{L} = -\\frac{1}{B} \\sum_{i=1}^{B} \\log p_{i, y_i}.
            $$
            """
        ),
        code(
            """
            ## Uncomment this if you are running in a fresh environment.
            ## %pip install -q datasets numpy matplotlib

            import math
            import random
            from dataclasses import dataclass

            import matplotlib.pyplot as plt
            import numpy as np
            from datasets import load_dataset

            np.random.seed(7)
            random.seed(7)
            """
        ),
        code(
            """
            ds = load_dataset("ylecun/mnist")

            x_train = np.stack([np.array(example["image"], dtype=np.float32).reshape(-1) for example in ds["train"]]) / 255.0
            y_train = np.array(ds["train"]["label"], dtype=np.int64)
            x_test = np.stack([np.array(example["image"], dtype=np.float32).reshape(-1) for example in ds["test"]]) / 255.0
            y_test = np.array(ds["test"]["label"], dtype=np.int64)

            x_train = x_train[:20000]
            y_train = y_train[:20000]

            print(x_train.shape, y_train.shape, x_test.shape, y_test.shape)
            """
        ),
        md(
            r"""
            ## NumPy Model

            The hidden layer is

            $$
            H = \\max(0, XW_1 + b_1)
            $$

            and the logits are

            $$
            Z = HW_2 + b_2.
            $$

            After the softmax, the derivative of cross-entropy with respect to the logits is

            $$
            \\frac{\\partial \\mathcal{L}}{\\partial Z} = \\frac{P - Y}{B},
            $$

            where \(P\) is the predicted probability matrix and \(Y\) is the one-hot target matrix.
            """
        ),
        code(
            """
            def one_hot(y: np.ndarray, num_classes: int) -> np.ndarray:
                out = np.zeros((len(y), num_classes), dtype=np.float32)
                out[np.arange(len(y)), y] = 1.0
                return out


            def relu(x: np.ndarray) -> np.ndarray:
                return np.maximum(x, 0.0)


            def relu_grad(x: np.ndarray) -> np.ndarray:
                return (x > 0).astype(np.float32)


            def softmax(logits: np.ndarray) -> np.ndarray:
                shifted = logits - logits.max(axis=1, keepdims=True)
                exp = np.exp(shifted)
                return exp / exp.sum(axis=1, keepdims=True)


            def cross_entropy(probs: np.ndarray, y: np.ndarray) -> float:
                eps = 1e-9
                return float(-np.log(probs[np.arange(len(y)), y] + eps).mean())


            @dataclass
            class MLP:
                hidden_dim: int = 256
                input_dim: int = 784
                output_dim: int = 10

                def __post_init__(self) -> None:
                    scale1 = math.sqrt(2.0 / self.input_dim)
                    scale2 = math.sqrt(2.0 / self.hidden_dim)
                    self.W1 = np.random.randn(self.input_dim, self.hidden_dim).astype(np.float32) * scale1
                    self.b1 = np.zeros((1, self.hidden_dim), dtype=np.float32)
                    self.W2 = np.random.randn(self.hidden_dim, self.output_dim).astype(np.float32) * scale2
                    self.b2 = np.zeros((1, self.output_dim), dtype=np.float32)

                def forward(self, x: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
                    z1 = x @ self.W1 + self.b1
                    h1 = relu(z1)
                    z2 = h1 @ self.W2 + self.b2
                    probs = softmax(z2)
                    cache = {"x": x, "z1": z1, "h1": h1, "z2": z2, "probs": probs}
                    return probs, cache

                def backward(self, cache: dict[str, np.ndarray], y: np.ndarray) -> dict[str, np.ndarray]:
                    x = cache["x"]
                    z1 = cache["z1"]
                    h1 = cache["h1"]
                    probs = cache["probs"].copy()
                    batch_size = len(y)

                    probs[np.arange(batch_size), y] -= 1.0
                    probs /= batch_size

                    dW2 = h1.T @ probs
                    db2 = probs.sum(axis=0, keepdims=True)
                    dh1 = probs @ self.W2.T
                    dz1 = dh1 * relu_grad(z1)
                    dW1 = x.T @ dz1
                    db1 = dz1.sum(axis=0, keepdims=True)
                    return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}

                def step(self, grads: dict[str, np.ndarray], lr: float) -> None:
                    self.W1 -= lr * grads["W1"]
                    self.b1 -= lr * grads["b1"]
                    self.W2 -= lr * grads["W2"]
                    self.b2 -= lr * grads["b2"]
            """
        ),
        code(
            """
            def accuracy(model: MLP, x: np.ndarray, y: np.ndarray, batch_size: int = 512) -> float:
                preds = []
                for start in range(0, len(x), batch_size):
                    xb = x[start : start + batch_size]
                    probs, _ = model.forward(xb)
                    preds.append(probs.argmax(axis=1))
                pred = np.concatenate(preds)
                return float((pred == y).mean())


            def iterate_minibatches(x: np.ndarray, y: np.ndarray, batch_size: int):
                idx = np.random.permutation(len(x))
                for start in range(0, len(x), batch_size):
                    batch_idx = idx[start : start + batch_size]
                    yield x[batch_idx], y[batch_idx]


            model = MLP(hidden_dim=256)
            history = {"train_loss": [], "train_acc": [], "test_acc": []}

            epochs = 12
            lr = 0.08
            batch_size = 256

            for epoch in range(epochs):
                losses = []
                for xb, yb in iterate_minibatches(x_train, y_train, batch_size):
                    probs, cache = model.forward(xb)
                    loss = cross_entropy(probs, yb)
                    grads = model.backward(cache, yb)
                    model.step(grads, lr=lr)
                    losses.append(loss)

                train_acc = accuracy(model, x_train[:4000], y_train[:4000])
                test_acc = accuracy(model, x_test, y_test)
                history["train_loss"].append(float(np.mean(losses)))
                history["train_acc"].append(train_acc)
                history["test_acc"].append(test_acc)
                print(f"epoch={epoch:02d} loss={history['train_loss'][-1]:.4f} train_acc={train_acc:.4f} test_acc={test_acc:.4f}")
            """
        ),
        code(
            """
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            axes[0].plot(history["train_loss"], marker="o")
            axes[0].set_title("Training loss")
            axes[0].set_xlabel("epoch")
            axes[0].set_ylabel("cross entropy")

            axes[1].plot(history["train_acc"], marker="o", label="train")
            axes[1].plot(history["test_acc"], marker="o", label="test")
            axes[1].set_title("Accuracy")
            axes[1].set_xlabel("epoch")
            axes[1].legend()
            plt.show()
            """
        ),
        code(
            """
            sample_idx = np.random.choice(len(x_test), size=12, replace=False)
            fig, axes = plt.subplots(3, 4, figsize=(10, 8))
            probs, _ = model.forward(x_test[sample_idx])
            preds = probs.argmax(axis=1)

            for ax, idx, pred in zip(axes.flat, sample_idx, preds):
                ax.imshow(x_test[idx].reshape(28, 28), cmap="gray")
                ax.set_title(f"pred={pred} true={y_test[idx]}")
                ax.axis("off")

            plt.tight_layout()
            plt.show()
            """
        ),
        md(
            r"""
            ## What To Extend

            A few natural next steps:

            1. Replace plain SGD with momentum or Adam and compare convergence.
            2. Add another hidden layer and watch how the gradient norms change.
            3. Swap the full-batch NumPy implementation for a Torch version and compare ergonomics.
            """
        ),
    ]


def deep_learning_autodiff() -> list[dict[str, object]]:
    return [
        md(
            r"""
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
              - https://huggingface.co/datasets/ylecun/mnist
              - https://docs.pytorch.org/tutorials/beginner/basics/autogradqs_tutorial.html
            ---

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
            """
        ),
        code(
            """
            ## %pip install -q datasets torch numpy matplotlib

            import numpy as np
            import torch
            import torch.nn.functional as F
            from datasets import load_dataset
            """
        ),
        code(
            """
            ds = load_dataset("ylecun/mnist")
            train_subset = ds["train"].select(range(1024))
            test_subset = ds["test"].select(range(1024))

            x = np.stack([np.array(example["image"], dtype=np.float32).reshape(-1) for example in train_subset]) / 255.0
            y = np.array(train_subset["label"], dtype=np.int64)

            batch_x = x[:256]
            batch_y = y[:256]

            print(batch_x.shape, batch_y.shape)
            """
        ),
        code(
            """
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
            """
        ),
        code(
            """
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
            """
        ),
        md(
            r"""
            ## Finite Difference Sanity Check

            Autodiff and the symbolic derivation can still agree on the same bug. A cheap extra check is finite differences on a few random coordinates:

            $$
            \\frac{\\partial \\mathcal{L}}{\\partial \\theta_j} \\approx \\frac{\\mathcal{L}(\\theta_j + \\varepsilon) - \\mathcal{L}(\\theta_j - \\varepsilon)}{2\\varepsilon}.
            $$
            """
        ),
        code(
            """
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
            """
        ),
        code(
            """
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
            """
        ),
        md(
            r"""
            ## Takeaway

            The interesting result is not that `autograd` works. The interesting result is that a short derivation, finite differences, and the framework implementation all agree on the same real minibatch. Once that is in place, the rest of deep learning code becomes much less mysterious.
            """
        ),
    ]


def char_rnn() -> list[dict[str, object]]:
    return [
        md(
            r"""
            ---
            title: Character-Level RNN on WikiText-2
            category: Deep Learning
            tags:
              - deep learning
              - rnn
              - gru
              - language modeling
              - wikitext
              - pytorch
            date: 2026-07-31
            description: Train a small recurrent language model on WikiText-2 and inspect how sequence state evolves.
            sources:
              - https://huggingface.co/datasets/Salesforce/wikitext
              - https://docs.pytorch.org/tutorials/beginner/nlp/sequence_models_tutorial.html
            ---

            ## Goal

            Train a small character-level recurrent model on [WikiText-2](https://huggingface.co/datasets/Salesforce/wikitext). We will crop the corpus down to a few hundred thousand characters so the notebook stays laptop-sized while still learning visible local structure.

            For a recurrent network,

            $$
            h_t = f(W_{xh} x_t + W_{hh} h_{t-1} + b_h), \\qquad
            \\hat{y}_t = W_{hy} h_t + b_y.
            $$

            We will use a GRU because it keeps the code compact while still preserving the recurrent inductive bias.
            """
        ),
        code(
            """
            ## %pip install -q datasets torch matplotlib

            import math
            import random

            import matplotlib.pyplot as plt
            import torch
            import torch.nn as nn
            import torch.nn.functional as F
            from datasets import load_dataset

            torch.manual_seed(7)
            random.seed(7)
            """
        ),
        code(
            """
            ds = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1")
            train_text = "\\n".join(ds["train"]["text"])[:300000]
            valid_text = "\\n".join(ds["validation"]["text"])[:50000]

            vocab = sorted(set(train_text + valid_text))
            stoi = {ch: i for i, ch in enumerate(vocab)}
            itos = {i: ch for ch, i in stoi.items()}

            train_ids = torch.tensor([stoi[ch] for ch in train_text], dtype=torch.long)
            valid_ids = torch.tensor([stoi[ch] for ch in valid_text], dtype=torch.long)

            print(f"chars={len(train_ids):,} vocab={len(vocab)}")
            """
        ),
        code(
            """
            def get_batch(data: torch.Tensor, batch_size: int, block_size: int, device: str):
                starts = torch.randint(0, len(data) - block_size - 1, (batch_size,))
                x = torch.stack([data[s : s + block_size] for s in starts]).to(device)
                y = torch.stack([data[s + 1 : s + block_size + 1] for s in starts]).to(device)
                return x, y


            class CharRNN(nn.Module):
                def __init__(self, vocab_size: int, embed_dim: int = 64, hidden_dim: int = 128):
                    super().__init__()
                    self.embed = nn.Embedding(vocab_size, embed_dim)
                    self.rnn = nn.GRU(embed_dim, hidden_dim, batch_first=True)
                    self.proj = nn.Linear(hidden_dim, vocab_size)

                def forward(self, idx, hidden=None):
                    x = self.embed(idx)
                    out, hidden = self.rnn(x, hidden)
                    logits = self.proj(out)
                    return logits, hidden

                @torch.no_grad()
                def generate(self, idx, max_new_tokens: int):
                    hidden = None
                    for _ in range(max_new_tokens):
                        logits, hidden = self(idx[:, -1:], hidden)
                        probs = logits[:, -1].softmax(dim=-1)
                        next_idx = torch.multinomial(probs, num_samples=1)
                        idx = torch.cat([idx, next_idx], dim=1)
                    return idx
            """
        ),
        code(
            """
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = CharRNN(len(vocab)).to(device)
            optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3)

            batch_size = 64
            block_size = 128
            train_losses = []

            for step in range(600):
                xb, yb = get_batch(train_ids, batch_size, block_size, device)
                logits, _ = model(xb)
                loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), yb.reshape(-1))
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_losses.append(float(loss))

                if step % 200 == 0:
                    print(f"step={step:04d} loss={float(loss):.4f}")
            """
        ),
        code(
            """
            plt.figure(figsize=(8, 4))
            plt.plot(train_losses)
            plt.title("Char-RNN training loss")
            plt.xlabel("step")
            plt.ylabel("cross entropy")
            plt.show()
            """
        ),
        code(
            """
            start = torch.tensor([[stoi["T"]]], dtype=torch.long, device=device)
            sample = model.generate(start, max_new_tokens=600)[0].tolist()
            print("".join(itos[i] for i in sample))
            """
        ),
        md(
            r"""
            ## What To Look For

            The model usually learns punctuation, line breaks, and some short-range spelling statistics before it learns anything like semantics. That is exactly the point. The recurrent state is carrying local context forward step by step, and you can see how far that alone gets you.
            """
        ),
    ]


def decoder_only_transformer() -> list[dict[str, object]]:
    return [
        md(
            r"""
            ---
            title: Decoder-Only Transformer on WikiText-2
            category: Deep Learning
            tags:
              - deep learning
              - transformer
              - self-attention
              - language modeling
              - wikitext
              - pytorch
            date: 2026-07-31
            description: Build a small decoder-only Transformer for character-level language modeling on WikiText-2.
            sources:
              - https://huggingface.co/datasets/Salesforce/wikitext
              - https://docs.pytorch.org/tutorials/intermediate/transformer_building_blocks.html
            ---

            ## Goal

            Build a tiny decoder-only Transformer on [WikiText-2](https://huggingface.co/datasets/Salesforce/wikitext). We will use a cropped character-level corpus so the model still shows real attention behavior without turning the notebook into an hours-long training run.

            Causal self-attention computes

            $$
            \\text{Attn}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^\\top}{\\sqrt{d_k}} + M\\right)V,
            $$

            where the mask \(M\) is \(-\\infty\) above the diagonal so that token \(t\) cannot read from the future.
            """
        ),
        code(
            """
            ## %pip install -q datasets torch matplotlib einops

            import math
            import random

            import matplotlib.pyplot as plt
            import torch
            import torch.nn as nn
            import torch.nn.functional as F
            from datasets import load_dataset
            """
        ),
        code(
            """
            ds = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1")
            text = "\\n".join(ds["train"]["text"])[:300000]

            vocab = sorted(set(text))
            stoi = {ch: i for i, ch in enumerate(vocab)}
            itos = {i: ch for ch, i in stoi.items()}
            data = torch.tensor([stoi[ch] for ch in text], dtype=torch.long)

            split = int(0.9 * len(data))
            train_ids = data[:split]
            valid_ids = data[split:]

            print(f"chars={len(data):,} vocab={len(vocab)}")
            """
        ),
        code(
            """
            def get_batch(data: torch.Tensor, batch_size: int, block_size: int, device: str):
                starts = torch.randint(0, len(data) - block_size - 1, (batch_size,))
                x = torch.stack([data[s : s + block_size] for s in starts]).to(device)
                y = torch.stack([data[s + 1 : s + block_size + 1] for s in starts]).to(device)
                return x, y


            class CausalSelfAttention(nn.Module):
                def __init__(self, d_model: int, n_heads: int, block_size: int):
                    super().__init__()
                    assert d_model % n_heads == 0
                    self.n_heads = n_heads
                    self.head_dim = d_model // n_heads
                    self.qkv = nn.Linear(d_model, 3 * d_model)
                    self.proj = nn.Linear(d_model, d_model)
                    mask = torch.tril(torch.ones(block_size, block_size))
                    self.register_buffer("mask", mask.view(1, 1, block_size, block_size))

                def forward(self, x):
                    B, T, C = x.shape
                    qkv = self.qkv(x)
                    q, k, v = qkv.chunk(3, dim=-1)

                    q = q.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
                    k = k.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
                    v = v.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)

                    scores = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
                    scores = scores.masked_fill(self.mask[:, :, :T, :T] == 0, float("-inf"))
                    attn = scores.softmax(dim=-1)
                    out = attn @ v
                    out = out.transpose(1, 2).contiguous().view(B, T, C)
                    return self.proj(out), attn


            class Block(nn.Module):
                def __init__(self, d_model: int, n_heads: int, block_size: int, mlp_mult: int = 4):
                    super().__init__()
                    self.ln1 = nn.LayerNorm(d_model)
                    self.attn = CausalSelfAttention(d_model, n_heads, block_size)
                    self.ln2 = nn.LayerNorm(d_model)
                    self.mlp = nn.Sequential(
                        nn.Linear(d_model, mlp_mult * d_model),
                        nn.GELU(),
                        nn.Linear(mlp_mult * d_model, d_model),
                    )

                def forward(self, x):
                    attn_out, attn = self.attn(self.ln1(x))
                    x = x + attn_out
                    x = x + self.mlp(self.ln2(x))
                    return x, attn


            class TinyGPT(nn.Module):
                def __init__(self, vocab_size: int, block_size: int, d_model: int = 128, n_heads: int = 4, n_layers: int = 3):
                    super().__init__()
                    self.block_size = block_size
                    self.token = nn.Embedding(vocab_size, d_model)
                    self.pos = nn.Embedding(block_size, d_model)
                    self.blocks = nn.ModuleList([Block(d_model, n_heads, block_size) for _ in range(n_layers)])
                    self.ln_f = nn.LayerNorm(d_model)
                    self.head = nn.Linear(d_model, vocab_size)

                def forward(self, idx):
                    B, T = idx.shape
                    pos = torch.arange(T, device=idx.device)
                    x = self.token(idx) + self.pos(pos)[None, :, :]
                    attn_maps = []
                    for block in self.blocks:
                        x, attn = block(x)
                        attn_maps.append(attn)
                    logits = self.head(self.ln_f(x))
                    return logits, attn_maps

                @torch.no_grad()
                def generate(self, idx, max_new_tokens: int):
                    for _ in range(max_new_tokens):
                        idx_cond = idx[:, -self.block_size :]
                        logits, _ = self(idx_cond)
                        probs = logits[:, -1].softmax(dim=-1)
                        next_idx = torch.multinomial(probs, num_samples=1)
                        idx = torch.cat([idx, next_idx], dim=1)
                    return idx
            """
        ),
        code(
            """
            device = "cuda" if torch.cuda.is_available() else "cpu"
            block_size = 96
            model = TinyGPT(len(vocab), block_size=block_size).to(device)
            optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-2)

            losses = []
            for step in range(400):
                xb, yb = get_batch(train_ids, batch_size=32, block_size=block_size, device=device)
                logits, _ = model(xb)
                loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), yb.reshape(-1))
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                losses.append(float(loss))

                if step % 100 == 0:
                    print(f"step={step:04d} loss={float(loss):.4f}")
            """
        ),
        code(
            """
            plt.figure(figsize=(8, 4))
            plt.plot(losses)
            plt.title("Decoder-only Transformer training loss")
            plt.xlabel("step")
            plt.ylabel("cross entropy")
            plt.show()
            """
        ),
        code(
            """
            prompt = torch.tensor([[stoi["T"]]], dtype=torch.long, device=device)
            sample = model.generate(prompt, max_new_tokens=600)[0].tolist()
            print("".join(itos[i] for i in sample))
            """
        ),
        code(
            """
            xb, _ = get_batch(valid_ids, batch_size=1, block_size=64, device=device)
            _, attn_maps = model(xb)
            head0 = attn_maps[0][0, 0].detach().cpu()

            plt.figure(figsize=(6, 5))
            plt.imshow(head0, cmap="magma")
            plt.title("Layer 0, head 0 attention map")
            plt.xlabel("key position")
            plt.ylabel("query position")
            plt.colorbar()
            plt.show()
            """
        ),
        md(
            r"""
            ## Why This Notebook Matters

            A character-level model is toy-sized, but the mechanics are real. The same masking rule, residual shape discipline, and next-token objective scale up to practical decoder-only language models.
            """
        ),
    ]


def movielens_retrieval() -> list[dict[str, object]]:
    return [
        md(
            r"""
            ---
            title: MovieLens 100K Two-Tower Retrieval
            category: Recommender Systems
            tags:
              - recommender systems
              - two tower
              - retrieval
              - implicit feedback
              - movielens
              - pytorch
            date: 2026-07-31
            description: Train a small two-tower retrieval model on MovieLens 100K using implicit feedback derived from real ratings.
            sources:
              - https://files.grouplens.org/datasets/movielens/ml-100k-README.txt
              - https://files.grouplens.org/datasets/movielens/ml-100k/u.data
              - https://files.grouplens.org/datasets/movielens/ml-100k/u.item
              - https://www.tensorflow.org/recommenders/examples/basic_retrieval
            ---

            ## Goal

            Build a small retrieval model on the real [MovieLens 100K data set](https://files.grouplens.org/datasets/movielens/ml-100k-README.txt). We will treat ratings of at least \(4\) as positive implicit feedback and train a two-tower model with sampled negatives.

            The scoring function is the dot product

            $$
            s(u, i) = q_u^\\top k_i,
            $$

            where \(q_u\\) is the user embedding and \(k_i\\) is the item embedding. Retrieval quality will be measured with Recall@K and MRR@K on a held-out item per user.
            """
        ),
        code(
            """
            ## %pip install -q pandas numpy torch matplotlib

            from pathlib import Path
            from urllib.request import urlopen

            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd
            import torch
            import torch.nn as nn
            import torch.nn.functional as F

            SEED = 7
            np.random.seed(SEED)
            _ = torch.manual_seed(SEED)
            """
        ),
        code(
            """
            repo_root = next((path for path in [Path.cwd(), *Path.cwd().parents] if (path / ".git").exists()), Path.cwd())
            root = repo_root / "work/notebook-data/movielens-100k"
            root.mkdir(parents=True, exist_ok=True)

            ratings_url = "https://files.grouplens.org/datasets/movielens/ml-100k/u.data"
            items_url = "https://files.grouplens.org/datasets/movielens/ml-100k/u.item"

            ratings_path = root / "u.data"
            items_path = root / "u.item"

            for url, path in [(ratings_url, ratings_path), (items_url, items_path)]:
                if not path.exists():
                    path.write_bytes(urlopen(url).read())

            ratings = pd.read_csv(
                ratings_path,
                sep="\\t",
                names=["user_id", "item_id", "rating", "timestamp"],
                encoding="latin-1",
            )

            items = pd.read_csv(
                items_path,
                sep="|",
                header=None,
                encoding="latin-1",
                usecols=[0, 1],
                names=["item_id", "title"],
            )

            ratings = ratings.merge(items, on="item_id", how="left")
            ratings.head()
            """
        ),
        code(
            """
            positives = ratings[ratings["rating"] >= 4].copy()
            positives = positives.sort_values(["user_id", "timestamp"])

            heldout = positives.groupby("user_id").tail(1)
            train = positives.drop(index=heldout.index)

            user_ids = sorted(positives["user_id"].unique())
            item_ids = sorted(positives["item_id"].unique())
            user_to_idx = {u: i for i, u in enumerate(user_ids)}
            item_to_idx = {i: j for j, i in enumerate(item_ids)}

            train_user = torch.tensor(train["user_id"].map(user_to_idx).to_numpy(), dtype=torch.long)
            train_item = torch.tensor(train["item_id"].map(item_to_idx).to_numpy(), dtype=torch.long)
            test_pairs = list(
                zip(
                    heldout["user_id"].map(user_to_idx).to_numpy(),
                    heldout["item_id"].map(item_to_idx).to_numpy(),
                )
            )

            positives_by_user = {
                user_to_idx[u]: set(group["item_id"].map(item_to_idx).tolist())
                for u, group in positives.groupby("user_id")
            }

            num_users = len(user_ids)
            num_items = len(item_ids)
            print(f"train positives={len(train):,} heldout users={len(test_pairs):,}")
            """
        ),
        code(
            """
            class TwoTower(nn.Module):
                def __init__(self, num_users: int, num_items: int, dim: int = 64):
                    super().__init__()
                    self.user = nn.Embedding(num_users, dim)
                    self.item = nn.Embedding(num_items, dim)
                    self.user_bias = nn.Embedding(num_users, 1)
                    self.item_bias = nn.Embedding(num_items, 1)

                def score(self, users, items):
                    dot = (self.user(users) * self.item(items)).sum(dim=-1)
                    bias = self.user_bias(users).squeeze(-1) + self.item_bias(items).squeeze(-1)
                    return dot + bias
            """
        ),
        code(
            """
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = TwoTower(num_users, num_items, dim=64).to(device)
            opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)

            batch_size = 2048
            steps = 2500
            losses = []

            train_user_device = train_user.to(device)
            train_item_device = train_item.to(device)

            for step in range(steps):
                idx = torch.randint(0, len(train_user_device), (batch_size,), device=device)
                u = train_user_device[idx]
                pos_i = train_item_device[idx]
                neg_i = torch.randint(0, num_items, (batch_size,), device=device)

                pos_score = model.score(u, pos_i)
                neg_score = model.score(u, neg_i)
                logits = torch.cat([pos_score, neg_score], dim=0)
                labels = torch.cat([torch.ones_like(pos_score), torch.zeros_like(neg_score)], dim=0)

                loss = F.binary_cross_entropy_with_logits(logits, labels)
                loss_value = loss.item()
                opt.zero_grad()
                loss.backward()
                opt.step()
                losses.append(loss_value)

                if step % 250 == 0:
                    print(f"step={step:04d} loss={loss_value:.4f}")
            """
        ),
        code(
            """
            def evaluate(model: TwoTower, test_pairs, positives_by_user, k: int = 10):
                user_emb = model.user.weight.detach()
                item_emb = model.item.weight.detach()
                user_bias = model.user_bias.weight.detach().squeeze(-1)
                item_bias = model.item_bias.weight.detach().squeeze(-1)

                recalls = []
                rr = []
                for u, target in test_pairs:
                    scores = user_emb[u] @ item_emb.T + user_bias[u] + item_bias
                    seen = positives_by_user[u] - {target}
                    if seen:
                        scores[list(seen)] = -1e9
                    topk = scores.topk(k).indices.tolist()
                    if target in topk:
                        recalls.append(1.0)
                        rr.append(1.0 / (topk.index(target) + 1))
                    else:
                        recalls.append(0.0)
                        rr.append(0.0)
                return float(np.mean(recalls)), float(np.mean(rr))


            recall_at_10, mrr_at_10 = evaluate(model.cpu(), test_pairs, positives_by_user, k=10)
            print({"recall@10": recall_at_10, "mrr@10": mrr_at_10})
            """
        ),
        code(
            """
            plt.figure(figsize=(8, 4))
            plt.plot(losses)
            plt.title("Two-tower retrieval training loss")
            plt.xlabel("step")
            plt.ylabel("BCE loss")
            plt.show()
            """
        ),
        code(
            """
            title_to_item = {row.title: item_to_idx[row.item_id] for row in items.itertuples() if row.item_id in item_to_idx}
            item_lookup = {item_to_idx[row.item_id]: row.title for row in items.itertuples() if row.item_id in item_to_idx}

            anchor = "Star Wars (1977)"
            anchor_idx = title_to_item[anchor]
            anchor_vec = model.item.weight.detach()[anchor_idx]
            sims = model.item.weight.detach() @ anchor_vec
            top = sims.topk(10).indices.tolist()
            [item_lookup[i] for i in top]
            """
        ),
        md(
            """
            ## Where To Push Next

            This notebook is the retrieval stage only. Good follow-ons:

            1. Add side features from `u.user` and genre indicators from `u.item`.
            2. Replace pointwise BCE with BPR or sampled softmax.
            3. Add a reranker and compare Recall@K against NDCG@K.
            """
        ),
    ]


def main() -> int:
    write_notebook("content/deep-learning/mlp-from-scratch-on-mnist.ipynb", deep_learning_mlp())
    write_notebook("content/deep-learning/checking-manual-gradients-against-autodiff-on-mnist.ipynb", deep_learning_autodiff())
    write_notebook("content/deep-learning/character-level-rnn-on-wikitext-2.ipynb", char_rnn())
    write_notebook("content/deep-learning/decoder-only-transformer-on-wikitext-2.ipynb", decoder_only_transformer())
    write_notebook("content/recc-sys/movielens-100k-two-tower-retrieval.ipynb", movielens_retrieval())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
