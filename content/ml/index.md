---
title: Machine Learning
category: Machine Learning
tags:
  - machine learning
  - deep learning
  - nlp
  - recommender systems
  - inference systems
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Map of the machine learning notes, with separate paths for deep learning, language, recommendation, and serving systems.
sources:
  - title: Attention Is All You Need
    url: https://arxiv.org/abs/1706.03762
    type: paper
  - title: Deep Residual Learning for Image Recognition
    url: https://arxiv.org/abs/1512.03385
    type: paper
---

## Purpose

The machine learning notes now split four ways. [[ml/deep-learning/index|Deep learning]] covers neural networks from first principles and the main architecture families. [[ml/nlp/index|NLP]] covers language representations and textbook modeling ideas. [[ml/recommender-systems/index|Recommender systems]] covers retrieval, ranking, and feedback signals in personalization. [[ml/serving-systems/index|Serving systems]] covers the systems side of large-model inference: kernels, memory, batching, and parallelism.

These areas connect in useful ways. Deep-learning architecture choices shape what later NLP and recommender models can express, and serving constraints push back on those architecture choices. Large-model serving leans on the same performance reasoning that shows up in [[systems/performance/index|performance engineering]] and the same hardware constraints that show up in [[hardware/index|hardware notes]].

## Sections

- [[ml/deep-learning/index|Deep learning]]
- [[ml/nlp/index|Natural language processing]]
- [[ml/recommender-systems/index|Recommender systems]]
- [[ml/serving-systems/index|Serving systems]]

## Sources

- [Vaswani et al. (2017), Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [He et al. (2015), Deep Residual Learning for Image Recognition](https://arxiv.org/abs/1512.03385)
