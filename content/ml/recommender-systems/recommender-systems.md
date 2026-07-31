---
title: Recommender Systems
aliases:
  - recc-sys/reccomender-systems
category: Recommender Systems
tags:
  - recommender systems
  - collaborative filtering
  - matrix factorization
  - matrix completion
  - personalization
  - cold-start problem
date: 2025-04-27
updated: 2026-07-30
status: draft
description: Overview of recommender system approaches, from popularity and co-occurrence baselines through matrix factorization and featurized models that handle cold start.
sources:
  - title: Koren, Bell & Volinsky (2009), Matrix Factorization Techniques for Recommender Systems
    url: https://doi.org/10.1109/MC.2009.263
    type: paper
---

## Purpose

Maps the main approaches to recommendation and the tradeoffs between them, with matrix factorization as the centerpiece. For a production ranking case study, see [[ml/recommender-systems/predicting-clicks-on-ads-at-facebook|Predicting Clicks on Ads at Facebook]]; the data scale involved motivates [[ml/recommender-systems/intro-mapreduce-spark|distributed data-mining techniques]].

## The problem

Personalization uses what we know about a user (preferences, activity) to recommend items they might like. The core difficulty is sparsity. Most users interact with a tiny fraction of the catalog, so the user-item interaction matrix is mostly empty. Collaborative filtering bets that users enjoy items liked by similar users, which lets data about many users compensate for the missing data about any one of them.

Feedback comes in two forms. Explicit feedback means ratings, purchase history, and rankings. Implicit feedback means browsing history, clicks, and time spent, and it needs preprocessing before it looks like a preference signal.

Beyond sparsity, the recurring challenges are:

- Cold start: hard to recommend for new users or items with no history.
- Changing interests: user preferences and item popularity shift over time.
- Scalability: the algorithms have to handle millions of users and items.

## Baseline approaches

**Popularity-based** recommendation serves everyone the most popular items. It ignores the user entirely, so there is no personalization, and it handles new users fine.

**Classifier-based** recommendation treats the task as classification. The input $x$ is a vector of user and item features, and the output is $y = +1$ (like) or $-1$ (dislike). This personalizes and can fold in arbitrary extra features, but it leans on feature engineering, which is hard to get right. On the Netflix Prize data, latent factor methods learned directly from interactions outperformed the classic alternatives ([Koren et al. 2009](https://doi.org/10.1109/MC.2009.263)).

**Co-occurrence-based** recommendation uses a normalized co-occurrence matrix $C$:

$$
C_{ij} = \frac{\text{users who bought both } i \text{ and } j}{\text{users who bought } i \text{ or } j}
$$

For a user who bought items $A$ and $B$, the score for item $X$ averages the co-occurrence with each purchase:

$$
\text{Score}(X) = \frac{C_{XA} + C_{XB}}{2}
$$

## Matrix factorization and completion

Represent user $u$ and item $v$ with $k$-dimensional feature vectors $L_u$ and $R_v$, and predict the rating as their inner product:

$$
\text{Rating}(u, v) = L_u^T R_v
$$

The full ratings matrix $M$ is approximated by $M \approx L R^T$. Since $L$ has $mk$ entries and $R$ has $nk$ (for $m$ items, $n$ users, $k$ topics), the model has

$$
\text{Degrees of freedom} = k(m + n)
$$

parameters, far fewer than the $mn$ entries of $M$ when $k$ is small. That gap is what makes it possible to fill in a mostly empty matrix.

Fitting the model is a **matrix completion** problem. Given the observed ratings, find $L$ and $R$ minimizing the squared error on the entries we can see:

$$
\min_{L, R} \sum_{(u,v): r_{uv} \text{ observed}} (L_u^T R_v - r_{uv})^2
$$

**Coordinate descent** works well here. Alternately fix $R$ and optimize $L$, then fix $L$ and optimize $R$. With one side fixed, the objective separates, so each step reduces to many independent linear regression problems.

To prevent overfitting, add $\ell_2$ regularization:

$$
\min_{L, R} \sum_{(u,v): r_{uv} \text{ observed}} (L_u^T R_v - r_{uv})^2 + \lambda (\|L_u\|^2 + \|R_v\|^2)
$$

## Extensions and cold start

Matrix factorization has nothing to say about a user or item with no observed ratings. Feature-based models fill that hole.

A **feature-based linear model** represents items by a feature vector $\phi(v)$ and learns global weights $w$:

$$
r_{uv} \approx w \cdot \phi(v)
$$

$$
\min_w \sum_{(u,v): r_{uv} \text{ observed}} (w \cdot \phi(v) - r_{uv})^2 + \lambda \|w\|^2
$$

Personalization comes back through **user-specific deviations** $w_u$:

$$
r_{uv} \approx (w + w_u) \cdot \phi(v)
$$

A new user starts at $w_u = 0$ and just gets the global weights. As their history accumulates, $w_u$ adapts.

**Featurized matrix factorization** combines both models:

$$
r_{uv} \approx L_u \cdot R_v + (w + w_u) \cdot \phi(u, v)
$$

This gets collaborative filtering where interaction data exists and graceful fallback to features where it doesn't, and it can be optimized with coordinate descent or gradient descent.

## Applications

Matrix completion can infer missing entries in distance matrices for localization, exploiting the low-rank structure that spatial constraints impose. Matrix factorization applied to document-word matrices uncovers latent topics, similar to topic modeling.

## Comparison

A coarse comparison of the approaches above. The ratings follow from the model definitions rather than from any single benchmark.

| Approach                | Personalization | Handles Cold-Start | Uses Features | Handles Sparsity | Scalability |
|-------------------------|----------------|--------------------|---------------|------------------|-------------|
| Popularity              | No             | Yes                | No            | Yes              | High        |
| Classifier              | Yes            | Yes                | Yes           | Limited          | Moderate    |
| Co-Occurrence           | Limited        | No                 | No            | Yes              | High        |
| Matrix Factorization    | Yes            | No                 | No            | Yes              | High        |
| Feature-Based Linear    | Yes            | Yes                | Yes           | Yes              | High        |
| Featurized Matrix Fact. | Yes            | Yes                | Yes           | Yes              | Moderate    |

## Sources

- [Koren, Bell & Volinsky (2009), Matrix Factorization Techniques for Recommender Systems](https://doi.org/10.1109/MC.2009.263)

## Related notes

- [[ml/recommender-systems/retrieval-and-ranking|retrieval and ranking]]
- [[ml/recommender-systems/predicting-clicks-on-ads-at-facebook|Predicting Clicks on Ads at Facebook]]
- [[ml/recommender-systems/intro-mapreduce-spark|distributed data-mining techniques]]
