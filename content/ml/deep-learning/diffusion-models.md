---
title: Diffusion Models
category: Deep Learning
tags:
  - deep learning
  - diffusion
  - generative models
  - unet
  - denoising
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Diffusion models from the forward noising process through the reverse denoising model, including the DDPM objective and a small implementation sketch with NumPy and PyTorch.
sources:
  - title: Denoising Diffusion Probabilistic Models
    url: https://arxiv.org/abs/2006.11239
    type: paper
  - title: U-Net
    url: https://arxiv.org/pdf/1505.04597
    type: paper
  - title: einops
    url: https://einops.rocks/
    type: docs
---

## Purpose

Diffusion models are generative models that learn to reverse a gradual noising process. The math looks unfamiliar at first, though the core training signal is simple: predict the noise that was added.

## Forward Process

Start from clean data $x_0$. Define a Markov chain that adds Gaussian noise:

$$
q(x_t \mid x_{t-1}) = \mathcal{N}\left(x_t; \sqrt{1-\beta_t}x_{t-1}, \beta_t I\right)
$$

with a variance schedule $\beta_t \in (0,1)$.

Let $\alpha_t = 1-\beta_t$ and $\bar{\alpha}_t = \prod_{s=1}^{t} \alpha_s$. Then the nice closed form is

$$
q(x_t \mid x_0) = \mathcal{N}\left(x_t; \sqrt{\bar{\alpha}_t}x_0, (1-\bar{\alpha}_t)I\right)
$$

which means we can sample any time step directly as

$$
x_t = \sqrt{\bar{\alpha}_t}x_0 + \sqrt{1-\bar{\alpha}_t}\,\epsilon,\qquad \epsilon \sim \mathcal{N}(0, I)
$$

## Reverse Process

The model learns a reverse Markov chain:

$$
p_\theta(x_{t-1} \mid x_t)
$$

Ho, Jain, and Abbeel show that a particularly convenient parameterization is to train a network $\epsilon_\theta(x_t, t)$ to predict the noise $\epsilon$ used to form $x_t$.

The widely used training objective is

$$
\mathcal{L}_{simple} = \mathbb{E}_{t, x_0, \epsilon}
\left[\left\lVert \epsilon - \epsilon_\theta(x_t, t)\right\rVert_2^2\right]
$$

That is the heart of DDPM.

## Why U-Nets Show Up

Image diffusion models need:

- local processing at many resolutions
- a way to preserve fine detail
- conditioning on time step $t$

U-Nets fit that well. They downsample to build large receptive fields, then upsample while mixing back in high-resolution skip features.

## NumPy Schedule and One Denoising Step

```python
import numpy as np

def make_schedule(T, beta_start=1e-4, beta_end=2e-2):
    betas = np.linspace(beta_start, beta_end, T, dtype=np.float32)
    alphas = 1.0 - betas
    alpha_bars = np.cumprod(alphas)
    return betas, alphas, alpha_bars

def q_sample(x0, t, alpha_bars, noise):
    return np.sqrt(alpha_bars[t]) * x0 + np.sqrt(1.0 - alpha_bars[t]) * noise

def predict_x0_from_eps(xt, t, eps_hat, alpha_bars):
    return (xt - np.sqrt(1.0 - alpha_bars[t]) * eps_hat) / np.sqrt(alpha_bars[t])
```

This is enough to see the mechanism. Training repeatedly samples random $t$, noises a clean example to $x_t$, and asks the network to recover the injected noise.

## PyTorch Noise-Prediction Skeleton

```python
import math
import torch
import torch.nn as nn
from einops import rearrange

class TimeEmbedding(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        half = self.dim // 2
        freqs = torch.exp(
            -math.log(10000) * torch.arange(half, device=t.device) / half
        )
        args = t[:, None].float() * freqs[None]
        return torch.cat([args.sin(), args.cos()], dim=-1)

class ConvBlock(nn.Module):
    def __init__(self, cin: int, cout: int, tdim: int):
        super().__init__()
        self.conv1 = nn.Conv2d(cin, cout, 3, padding=1)
        self.conv2 = nn.Conv2d(cout, cout, 3, padding=1)
        self.time_proj = nn.Linear(tdim, cout)
        self.act = nn.SiLU()

    def forward(self, x, t_emb):
        h = self.act(self.conv1(x))
        h = h + rearrange(self.time_proj(t_emb), "b c -> b c 1 1")
        h = self.act(self.conv2(h))
        return h

class TinyDenoiser(nn.Module):
    def __init__(self, channels: int = 64, tdim: int = 128):
        super().__init__()
        self.time = TimeEmbedding(tdim)
        self.in_block = ConvBlock(3, channels, tdim)
        self.out = nn.Conv2d(channels, 3, 1)

    def forward(self, x_t: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        t_emb = self.time(t)
        h = self.in_block(x_t, t_emb)
        return self.out(h)
```

A production diffusion U-Net is much larger and multi-scale. The note-worthy part is that the network predicts noise, not pixels directly.

## Sampling

Sampling starts from Gaussian noise $x_T \sim \mathcal{N}(0, I)$ and iteratively applies the learned reverse transitions until reaching $x_0$.

This is why diffusion generation is slower than one-shot generators: it spends many denoising steps to produce one sample.

## Related Notes

- [[ml/deep-learning/convolutional-neural-networks|Convolutional Neural Networks]]
- [[ml/deep-learning/modeling-architecture-and-data|Modeling, Architecture, and Data]]

## Sources

- [Ho, Jain, and Abbeel (2020), Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239)
- [Ronneberger, Fischer, and Brox (2015), U-Net](https://arxiv.org/pdf/1505.04597)
- [einops documentation](https://einops.rocks/)
