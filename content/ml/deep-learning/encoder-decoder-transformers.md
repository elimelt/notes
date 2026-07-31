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
description: The original transformer architecture, including encoder and decoder stacks, cross-attention, positional encoding, optimization details, and sequence-to-sequence training.
sources:
  - title: Vaswani et al. (2017), Attention Is All You Need
    url: https://arxiv.org/abs/1706.03762
    type: paper
  - title: Bahdanau, Cho, and Bengio (2014), Neural Machine Translation by Jointly Learning to Align and Translate
    url: https://arxiv.org/abs/1409.0473
    type: paper
  - title: einops
    url: https://einops.rocks/
    type: docs
---

## Purpose

The original transformer was a sequence-to-sequence model, not a decoder-only language model. This note covers that original shape and the main idea that distinguishes it from plain self-attention stacks: cross-attention from the decoder into a separately encoded source sequence.

## What Problem It Solves

Given source tokens $x_{1:S}$ and target tokens $y_{1:T}$, model

$$
p(y_{1:T} \mid x_{1:S}) = \prod_{t=1}^{T} p(y_t \mid y_{<t}, x_{1:S})
$$

This factorization says:

- the full source sequence is available
- the target is generated autoregressively
- each target step can condition on the whole source

That is exactly the structure of translation and many other transduction tasks.

## Why Bahdanau Attention Matters Here

Before transformers, Bahdanau, Cho, and Bengio argued that the plain encoder-decoder architecture suffered from a fixed-length bottleneck. Their fix was to let the decoder form a context vector by softly attending over source annotations:

$$
c_i = \sum_{j=1}^{T_x} \alpha_{ij} h_j
$$

with

$$
\alpha_{ij} = \frac{\exp(e_{ij})}{\sum_{k=1}^{T_x}\exp(e_{ik})},
\qquad
e_{ij} = a(s_{i-1}, h_j)
$$

The transformer inherits this idea and replaces recurrence with attention blocks.

## The Original Transformer Architecture

Vaswani et al. use:

- **$N = 6$** encoder layers
- **$N = 6$** decoder layers
- **$d_{model} = 512$**
- **$d_{ff} = 2048$**
- **$h = 8$** attention heads
- dropout rate **0.1**

These numbers define the base model. The "big" model scales width and head count further.

## Encoder

The encoder stack applies unmasked self-attention followed by a positionwise feed-forward network. In the original post-norm presentation:

$$
\operatorname{EncoderLayer}(x)
=
\operatorname{LayerNorm}\left(x + \operatorname{Sublayer}(x)\right)
$$

where the first sublayer is multi-head self-attention and the second is the feed-forward block.

The feed-forward block is:

$$
\operatorname{FFN}(x) = \max(0, xW_1 + b_1)W_2 + b_2
$$

with input/output dimension $512$ and inner dimension $2048$.

## Decoder

Each decoder layer contains three sublayers:

1. masked self-attention over the target prefix
2. encoder-decoder attention
3. feed-forward network

That middle step is cross-attention.

## Cross-Attention

Cross-attention differs from self-attention only in the origin of $Q$, $K$, and $V$:

- queries come from decoder states
- keys come from encoder states
- values come from encoder states

Formally,

$$
\operatorname{CrossAttn}(Q_{dec}, K_{enc}, V_{enc})
=
\operatorname{softmax}\left(\frac{Q_{dec}K_{enc}^\top}{\sqrt{d_k}}\right)V_{enc}
$$

This is the mechanism that lets target position $t$ align to whichever source positions matter for predicting $y_t$.

## Positional Encoding

Because the transformer has no recurrence and no convolution, order must be injected. The paper uses sinusoidal positional encodings:

$$
\operatorname{PE}(pos, 2i)
=
\sin\left(pos / 10000^{2i/d_{model}}\right)
$$

$$
\operatorname{PE}(pos, 2i+1)
=
\cos\left(pos / 10000^{2i/d_{model}}\right)
$$

These are added to the token embeddings.

## Optimization Details That Matter

The transformer paper is worth reading for the optimizer schedule alone. They use Adam with:

- $\beta_1 = 0.9$
- $\beta_2 = 0.98$
- $\epsilon = 10^{-9}$

and learning rate

$$
\operatorname{lrate}
=
d_{model}^{-0.5}
\min\left(\text{step}^{-0.5}, \text{step} \cdot \text{warmup}^{-1.5}\right)
$$

with **4000 warmup steps**.

They also use **label smoothing** with $\epsilon_{ls} = 0.1$, which the paper says hurts perplexity but improves accuracy and BLEU.

## Experimental Result

The paper reports:

- **28.4 BLEU** on WMT 2014 English-to-German, improving over prior best ensembles by more than 2 BLEU
- **41.8 BLEU** on WMT 2014 English-to-French for a single model
- training of the big English-to-French model in **3.5 days on 8 GPUs**

Those numbers mattered historically because they made the case that attention-only sequence transduction was not just elegant. It was competitive and cheaper to train.

## NumPy Cross-Attention

```python
import numpy as np

def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)

def cross_attention(dec_states, enc_states, Wq, Wk, Wv):
    Q = dec_states @ Wq
    K = enc_states @ Wk
    V = enc_states @ Wv
    scores = Q @ np.swapaxes(K, -1, -2) / np.sqrt(Q.shape[-1])
    probs = softmax(scores, axis=-1)
    return probs @ V
```

## PyTorch Decoder Block with Cross-Attention

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

    def forward(self, q_in, k_in, v_in, causal=False):
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
            nn.ReLU(),
            nn.Linear(4 * d_model, d_model),
        )

    def forward(self, y, enc):
        y = y + self.self_attn(self.ln1(y), self.ln1(y), self.ln1(y), causal=True)
        y = y + self.cross_attn(self.ln2(y), enc, enc, causal=False)
        y = y + self.mlp(self.ln3(y))
        return y
```

## Where Encoder-Decoder Still Wins

- translation
- summarization from a fully observed source
- speech or vision to text
- tasks where source and target have distinct roles

Decoder-only models are simpler. Still, when one sequence is given in full and the other is generated conditioned on it, encoder-decoder structure remains natural.

## Related Notes

- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
- [[ml/deep-learning/recurrent-neural-networks|Recurrent Neural Networks]]

## Sources

- [Vaswani et al. (2017), Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Bahdanau, Cho, and Bengio (2014), Neural Machine Translation by Jointly Learning to Align and Translate](https://arxiv.org/abs/1409.0473)
- [einops documentation](https://einops.rocks/)
