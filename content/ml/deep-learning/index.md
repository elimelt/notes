---
title: Deep Learning
category: Deep Learning
tags:
  - deep learning
  - neural networks
  - transformers
  - cnn
  - rnn
  - diffusion
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: A deep-learning track built from first principles, covering neural-network derivations, model-design choices, and the major architecture families.
sources:
  - title: Rumelhart, Hinton, and Williams (1986), Learning Representations by Back-Propagating Errors
    url: https://www.nature.com/articles/323533a0
    type: paper
  - title: Vaswani et al. (2017), Attention Is All You Need
    url: https://arxiv.org/abs/1706.03762
    type: paper
  - title: LeCun et al. (1998), Gradient-Based Learning Applied to Document Recognition
    url: https://yann.lecun.com/exdb/publis/pdf/lecun-98.pdf
    type: paper
  - title: Ho, Jain, and Abbeel (2020), Denoising Diffusion Probabilistic Models
    url: https://arxiv.org/abs/2006.11239
    type: paper
---

## Purpose

These notes treat deep learning as a modeling discipline, not just a list of branded architectures. The section starts with neural networks from first principles, then moves to the design choices that matter before the first training run, then covers the main architecture families that recur across language, vision, sequence modeling, and generative modeling.

The goal is not only to say what each model is. The goal is to make the implementation and the math line up. Most notes include:

- the forward equations
- the backpropagation view or training objective
- a small NumPy implementation that exposes the mechanics
- a more idiomatic PyTorch implementation, often with `einops` for shape clarity

## Reading Path

1. [[ml/deep-learning/neural-networks-from-scratch|Neural Networks from Scratch]]
2. [[ml/deep-learning/modeling-architecture-and-data|Modeling, Architecture, and Data]]
3. [[ml/deep-learning/recurrent-neural-networks|Recurrent Neural Networks]]
4. [[ml/deep-learning/convolutional-neural-networks|Convolutional Neural Networks]]
5. [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
6. [[ml/deep-learning/encoder-decoder-transformers|Encoder-Decoder Transformers]]
7. [[ml/deep-learning/diffusion-models|Diffusion Models]]
8. [[ml/deep-learning/graph-neural-networks|Graph Neural Networks]]

## Notes

- Foundations: [[ml/deep-learning/neural-networks-from-scratch|neural networks from scratch]]
- Design choices: [[ml/deep-learning/modeling-architecture-and-data|modeling, architecture, and data]]
- Sequence models:
  - [[ml/deep-learning/recurrent-neural-networks|recurrent neural networks]]
  - [[ml/deep-learning/decoder-only-transformers|decoder-only transformers]]
  - [[ml/deep-learning/encoder-decoder-transformers|encoder-decoder transformers]]
- Vision and generative models:
  - [[ml/deep-learning/convolutional-neural-networks|convolutional neural networks]]
  - [[ml/deep-learning/diffusion-models|diffusion models]]
- Structured domains: [[ml/deep-learning/graph-neural-networks|graph neural networks]]

## Sources

- [Rumelhart, Hinton, and Williams (1986), Learning Representations by Back-Propagating Errors](https://www.nature.com/articles/323533a0)
- [Vaswani et al. (2017), Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [LeCun et al. (1998), Gradient-Based Learning Applied to Document Recognition](https://yann.lecun.com/exdb/publis/pdf/lecun-98.pdf)
- [Ho, Jain, and Abbeel (2020), Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239)
