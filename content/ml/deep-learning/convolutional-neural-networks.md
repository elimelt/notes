---
title: Convolutional Neural Networks
category: Deep Learning
tags:
  - deep learning
  - cnn
  - convolution
  - vision
  - resnet
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Convolutional neural networks from discrete convolution upward, including receptive fields, pooling, residual blocks, and both NumPy and PyTorch implementations.
sources:
  - title: LeCun et al. (1998), Gradient-Based Learning Applied to Document Recognition
    url: https://yann.lecun.com/exdb/publis/pdf/lecun-98.pdf
    type: paper
  - title: Deep Residual Learning for Image Recognition
    url: https://arxiv.org/abs/1512.03385
    type: paper
  - title: U-Net
    url: https://arxiv.org/pdf/1505.04597
    type: paper
---

## Purpose

CNNs encode a strong prior for grid-structured data: nearby pixels interact strongly, and the same local pattern can matter anywhere in the image. That prior shows up as local connectivity and weight sharing.

## Discrete Convolution

For input image $x$ and kernel $K$, a 2D discrete convolution layer computes

$$
y_{i,j} = \sum_{u=0}^{k_h-1} \sum_{v=0}^{k_w-1} K_{u,v} \, x_{i+u, j+v}
$$

Deep-learning libraries usually implement cross-correlation rather than a mathematically flipped convolution, though the learned behavior is the same because the kernel parameters are free.

With $C_{in}$ input channels and $C_{out}$ output channels:

$$
y_{c_{out}, i, j}
= \sum_{c_{in}=1}^{C_{in}} \sum_{u,v} K_{c_{out}, c_{in}, u, v} \, x_{c_{in}, i+u, j+v}
$$

## Why CNNs Work

- **locality**: nearby pixels are more related than distant ones
- **translation equivariance**: shifting the image shifts the feature map
- **parameter sharing**: one kernel is reused everywhere

These assumptions are powerful when the domain really is image-like.

## Stride, Padding, and Receptive Field

Stride reduces spatial resolution. Padding preserves edge information and output size. Stacking layers expands the receptive field. A deep stack of small kernels often works better than one giant kernel because it inserts more nonlinearities and uses fewer parameters.

## Residual Blocks

Deep CNNs are much easier to train with skip connections:

$$
y = x + F(x)
$$

ResNet is the canonical example. Many later image models, even when they are not literally "ResNets," still preserve this residual design logic.

## NumPy Convolution

```python
import numpy as np

def conv2d_single_channel(x, kernel, stride=1, padding=0):
    x = np.pad(x, ((padding, padding), (padding, padding)))
    kh, kw = kernel.shape
    oh = (x.shape[0] - kh) // stride + 1
    ow = (x.shape[1] - kw) // stride + 1
    out = np.zeros((oh, ow), dtype=x.dtype)

    for i in range(oh):
        for j in range(ow):
            patch = x[i * stride:i * stride + kh, j * stride:j * stride + kw]
            out[i, j] = np.sum(patch * kernel)
    return out
```

The important point is not the loops. It is that one small kernel is reused across all spatial positions.

## PyTorch CNN with Residual Block

```python
import torch
import torch.nn as nn
from einops import rearrange

class ResidualBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(channels),
        )
        self.act = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(x + self.net(x))

class SmallCNN(nn.Module):
    def __init__(self, n_classes: int = 10):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        self.block = ResidualBlock(64)
        self.head = nn.Linear(64, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem(x)
        x = self.block(x)
        x = x.mean(dim=(-2, -1))
        return self.head(x)
```

`einops` becomes useful when reshaping patches or mixing spatial and sequence views, though plain CNN code often reads fine without it.

## U-Nets

For dense prediction such as segmentation, classification-style downsampling is not enough. U-Net uses:

- a contracting path for context
- an expanding path for localization
- skip connections between matching resolutions

This encoder-decoder-with-skips pattern later became one of the default backbones for diffusion models.

## Related Notes

- [[ml/deep-learning/diffusion-models|Diffusion Models]]
- [[ml/deep-learning/modeling-architecture-and-data|Modeling, Architecture, and Data]]

## Sources

- [LeCun et al. (1998), Gradient-Based Learning Applied to Document Recognition](https://yann.lecun.com/exdb/publis/pdf/lecun-98.pdf)
- [He et al. (2015), Deep Residual Learning for Image Recognition](https://arxiv.org/abs/1512.03385)
- [Ronneberger, Fischer, and Brox (2015), U-Net](https://arxiv.org/pdf/1505.04597)
