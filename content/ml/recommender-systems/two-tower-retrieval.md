---
title: Two-Tower Retrieval
category: Recommender Systems
tags:
  - recommender systems
  - retrieval
  - two-tower
  - embeddings
  - ann
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Why two-tower retrieval became the default first-stage architecture for large recommenders, how it is trained, and what it gives up in exchange for fast approximate nearest-neighbor serving.
sources:
  - title: Covington, Adams, and Sargin (2016), Deep Neural Networks for YouTube Recommendations
    url: https://research.google.com/pubs/archive/45530.pdf
    type: paper
  - title: Huang et al. (2013), Learning Deep Structured Semantic Models for Web Search using Clickthrough Data
    url: https://dl.acm.org/doi/10.1145/2505515.2505665
    type: paper
---

## Purpose

Two-tower retrieval is the workhorse first stage in large recommendation systems. One tower encodes the user or query. The other encodes the item. The score is usually a dot product. That sounds restrictive. It is restrictive. The reason people use it anyway is that the restriction buys a serving path that scales.

## The Basic Form

Let $f(u)$ be the user embedding and $g(i)$ the item embedding. Retrieval uses

$$
s(u,i) = f(u)^\top g(i)
$$

or a nearby similarity such as cosine similarity.

At training time, both towers are learned jointly from historical interactions. At serving time, item embeddings are precomputed and indexed. A request only has to:

1. build the user embedding
2. query an ANN index
3. return the top $k$ items

That turns catalog-sized search into sublinear nearest-neighbor search.

## Why It Became the Default

The main gain is decomposition. The user and item encoders can be evaluated separately. Since the item tower is offline, online retrieval costs almost nothing beyond user encoding and ANN lookup.

That is the key systems trade:

- richer cross-feature interactions are sacrificed
- catalog-scale retrieval becomes feasible

If the item tower had to read user features at scoring time, or the user tower had to read item features for every candidate, the whole trick would collapse.

## Training

There are two common training views, and they are closer than they look.

### Softmax View

The YouTube paper frames candidate generation as multiclass classification over the video vocabulary. The model predicts which next item the user will consume, usually with sampled softmax because the full catalog is too large.

### Contrastive View

The same setup can be read as contrastive learning. Given a positive pair $(u,i^+)$ and sampled negatives $\{i^-\}$, make the positive item's dot product larger than the negatives'.

In both cases the model learns an embedding space where relevant items sit near the user vector.

## Feature Design

The user tower often absorbs:

- recent interactions
- search queries
- demographics or locale
- device and temporal context

The item tower often absorbs:

- item ID
- metadata
- text
- image or audio features
- creator or taxonomy information

The tension is always the same. The more context you want in the score, the more pressure there is to break the tower decomposition. Once you break it too much, retrieval stops being cheap.

## What It Gives Up

Two-tower models cannot express arbitrary user-item feature crosses at retrieval time. The score is bottlenecked through the embedding dimension and the similarity function. That means:

- memorized exception rules are hard
- calibration is usually poor
- business constraints are awkward to encode directly
- exposure balancing and multi-objective tradeoffs are usually deferred to later stages

This is why first-stage retrieval and final ranking are almost never the same model.

## Hard Negatives Matter

A weak negative sampler teaches the model only coarse separation. The embeddings become good at telling a watched item from random catalog junk, while still failing to separate one plausible item from another plausible item.

The common fix is to train with harder negatives:

- in-batch negatives
- co-exposed but skipped items
- items retrieved by a previous model and rejected downstream
- semantically close items

The downside is that very hard negatives can become false negatives. You can end up pushing apart items the user would have liked if they had seen them.

## How It Fits the Pipeline

Two-tower retrieval is usually not asked to produce the final order. Its job is recall. A good retrieval stage finds most of the items the ranker would have wanted, while staying inside the latency budget.

That changes how you judge it. Absolute calibration barely matters here. Candidate recall, diversity of candidate sources, and tail coverage matter a lot more.

## When Not to Use It

Do not force a two-tower model into places where the business needs rich slate-level reasoning or precise feature interactions. If the catalog is small enough to score directly with a richer model, or if every decision depends on inventory, auction dynamics, or complex constraints, the tower decomposition may cost more than it saves.

## Related Notes

- [[ml/recommender-systems/retrieval-and-ranking|Retrieval and Ranking]]
- [[ml/recommender-systems/deep-neural-networks-for-youtube-recommendations|Deep Neural Networks for YouTube Recommendations]]
- [[ml/recommender-systems/wide-and-deep|Wide and Deep]]

## Sources

- [Covington, Adams, and Sargin (2016), Deep Neural Networks for YouTube Recommendations](https://research.google.com/pubs/archive/45530.pdf)
- [Huang et al. (2013), Learning Deep Structured Semantic Models for Web Search using Clickthrough Data](https://dl.acm.org/doi/10.1145/2505515.2505665)
