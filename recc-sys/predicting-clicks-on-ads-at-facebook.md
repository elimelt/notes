---
title: Practical Lessons from Predicting Clicks on Ads at Facebook
category: Machine Learning Systems
tags: recommender systems, machine learning, ads, Facebook
description: A review/summary of the paper "Practical Lessons from Predicting Clicks on Ads at Facebook", covering foundational concepts of ads modeling/ranking systems.
---

# Practical Lessons from Predicting Clicks on Ads at Facebook

> Disclaimer: This is not affiliated with my work at Meta. This paper is publicly available at https://research.facebook.com/file/273183074306353/practical-lessons-from-predicting-clicks-on-ads-at-facebook.pdf

## Background

The overall ads ranking system is composed of two main components: the **ranking** and **bidding**. Ranking is performed by a series of models that increase in complexity and cost as they progress through the pipeline, progressively filtering out the majority of ads, since most are not relevant to the user. Then, an "auction" is performed to determine which ad will be shown to the user based on the bids from advertisers, e.g. how much they are willing to pay for a click.

This paper is primarily focused on the ranking component, particularly the final layer of the ranking system where higher accuracy over a smaller dataset is required.

## Normalized Entropy

Normalized entropy is used to measure the discriminative power of a model. It is defined as:

$$
\text{Normalized Entropy} = \frac{H}{H_{\text{max}}}
$$

Where $H$ is the entropy of the model and $H_{\text{max}}$ is the maximum possible entropy, e.g. the average CTR of the dataset.

Given a dataset labeled $1, \ldots, n$ with outputs $y_i \in \{-1, 1\}$, with a background CTR $p$ and a predicted click probability $p_i$, the entropy is defined as:

$$
\text{Entropy} = -\frac{1}{n} \sum_{i=1}^{n} \left( \frac{1 + y_i}{2} \log(p_i) + \frac{1 - y_i}{2} \log(1 - p_i) \right)
$$

The maximum possible entropy is given by $Ber(p)$, i.e.:
$$
H_{\text{max}} = -(p \log(p) + (1 - p) \log(1 - p))
$$.

So we have the normalized entropy as:

$$
\text{NE} = \frac{-\frac{1}{n} \sum_{i=1}^{n} \left( \frac{1 + y_i}{2} \log(p_i) + \frac{1 - y_i}{2} \log(1 - p_i) \right)}{-(p \log(p) + (1 - p) \log(1 - p))}
$$

Intuitively, the closer the background CTR is, the easier it is for the model to discriminate. This metric is nice for a few reasons:

- It is interpretable, as 1 means the model is no better than using the average CTR to predict clicks, and anything lower than 1 means the model is performing better than the average CTR.
- It helps compare models, since normalizing makes it insensitive to the background CTR.