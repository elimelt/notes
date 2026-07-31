---
title: Encoder-Decoder Transformers
category: Deep Learning
tags:
  - deep learning
  - transformers
  - cross attention
  - seq2seq
  - translation
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: The encoder-decoder transformer, with separate encoder and decoder stacks, cross-attention, sequence-to-sequence training, and reference implementations in NumPy and PyTorch.
sources:
  - title: Attention Is All You Need
    url: https://arxiv.org/abs/1706.03762
    type: paper
  - title: Neural Machine Translation by Jointly Learning to Align and Translate
    url: https://arxiv.org/abs/1409.0473
    type: paper
  - title: einops
    url: https://einops.rocks/
    type: docs
---

## Purpose

The original transformer was not decoder-only. It was an encoder-decoder model for sequence transduction. This note covers that split and the extra mechanism that makes it useful: cross-attention.

## The Factorization

For source sequence $x_{1:S}$ and target sequence $y_{1:T}$:

$$
p(y_{1:T} \mid x_{1:S}) = \prod_{t=1}^{T} p(y_t \mid y_{<t}, x_{1:S})
$$

The encoder builds a representation of the full source. The decoder autoregressively predicts the target while attending both to earlier target tokens and to the encoded source.

## Encoder Stack

The encoder uses unmasked self-attention because every source token may see every other source token:

$$
\begin{aligned}
H_1 &= X + \text{MHA}(\text{LN}(X)) \\
H_2 &= H_1 + \text{MLP}(\text{LN}(H_1))
\end{aligned}
$$

After several layers, the encoder outputs contextualized source states $E \in \mathbb{R}^{S \times d}$.

## Decoder Stack

The decoder has three sublayers:

1. masked self-attention over target-prefix states
2. cross-attention to encoder states
3. feed-forward network

In pre-norm form:

$$
\begin{aligned}
H_1 &= Y + \text{MaskedMHA}(\text{LN}(Y)) \\
H_2 &= H_1 + \text{CrossAttn}(\text{LN}(H_1), E) \\
H_3 &= H_2 + \text{MLP}(\text{LN}(H_2))
\end{aligned}
$$

## Cross-Attention

Cross-attention differs from self-attention only in where $Q$, $K$, and $V$ come from.

- queries come from the decoder state
- keys and values come from the encoder output

$$
\text{CrossAttn}(Q_{dec}, K_{enc}, V_{enc}) = \text{softmax}\left(\frac{Q_{dec}K_{enc}^\top}{\sqrt{d_k}}\right)V_{enc}
$$

This is the mechanism that lets the decoder align to relevant source positions when predicting each target token.

Bahdanau attention made this alignment idea central. The transformer kept the idea and replaced recurrence with attention stacks.

## NumPy Cross-Attention

```python
import numpy as np

def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)

def cross_attention(dec_states, enc_states, Wq, Wk, Wv):
    # dec_states: (B, T, D), enc_states: (B, S, D)
    Q = dec_states @ Wq
    K = enc_states @ Wk
    V = enc_states @ Wv
    scores = Q @ np.swapaxes(K, -1, -2) / np.sqrt(Q.shape[-1])
    probs = softmax(scores, axis=-1)
    return probs @ V
```

## PyTorch Decoder Layer with Cross-Attention

```python
import torch
import torch.nn as nn
from einops import rearrange

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        assert d_model % n_heads == 0
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.q_proj = nn.Linear(d_model, d_model, bias=False)
        self.k_proj = nn.Linear(d_model, d_model, bias=False)
        self.v_proj = nn.Linear(d_model, d_model, bias=False)
        self.out = nn.Linear(d_model, d_model, bias=False)

    def forward(self, q_in, k_in, v_in, causal: bool = False):
        B, Tq, D = q_in.shape
        Tk = k_in.shape[1]

        q = rearrange(self.q_proj(q_in), "b t (h d) -> b h t d", h=self.n_heads)
        k = rearrange(self.k_proj(k_in), "b t (h d) -> b h t d", h=self.n_heads)
        v = rearrange(self.v_proj(v_in), "b t (h d) -> b h t d", h=self.n_heads)

        scores = torch.matmul(q, k.transpose(-1, -2)) / (self.head_dim ** 0.5)
        if causal:
            mask = torch.triu(torch.ones(Tq, Tk, device=q_in.device, dtype=torch.bool), diagonal=1)
            scores = scores.masked_fill(mask, float("-inf"))
        attn = scores.softmax(dim=-1)
        out = torch.matmul(attn, v)
        out = rearrange(out, "b h t d -> b t (h d)")
        return self.out(out)

class Seq2SeqDecoderBlock(nn.Module):
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.self_attn = MultiHeadAttention(d_model, n_heads)
        self.ln2 = nn.LayerNorm(d_model)
        self.cross_attn = MultiHeadAttention(d_model, n_heads)
        self.ln3 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(),
            nn.Linear(4 * d_model, d_model),
        )

    def forward(self, y, enc):
        y = y + self.self_attn(self.ln1(y), self.ln1(y), self.ln1(y), causal=True)
        y = y + self.cross_attn(self.ln2(y), enc, enc, causal=False)
        y = y + self.mlp(self.ln3(y))
        return y
```

## Training

Sequence-to-sequence training usually shifts the target by one token:

- decoder input: `<bos>, y_1, \dots, y_{T-1}`
- prediction target: `y_1, \dots, y_T`

Teacher forcing keeps training parallel across target positions, even though inference is autoregressive.

## When Encoder-Decoder Still Wins

Decoder-only models are simpler. Still, encoder-decoder designs remain attractive when:

- the input and output have distinct roles
- the source is fully observed before generation starts
- cross-attention is a clean structural prior

That includes translation, summarization, and many speech or vision-to-text settings.

## Related Notes

- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
- [[ml/deep-learning/recurrent-neural-networks|Recurrent Neural Networks]]

## Sources

- [Vaswani et al. (2017), Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Bahdanau, Cho, and Bengio (2014), Neural Machine Translation by Jointly Learning to Align and Translate](https://arxiv.org/abs/1409.0473)
- [einops documentation](https://einops.rocks/)
