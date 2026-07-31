---
title: Recommender Systems
aliases:
  - recc-sys/reccomender-systems
category: Recommender Systems
tags:
  - recommender systems
  - collaborative filtering
  - matrix factorization
  - personalization
  - ranking
date: 2025-04-27
updated: 2026-07-31
status: evergreen
description: A first-principles map of recommender systems, from simple baselines through latent-factor models and the multi-stage production pipelines used at scale.
sources:
  - title: Koren, Bell, and Volinsky (2009), Matrix Factorization Techniques for Recommender Systems
    url: https://doi.org/10.1109/MC.2009.263
    type: paper
  - title: Hu, Koren, and Volinsky (2008), Collaborative Filtering for Implicit Feedback Datasets
    url: https://yifanhu.net/PUB/cf.pdf
    type: paper
  - title: Rendle et al. (2009), BPR
    url: https://arxiv.org/pdf/1205.2618
    type: paper
---

## Purpose

This note is the top-level map. It is not trying to catalog every model family. It is trying to pin down the parts that keep recurring when recommendation systems are rebuilt in practice: sparse supervision, latent structure, pipeline decomposition, and the mismatch between offline logs and online behavior.

## The Core Problem

A recommender has a user, a catalog, and a decision rule for exposure. The simplest version asks:

> given user $u$, which items $i$ should appear near the top of the list?

That question hides most of the difficulty.

- Users touch only a tiny fraction of the catalog.
- Missing interactions are ambiguous.
- Preferences drift.
- Exposure itself changes the future data.

So the training table is sparse, policy-shaped, and nonstationary from the start.

## Signals: Explicit Versus Implicit

Two kinds of feedback show up over and over.

### Explicit Feedback

Ratings, thumbs-up events, stated preferences. These are direct and usually scarce.

### Implicit Feedback

Clicks, purchases, watches, dwell time, skips. These are abundant and weak. The absence of an interaction does not mean dislike. It often only means "not exposed" or "not now."

That is why [[ml/recommender-systems/ranking-objectives|ranking objectives and implicit feedback]] matters so much. Before choosing a model family, decide what the labels mean.

## Baselines Still Matter

The simplest recommenders often stay in production longer than expected because they are robust and cheap.

- **Popularity**: recommend the most popular items.
- **Recent popularity**: same idea, but with a freshness window.
- **Item-item co-occurrence**: recommend things often consumed with what the user already consumed.

These baselines are blunt, though they answer useful questions. If a new model cannot beat recent popularity in online testing, the modeling story is usually wrong or the evaluation setup is.

## Latent Factor Models

Matrix factorization became the canonical collaborative-filtering model because it turns an enormous sparse table into a lower-dimensional geometric problem.

Represent user $u$ and item $i$ with vectors $x_u, y_i \in \mathbb{R}^k$ and score them with

$$
\hat{r}_{ui} = x_u^\top y_i
$$

That works because user-item interactions often have lower-dimensional structure. Instead of learning an arbitrary score for every pair, the model learns a compact representation of user tastes and item attributes.

For explicit-feedback settings, the standard objective is regularized squared error on observed entries. For implicit-feedback settings, confidence weighting becomes the more natural move:

$$
\min_{x_*, y_*} \sum_{u,i} c_{ui}(p_{ui} - x_u^\top y_i)^2 + \lambda \left(\sum_u \lVert x_u \rVert^2 + \sum_i \lVert y_i \rVert^2 \right)
$$

That is the Hu, Koren, and Volinsky formulation. It does not treat all zeros as equally meaningful.

## Ranking, Not Just Prediction

A lot of recommender work is not truly about estimating ratings. It is about ordering.

That is why pairwise and listwise objectives matter. BPR, RankNet, LambdaRank, and LambdaMART all attack the ranking problem more directly than plain regression. If the product only shows a top-$k$ list, learning the relative order can matter more than absolute calibration.

There is still no universal rule here. Ads systems often need calibrated click probabilities. Media feeds often care more about top-of-list order. Good teams pick the loss based on the downstream consumer of the score.

## The Multi-Stage Pipeline

Once the catalog is large, recommenders almost always become staged systems:

1. retrieve a candidate set
2. rank the candidates with a richer model
3. apply filters or business constraints

This is not optional elegance. It is the computational shape forced by large catalogs and tight latency budgets.

[[ml/recommender-systems/retrieval-and-ranking|Retrieval and Ranking]] explains the split. [[ml/recommender-systems/two-tower-retrieval|Two-Tower Retrieval]] covers the standard retrieval architecture. [[ml/recommender-systems/wide-and-deep|Wide and Deep]] is a ranking-side example of how sparse and dense features get combined once the candidate set is small enough.

## Beyond Bags of Interactions

Basic matrix factorization throws away order and graph structure. Modern recommenders usually try to recover one or both.

- **Sequential models** capture short-horizon intent and recency.
- **Graph models** propagate signal across the user-item interaction graph and related structures.

Those ideas live in [[ml/recommender-systems/sequential-recommendation|Sequential and Graph Recommenders]].

## Evaluation Is Harder Than It Looks

Offline accuracy is useful and routinely misleading.

The training and evaluation logs come from an older policy that already filtered what users saw. That creates exposure bias and feedback loops. A model can look excellent offline by copying the current policy's blind spots. Then it disappoints online.

That is why mature recommender teams invest in:

- randomized logging
- exploration
- counterfactual evaluation
- A/B tests on actual business metrics

[[ml/recommender-systems/bias-and-marketplace-effects|Bias, Marketplace Effects, and Counterfactual Evaluation]] covers this in more detail.

## A Good Mental Model

A production recommender is usually some combination of:

- a retrieval system for recall
- a ranker for precision
- a logging policy that decides what can be learned next
- a marketplace allocator, whether the team admits it or not

The last line matters. Once recommendation controls exposure, it is not merely prediction anymore.

## Related Notes

- [[ml/recommender-systems/ranking-objectives|Ranking Objectives and Implicit Feedback]]
- [[ml/recommender-systems/retrieval-and-ranking|Retrieval and Ranking]]
- [[ml/recommender-systems/sequential-recommendation|Sequential and Graph Recommenders]]
- [[ml/recommender-systems/bias-and-marketplace-effects|Bias, Marketplace Effects, and Counterfactual Evaluation]]

## Sources

- [Koren, Bell, and Volinsky (2009), Matrix Factorization Techniques for Recommender Systems](https://doi.org/10.1109/MC.2009.263)
- [Hu, Koren, and Volinsky (2008), Collaborative Filtering for Implicit Feedback Datasets](https://yifanhu.net/PUB/cf.pdf)
- [Rendle et al. (2009), BPR: Bayesian Personalized Ranking from Implicit Feedback](https://arxiv.org/pdf/1205.2618)
