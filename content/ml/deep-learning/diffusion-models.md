---
title: Diffusion Models
category: Deep Learning
tags:
  - deep learning
  - diffusion
  - convolution
  - generative models
  - u-net
  - denoising
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Diffusion models from the forward noising process through the DDPM reverse model, including the variational objective, noise-prediction parameterization, and implementation sketches in NumPy and PyTorch.
sources:
  - title: Ho, Jain, and Abbeel (2020), Denoising Diffusion Probabilistic Models
    url: https://arxiv.org/abs/2006.11239
    type: paper
  - title: Ronneberger, Fischer, and Brox (2015), U-Net
    url: https://arxiv.org/pdf/1505.04597
    type: paper
  - title: einops
    url: https://einops.rocks/
    type: docs
---

## Purpose

Diffusion models are easiest to understand if you separate three layers:

1. a fixed forward process that gradually destroys data with noise
2. a learned reverse process that denoises
3. a training objective that makes denoising equivalent to a tractable regression problem

The DDPM paper is the canonical reference for that setup.

## Forward Process

Start from clean data $x_0$. Define a Markov chain:

$$
q(x_{1:T}\mid x_0) = \prod_{t=1}^{T} q(x_t \mid x_{t-1})
$$

with Gaussian step

$$
q(x_t \mid x_{t-1})
=
\mathcal{N}\left(
x_t;
\sqrt{1-\beta_t}\,x_{t-1},
\beta_t I
\right)
$$

where $\beta_t$ is a variance schedule.

Let

$$
\alpha_t = 1-\beta_t,
\qquad
\bar{\alpha}_t = \prod_{s=1}^{t} \alpha_s
$$

Then DDPM uses the closed form

$$
q(x_t \mid x_0)
=
\mathcal{N}\left(
x_t;
\sqrt{\bar{\alpha}_t}x_0,
(1-\bar{\alpha}_t)I
\right)
$$

which yields the useful sampling identity

$$
x_t
=
\sqrt{\bar{\alpha}_t}x_0
+
\sqrt{1-\bar{\alpha}_t}\,\epsilon,
\qquad
\epsilon \sim \mathcal{N}(0, I)
$$

This is why training can sample arbitrary timesteps directly instead of simulating the entire noising chain every time.

## Variational Objective

The paper starts from the usual variational bound on negative log likelihood:

$$
\mathbb{E}\left[-\log p_\theta(x_0)\right]
\le
\mathbb{E}_q\left[
-\log \frac{p_\theta(x_{0:T})}{q(x_{1:T}\mid x_0)}
\right]
=: L
$$

That objective can be decomposed into timestep-wise terms. The paper's key contribution is not only writing down the bound. It is showing how to parameterize the reverse process so training becomes simple and stable.

## Reverse Process and Noise Prediction

The reverse model is

$$
p_\theta(x_{t-1}\mid x_t)
$$

parameterized as a Gaussian with learned mean. DDPM shows that a particularly convenient approach is to predict the noise $\epsilon$ instead:

$$
\epsilon_\theta(x_t, t)
$$

This leads to the simplified training objective

$$
L_{simple}
=
\mathbb{E}_{t, x_0, \epsilon}
\left[
\left\lVert
\epsilon - \epsilon_\theta(x_t, t)
\right\rVert_2^2
\right]
$$

That is the practical heart of the method. The model is trained as a noise regressor, not as a direct pixel generator.

## Sampling Algorithm

The paper's Algorithm 2 is the reverse-time sampler:

1. start from $x_T \sim \mathcal{N}(0, I)$
2. for $t = T, \dots, 1$, predict noise with $\epsilon_\theta(x_t, t)$
3. form the mean of $p_\theta(x_{t-1}\mid x_t)$
4. add Gaussian noise when $t > 1$

The extracted update in the paper is

$$
x_{t-1}
=
\frac{1}{\sqrt{\alpha_t}}
\left(
x_t - \frac{1-\alpha_t}{\sqrt{1-\bar{\alpha}_t}}
\epsilon_\theta(x_t, t)
\right)
+
\sigma_t z
$$

with $z \sim \mathcal{N}(0, I)$ for $t > 1$.

This explains why diffusion generation is slow. One sample requires many denoising steps.

## Why U-Nets Became the Default Backbone

Image diffusion models need:

- local spatial processing
- large receptive fields
- high-resolution detail preservation
- conditioning on timestep $t$

U-Nets already solve most of that. They combine:

- a contracting path
- an expanding path
- skip connections across scales

So diffusion models inherited a backbone that was already strong for dense image-to-image problems.

## Results from the DDPM Paper

The paper reports:

- **Inception score 9.46** on unconditional CIFAR-10
- **FID 3.17** on unconditional CIFAR-10
- sample quality on **256x256 LSUN** similar to ProgressiveGAN

The paper also argues that diffusion admits a progressive lossy decompression view, which is a useful intuition: early reverse steps recover coarse structure, later ones add detail.

## NumPy Schedule and Noising Step

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

## PyTorch Noise-Predictor Sketch

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
        freqs = torch.exp(-math.log(10000) * torch.arange(half, device=t.device) / half)
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

The point here is the parameterization. The model takes $(x_t, t)$ and predicts the noise.

## Related Notes

- [[ml/deep-learning/convolutional-neural-networks|Convolutional Neural Networks]]
- [[ml/deep-learning/modeling-architecture-and-data|Modeling, Architecture, and Data]]

## Sources

- [Ho, Jain, and Abbeel (2020), Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239)
- [Ronneberger, Fischer, and Brox (2015), U-Net](https://arxiv.org/pdf/1505.04597)
- [einops documentation](https://einops.rocks/)
