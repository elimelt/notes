---
title: Machine Learning
category: Machine Learning
tags:
  - machine learning
  - nlp
  - recommender systems
  - inference systems
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Map of the machine learning notes, with separate paths for language, recommendation, and inference systems.
---

## Purpose

The machine learning notes split three ways. [[ml/nlp/index|NLP]] covers language representations and textbook modeling ideas. [[ml/recommender-systems/index|Recommender systems]] covers retrieval, ranking, and feedback signals in personalization. [[ml/serving-systems/index|Serving systems]] covers the systems side of large-model inference: kernels, memory, batching, and parallelism.

These areas connect in useful ways. Recommendation pipelines and language systems both end up trading model quality against latency and throughput. Large-model serving leans on the same performance reasoning that shows up in [[systems/performance/index|performance engineering]] and the same hardware constraints that show up in [[hardware/index|hardware notes]].

## Sections

- [[ml/nlp/index|Natural language processing]]
- [[ml/recommender-systems/index|Recommender systems]]
- [[ml/serving-systems/index|Serving systems]]
