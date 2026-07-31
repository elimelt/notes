---
title: Recurrent Neural Networks
category: Deep Learning
tags:
  - deep learning
  - rnn
  - lstm
  - gru
  - sequence modeling
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Recurrent neural networks from the recurrence equation upward, including backpropagation through time, the vanishing-gradient problem, and LSTM/GRU implementations in NumPy and PyTorch.
sources:
  - title: Elman (1990), Finding Structure in Time
    url: https://papers.baulab.info/papers/Elman-1990.pdf
    type: paper
  - title: Hochreiter and Schmidhuber (1997), Long Short-Term Memory
    url: https://deeplearning.cs.cmu.edu/S23/document/readings/LSTM.pdf
    type: paper
  - title: Bahdanau, Cho, and Bengio (2014), Neural Machine Translation by Jointly Learning to Align and Translate
    url: https://arxiv.org/abs/1409.0473
    type: paper
---

## Purpose

RNNs were the standard way to model sequences before transformers took over most large-scale language work. They still matter because they expose the core problem in sequence modeling: state has to flow through time, and so do gradients.

## Vanilla RNN

At time step $t$, with input $x_t$ and hidden state $h_{t-1}$:

$$
h_t = \phi(W_{xh}x_t + W_{hh}h_{t-1} + b_h)
$$

and, for output logits,

$$
o_t = W_{hy} h_t + b_y
$$

The same parameters are reused at every time step. That is the key inductive bias: time-shifted reuse of the same transition.

## Unrolling Through Time

An RNN can be seen as a deep network whose depth is the sequence length:

$$
h_t = f_t(h_{t-1})
$$

Backpropagation through time differentiates through all these copies of the recurrence.

For a loss $\mathcal{L} = \sum_t \mathcal{L}_t$, the gradient to an early hidden state contains products of Jacobians:

$$
\frac{\partial \mathcal{L}}{\partial h_t}
= \sum_{k \ge t} \frac{\partial \mathcal{L}_k}{\partial h_k}
\prod_{j=t+1}^{k} \frac{\partial h_j}{\partial h_{j-1}}
$$

That product is the problem. If the recurrent Jacobian tends to have singular values below $1$, gradients vanish. If above $1$, they explode.

## Why LSTMs Help

LSTMs create a path where error can flow more directly.

One common form is:

$$
\begin{aligned}
f_t &= \sigma(W_f [h_{t-1}; x_t] + b_f) \\
i_t &= \sigma(W_i [h_{t-1}; x_t] + b_i) \\
\tilde{c}_t &= \tanh(W_c [h_{t-1}; x_t] + b_c) \\
c_t &= f_t \odot c_{t-1} + i_t \odot \tilde{c}_t \\
o_t &= \sigma(W_o [h_{t-1}; x_t] + b_o) \\
h_t &= o_t \odot \tanh(c_t)
\end{aligned}
$$

The cell state $c_t$ is the important part. If $f_t \approx 1$ and $i_t \approx 0$, information can persist with much less distortion than in a vanilla recurrence.

## GRUs

GRUs compress the gating story:

$$
\begin{aligned}
z_t &= \sigma(W_z x_t + U_z h_{t-1}) \\
r_t &= \sigma(W_r x_t + U_r h_{t-1}) \\
\tilde{h}_t &= \tanh(W_h x_t + U_h(r_t \odot h_{t-1})) \\
h_t &= (1 - z_t)\odot h_{t-1} + z_t \odot \tilde{h}_t
\end{aligned}
$$

They are simpler than LSTMs and often competitive.

## NumPy RNN Cell

```python
import numpy as np

def tanh(x):
    return np.tanh(x)

class VanillaRNN:
    def __init__(self, d_in, d_hidden, d_out, seed=0):
        rng = np.random.default_rng(seed)
        self.Wxh = rng.normal(0, 0.1, size=(d_hidden, d_in))
        self.Whh = rng.normal(0, 0.1, size=(d_hidden, d_hidden))
        self.bh = np.zeros(d_hidden)
        self.Why = rng.normal(0, 0.1, size=(d_out, d_hidden))
        self.by = np.zeros(d_out)

    def step(self, x_t, h_prev):
        h_t = tanh(x_t @ self.Wxh.T + h_prev @ self.Whh.T + self.bh)
        o_t = h_t @ self.Why.T + self.by
        return h_t, o_t

    def forward(self, x):
        # x: (B, T, D)
        B, T, _ = x.shape
        h = np.zeros((B, self.Whh.shape[0]))
        outputs = []
        for t in range(T):
            h, o = self.step(x[:, t], h)
            outputs.append(o)
        return np.stack(outputs, axis=1)
```

## PyTorch LSTM Language Model

```python
import torch
import torch.nn as nn

class LSTMLM(nn.Module):
    def __init__(self, vocab_size: int, d_model: int, n_layers: int = 2):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, d_model)
        self.rnn = nn.LSTM(
            input_size=d_model,
            hidden_size=d_model,
            num_layers=n_layers,
            batch_first=True,
        )
        self.lm_head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        x = self.embed(token_ids)
        h, _ = self.rnn(x)
        return self.lm_head(h)
```

## Where RNNs Still Make Sense

- low-latency streaming settings
- small or medium sequence lengths
- domains where strict online recurrence is natural

Their main weakness is that the hidden state is a fixed-width summary. Attention-based models route information more flexibly.

## Related Notes

- [[ml/deep-learning/encoder-decoder-transformers|Encoder-Decoder Transformers]]
- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]

## Sources

- [Elman (1990), Finding Structure in Time](https://papers.baulab.info/papers/Elman-1990.pdf)
- [Hochreiter and Schmidhuber (1997), Long Short-Term Memory](https://deeplearning.cs.cmu.edu/S23/document/readings/LSTM.pdf)
- [Bahdanau, Cho, and Bengio (2014), Neural Machine Translation by Jointly Learning to Align and Translate](https://arxiv.org/abs/1409.0473)
