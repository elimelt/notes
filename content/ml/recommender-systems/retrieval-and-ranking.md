---
title: Retrieval and Ranking
category: Recommender Systems
tags:
  - recommender systems
  - retrieval
  - ranking
  - candidate generation
  - ads
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Why large recommender systems split into candidate generation and ranking, and what each stage is trying to optimize.
---

## Purpose

This note gives the backbone shape of a modern recommender system. It is the piece that the more specific notes hang from.

## Why the pipeline splits

A production recommender rarely scores every item with its richest model. The catalog is too large and the latency budget is too small. Instead the system uses a cheap stage to pull back a small candidate set, then a more expensive stage to sort those candidates well.

You can think of the split as a resource allocation problem. If the catalog has $N$ items and the ranking model costs $c_r$ per item, full scoring costs $N c_r$. If retrieval keeps only $k \ll N$ items, the expensive stage costs $k c_r$ instead. That trade is what makes richer ranking models feasible.

## Retrieval

Retrieval is a recall-heavy stage. The goal is not to order items perfectly. The goal is to avoid throwing away good items before ranking sees them.

Common retrieval sources:

- collaborative signals such as similar users or similar items
- content-based matches from item and user features
- heuristic buckets such as recent items, popular items, or items from a followed creator
- approximate nearest-neighbor search over learned embeddings

Each source has a failure mode. Popularity misses niche taste. Content similarity misses cross-category jumps. Pure collaborative filtering struggles with cold start. That is why real systems usually union candidates from several sources.

## Ranking

Ranking is a precision-heavy stage. Once the candidate set is small enough, the model can use richer features: user history, context, freshness, calibration, and business constraints. The target might be click-through rate, watch time, conversion, revenue, or a weighted objective that mixes several of them.

The output is often a score $s(x)$ that orders candidates for the current request context $x$. The score does not need to estimate a perfectly calibrated probability to be useful. It needs to induce the right ordering under the chosen objective.

## Feedback loops

Recommendation changes the data it later trains on. If a system never shows certain items, it never learns who wanted them. Logging, exploration, and counterfactual evaluation matter because the observed labels come from a policy that already filtered the world.

## Related notes

- [[ml/recommender-systems/recommender-systems|Recommender Systems]]
- [[ml/recommender-systems/predicting-clicks-on-ads-at-facebook|Predicting Clicks on Ads at Facebook]]
- [[ml/recommender-systems/intro-mapreduce-spark|MapReduce and Spark]]
