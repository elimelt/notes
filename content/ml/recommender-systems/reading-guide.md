---
title: Recommender Systems Reading Guide
category: Recommender Systems
tags:
  - recommender systems
  - retrieval
  - ranking
  - personalization
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Overview of the recommender systems notes, organized around pipeline stages, objectives, and the papers that shaped modern production systems.
sources:
  - title: Covington, Adams, and Sargin (2016), Deep Neural Networks for YouTube Recommendations
    url: https://research.google.com/pubs/archive/45530.pdf
    type: paper
  - title: Cheng et al. (2016), Wide & Deep Learning for Recommender Systems
    url: https://arxiv.org/pdf/1606.07792
    type: paper
  - title: Hu, Koren, and Volinsky (2008), Collaborative Filtering for Implicit Feedback Datasets
    url: https://yifanhu.net/PUB/cf.pdf
    type: paper
---

## Purpose

These notes are organized around the shape that most production recommenders eventually take. First define the objective. Then retrieve a tractable candidate set. Then rank those candidates with a richer model. Then measure what happened without lying to yourself about feedback loops. The section is built around that order.

## Reading Path

If I wanted to rebuild the area from scratch, I would read it in this order:

1. [[ml/recommender-systems/recommender-systems|Recommender Systems]]
2. [[ml/recommender-systems/ranking-objectives|Ranking Objectives and Implicit Feedback]]
3. [[ml/recommender-systems/retrieval-and-ranking|Retrieval and Ranking]]
4. [[ml/recommender-systems/two-tower-retrieval|Two-Tower Retrieval]]
5. [[ml/recommender-systems/wide-and-deep|Wide and Deep]]
6. [[ml/recommender-systems/sequential-recommendation|Sequential and Graph Recommenders]]
7. [[ml/recommender-systems/bias-and-marketplace-effects|Bias, Marketplace Effects, and Counterfactual Evaluation]]

After that, the paper notes land better:

- [[ml/recommender-systems/deep-neural-networks-for-youtube-recommendations|Deep Neural Networks for YouTube Recommendations]]
- [[ml/recommender-systems/predicting-clicks-on-ads-at-facebook|Practical Lessons from Predicting Clicks on Ads at Facebook]]

## Notes

- Foundations: [[ml/recommender-systems/recommender-systems|recommender systems]]
- Labels and losses: [[ml/recommender-systems/ranking-objectives|ranking objectives and implicit feedback]]
- Pipeline shape: [[ml/recommender-systems/retrieval-and-ranking|retrieval and ranking]]
- Retrieval architecture: [[ml/recommender-systems/two-tower-retrieval|two-tower retrieval]]
- Retrieval experiment: [[ml/recommender-systems/movielens-100k-two-tower-retrieval|MovieLens 100K two-tower retrieval]]
- Ranking architecture: [[ml/recommender-systems/wide-and-deep|wide and deep]]
- Temporal and structural signals: [[ml/recommender-systems/sequential-recommendation|sequential and graph recommenders]]
- Evaluation and ecosystem effects: [[ml/recommender-systems/bias-and-marketplace-effects|bias, marketplace effects, and counterfactual evaluation]]
- Data infrastructure: [[ml/recommender-systems/intro-mapreduce-spark|MapReduce and Spark]]
- Production case studies:
  - [[ml/recommender-systems/deep-neural-networks-for-youtube-recommendations|YouTube recommendations]]
  - [[ml/recommender-systems/predicting-clicks-on-ads-at-facebook|Facebook ads CTR]]

## Related notes

- [[recc-sys/movielens-100k-two-tower-retrieval|MovieLens 100K Two-Tower Retrieval]]

## Sources

- [Covington, Adams, and Sargin (2016), Deep Neural Networks for YouTube Recommendations](https://research.google.com/pubs/archive/45530.pdf)
- [Cheng et al. (2016), Wide & Deep Learning for Recommender Systems](https://arxiv.org/pdf/1606.07792)
- [Hu, Koren, and Volinsky (2008), Collaborative Filtering for Implicit Feedback Datasets](https://yifanhu.net/PUB/cf.pdf)
