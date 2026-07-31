---
title: Decoder-Only Transformers
category: Deep Learning
tags:
  - deep learning
  - transformers
  - self-attention
  - autoregressive models
  - pytorch
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: The decoder-only transformer from the modeling side, including causal self-attention, multi-head projection, residual blocks, and implementations in NumPy and PyTorch with einops.
sources:
  - title: Attention Is All You Need
    url: https://arxiv.org/abs/1706.03762
    type: paper
  - title: Language Models are Unsupervised Multitask Learners
    url: https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf
    type: paper
  - title: einops
    url: https://einops.rocks/
    type: docs
---

## Purpose

This note covers the decoder-only transformer as a sequence model. The serving notes already discuss it from the systems side in [[ml/serving-systems/transformers|Transformer Architecture and Implementation]]. Here the focus is the actual computation: causal self-attention, the block structure, and why autoregressive training fits the model.

## The Core Recurrence-Free Idea

Given token embeddings $X \in \mathbb{R}^{T \times d_{model}}$, produce queries, keys, and values:

$$
Q = XW_Q,\quad K = XW_K,\quad V = XW_V
$$

with $W_Q, W_K, W_V \in \mathbb{R}^{d_{model} \times d_k}$.

Scaled dot-product attention is

$$
\text{Attn}(Q,K,V) = \text{softmax}\left(\frac{QK^\top}{\sqrt{d_k}} + M\right)V
$$

where $M$ is a causal mask whose future entries are $-\infty$.

The mask enforces

$$
\hat{x}_t = f(x_{\le t})
$$

so the model can be trained on next-token prediction without peeking ahead.

## Multi-Head Attention

One attention map is a bottleneck. Multi-head attention splits the model dimension into $h$ heads:

$$
\text{MHA}(X) = \text{Concat}(\text{head}_1, \dots, \text{head}_h)W_O
$$

with

$$
\text{head}_i = \text{Attn}(XW_Q^{(i)}, XW_K^{(i)}, XW_V^{(i)})
$$

Each head can specialize in a different relation: locality, induction, copying, syntax, and so on.

## The Decoder Block

A modern pre-norm decoder block is usually

$$
\begin{aligned}
H_1 &= X + \text{MHA}(\text{LN}(X)) \\
H_2 &= H_1 + \text{MLP}(\text{LN}(H_1))
\end{aligned}
$$

The MLP is typically a two-layer expansion and contraction:

$$
\text{MLP}(x) = W_2 \phi(W_1x + b_1) + b_2
$$

The residual path matters. Without it, very deep stacks are much harder to optimize.

## Training Objective

For tokens $(x_1, \dots, x_T)$, maximize

$$
\log p(x_1, \dots, x_T) = \sum_{t=1}^{T} \log p(x_t \mid x_{<t})
$$

Training uses teacher forcing: all positions are computed in parallel, but the mask ensures the model at position $t$ still depends only on earlier tokens.

## NumPy Self-Attention

This implementation exposes the actual tensor algebra for one batch.

```python
import numpy as np

def causal_mask(T):
    mask = np.full((T, T), -1e9, dtype=np.float32)
    return np.triu(mask, k=1)

def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)

def self_attention(x, Wq, Wk, Wv):
    # x: (B, T, D)
    Q = x @ Wq
    K = x @ Wk
    V = x @ Wv
    scores = Q @ np.swapaxes(K, -1, -2) / np.sqrt(Q.shape[-1])
    scores = scores + causal_mask(x.shape[1])[None, :, :]
    probs = softmax(scores, axis=-1)
    return probs @ V
```

## PyTorch Block with `einops`

```python
import torch
import torch.nn as nn
from einops import rearrange

class CausalSelfAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        assert d_model % n_heads == 0
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.qkv = nn.Linear(d_model, 3 * d_model, bias=False)
        self.out = nn.Linear(d_model, d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.shape
        qkv = self.qkv(x)
        q, k, v = qkv.chunk(3, dim=-1)

        q = rearrange(q, "b t (h d) -> b h t d", h=self.n_heads)
        k = rearrange(k, "b t (h d) -> b h t d", h=self.n_heads)
        v = rearrange(v, "b t (h d) -> b h t d", h=self.n_heads)

        scores = torch.matmul(q, k.transpose(-1, -2)) / (self.head_dim ** 0.5)
        mask = torch.triu(torch.ones(T, T, device=x.device, dtype=torch.bool), diagonal=1)
        scores = scores.masked_fill(mask, float("-inf"))
        attn = scores.softmax(dim=-1)
        y = torch.matmul(attn, v)
        y = rearrange(y, "b h t d -> b t (h d)")
        return self.out(y)

class DecoderBlock(nn.Module):
    def __init__(self, d_model: int, n_heads: int, mlp_mult: int = 4):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = CausalSelfAttention(d_model, n_heads)
        self.ln2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, mlp_mult * d_model),
            nn.GELU(),
            nn.Linear(mlp_mult * d_model, d_model),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x
```

## Why Decoder-Only Models Won Language Modeling

- next-token prediction matches the causal factorization of text
- all positions train in parallel despite the causal constraint
- attention handles long-range dependencies more directly than a recurrent hidden state

The main cost is quadratic attention in sequence length:

$$
O(T^2 d)
$$

for sequence length $T$ and model width $d$.

## Related Notes

- [[ml/deep-learning/encoder-decoder-transformers|Encoder-Decoder Transformers]]
- [[ml/deep-learning/neural-networks-from-scratch|Neural Networks from Scratch]]
- [[ml/serving-systems/transformers|Transformer Architecture and Implementation]]

## Sources

- [Vaswani et al. (2017), Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Radford et al. (2019), Language Models are Unsupervised Multitask Learners](https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf)
- [einops documentation](https://einops.rocks/)
