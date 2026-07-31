---
title: Recommender Systems
category: Recommender Systems
tags:
  - recommender systems
  - retrieval
  - ranking
  - personalization
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Overview of the recommender systems notes, with emphasis on pipeline structure, scaling, and production signals.
---

## Purpose

Recommendation systems are easier to reason about once the pipeline is split into stages. First decide which items are plausible. Then rank the survivors with a richer model. Then learn from what users did. [[ml/recommender-systems/retrieval-and-ranking|Retrieval and ranking]] lays out that structure, and [[ml/recommender-systems/recommender-systems|Recommender Systems]] surveys the main modeling families inside it.

The existing notes are still small, so this section is organized around the backbone ideas rather than around one course or paper. [[ml/recommender-systems/intro-mapreduce-spark|MapReduce and Spark]] explains why large-scale offline feature and training jobs look the way they do, and [[ml/recommender-systems/predicting-clicks-on-ads-at-facebook|Predicting Clicks on Ads at Facebook]] is a production case study.

## Notes

- Pipeline structure: [[ml/recommender-systems/retrieval-and-ranking|retrieval and ranking]]
- Modeling overview: [[ml/recommender-systems/recommender-systems|recommender systems]]
- Data infrastructure: [[ml/recommender-systems/intro-mapreduce-spark|MapReduce and Spark]]
- Production case study: [[ml/recommender-systems/predicting-clicks-on-ads-at-facebook|Predicting Clicks on Ads at Facebook]]
