---
title: Practical Lessons from Predicting Clicks on Ads at Facebook
category: Machine Learning Systems
tags:
  - recommender systems
  - machine learning
  - ads
  - Facebook
date: 2025-05-17
updated: 2026-07-30
status: incomplete
description: Notes on the paper "Practical Lessons from Predicting Clicks on Ads at Facebook". Covers the ranking system context and the normalized entropy metric; the paper's main modeling results are not summarized yet.
sources:
  - title: He et al. (2014), Practical Lessons from Predicting Clicks on Ads at Facebook
    url: https://research.facebook.com/file/273183074306353/practical-lessons-from-predicting-clicks-on-ads-at-facebook.pdf
    type: paper
---

## Purpose

Reading notes on He et al.'s ads click prediction paper. So far this covers the system context and the normalized entropy metric the paper evaluates with. The paper's central modeling result, using boosted decision trees to transform features for a linear model, along with its findings on data freshness and online learning, still needs a writeup. This case study is a production example of the objectives and modeling approaches introduced in [[recc-sys/reccomender-systems|Recommender Systems]].

> Disclaimer: This is not affiliated with my work at Meta. This paper is publicly available at https://research.facebook.com/file/273183074306353/practical-lessons-from-predicting-clicks-on-ads-at-facebook.pdf

## Citation

- [Practical Lessons from Predicting Clicks on Ads at Facebook (He et al., ADKDD 2014)](https://research.facebook.com/file/273183074306353/practical-lessons-from-predicting-clicks-on-ads-at-facebook.pdf)

## Background

The overall ads system has two main components, **ranking** and **bidding**. Ranking is performed by a series of models that increase in complexity and cost as they progress through the pipeline, progressively filtering out the majority of ads, since most are not relevant to the user. Then an "auction" determines which ad gets shown, based on the bids from advertisers, i.e. how much they are willing to pay for a click.

The paper focuses on the ranking component, particularly the final layer of the ranking system, where higher accuracy over a smaller candidate set is required.

## Normalized Entropy

Normalized entropy (NE) measures the predictive quality of a model relative to a trivial baseline that always predicts the background CTR, meaning the average CTR of the dataset. It is defined as:

$$
\text{Normalized Entropy} = \frac{H}{H_{\text{max}}}
$$

where $H$ is the average log loss of the model's predictions and $H_{\text{max}}$ is the log loss of the baseline predictor.

Given a dataset labeled $1, \ldots, n$ with outputs $y_i \in \{-1, 1\}$, a background CTR $p$, and predicted click probabilities $p_i$, the model's average log loss is:

$$
H = -\frac{1}{n} \sum_{i=1}^{n} \left( \frac{1 + y_i}{2} \log(p_i) + \frac{1 - y_i}{2} \log(1 - p_i) \right)
$$

The baseline's loss is the entropy of a $\text{Bernoulli}(p)$ variable:

$$
H_{\text{max}} = -(p \log(p) + (1 - p) \log(1 - p))
$$

So the normalized entropy is:

$$
\text{NE} = \frac{-\frac{1}{n} \sum_{i=1}^{n} \left( \frac{1 + y_i}{2} \log(p_i) + \frac{1 - y_i}{2} \log(1 - p_i) \right)}{-(p \log(p) + (1 - p) \log(1 - p))}
$$

The normalization matters because raw log loss is sensitive to the background CTR. When $p$ is close to 0 or 1, even the trivial baseline achieves a small log loss, so a raw log loss number says little on its own. Dividing by the baseline's loss fixes that, and the paper likes the metric for two reasons:

- It is interpretable. NE of 1 means the model does no better than always predicting the average CTR, and anything below 1 beats the baseline.
- It makes models comparable, since normalizing removes the sensitivity to the background CTR.

## Sources

- [He et al. (2014), Practical Lessons from Predicting Clicks on Ads at Facebook](https://research.facebook.com/file/273183074306353/practical-lessons-from-predicting-clicks-on-ads-at-facebook.pdf)
