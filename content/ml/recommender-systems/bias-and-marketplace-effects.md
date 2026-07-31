---
title: Bias, Marketplace Effects, and Counterfactual Evaluation
category: Recommender Systems
tags:
  - recommender systems
  - bias
  - contextual bandits
  - counterfactual evaluation
  - fairness
  - ads
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Why recommender logs are policy-shaped, how exploration and offline policy evaluation work, and why platforms have to care about producer-side exposure as well as user relevance.
sources:
  - title: Li et al. (2010), A Contextual-Bandit Approach to Personalized News Article Recommendation
    url: https://arxiv.org/pdf/1003.0146
    type: paper
  - title: Li et al. (2014), Counterfactual Estimation and Optimization of Click Metrics for Search Engines
    url: https://arxiv.org/pdf/1403.1891
    type: paper
  - title: Chaney, Stewart, and Engelhardt (2018), How Algorithmic Confounding in Recommendation Systems Increases Homogeneity and Decreases Utility
    url: https://arxiv.org/pdf/1710.11214
    type: paper
  - title: Patro et al. (2020), FairRec
    url: https://arxiv.org/pdf/2002.10764
    type: paper
---

## Purpose

Recommendation data is not passive observation. The system decides what people see, and that decision shapes the very labels used for the next training run. This note is about the consequences: selection bias, exploration, offline policy evaluation, and producer-side exposure in two-sided marketplaces.

## Logged Data Is Policy-Shaped

Suppose a platform only shows head items. The logs will contain lots of interactions with head items and very little evidence about the tail. That does not mean the tail is bad. It means the policy rarely exposed it.

This creates a loop:

1. policy chooses exposure
2. exposure determines which labels can be observed
3. observed labels train the next policy

Chaney, Stewart, and Engelhardt study this directly and show that training on already-confounded recommendation data can homogenize behavior without increasing utility.

That is the mental model to keep. Recommendation logs are not a random sample from user preference. They are a sample filtered by yesterday's recommender.

## Biases That Matter in Practice

- **Exposure bias**: unshown items cannot collect positive feedback.
- **Position bias**: higher-ranked items attract more interaction for reasons partly unrelated to relevance.
- **Popularity bias**: already-popular items collect more exposure, which makes them look even better.
- **Selection bias**: the training set overrepresents traffic the current system was already willing to show.

These biases are entangled. Popular items get better positions, better positions generate more clicks, and those clicks train the next model.

## Exploration and Contextual Bandits

The contextual-bandit framing is the clean way to talk about learning under exposure constraints.

At each step:

1. observe a context $x_t$
2. choose an action $a_t$
3. observe reward only for the chosen action

That is exactly the recommender problem on many surfaces. The system sees only the reward of shown items.

Li, Chu, Langford, and Schapire apply this to personalized news recommendation and report a **12.5% click lift** over a context-free bandit baseline on Yahoo! Front Page traffic. The paper also makes a second contribution that matters just as much: offline evaluation is possible when the logging policy randomized enough to give known propensities.

## Counterfactual Evaluation

If the logging policy chooses action $a$ with probability $\pi_0(a \mid x)$, then inverse-propensity weighting estimates the value of a target policy $\pi$ by reweighting logged rewards:

$$
\hat{V}_{\text{IPS}}(\pi) = \frac{1}{n} \sum_{t=1}^{n} \frac{\pi(a_t \mid x_t)}{\pi_0(a_t \mid x_t)} r_t
$$

This is the core trick behind counterfactual evaluation. Logged data can evaluate a policy the system never deployed, as long as the logs contain enough randomized support and the propensities are known.

The 2014 counterfactual evaluation paper argues for exactly this shift. Instead of waiting on serial A/B tests for every model idea, use causal estimators offline to cheaply screen many alternatives first.

The estimator is unbiased in the idealized setting. It is also noisy. If the logging policy almost never took actions the target policy likes, the importance weights explode. That is why randomized data collection is not optional bookkeeping. It is the price of honest offline evaluation.

## Marketplace Effects

Many platforms are not just matching users to content. They are marketplaces. Exposure is economically meaningful for the supplier side:

- sellers on e-commerce platforms
- creators on media platforms
- restaurants on local discovery surfaces
- drivers, hosts, or freelancers on labor platforms

Patro et al. make the point plainly. A customer-centric top-$k$ recommender can create large disparities in producer exposure. That may be unfair to producers, and it may also damage the platform by driving suppliers away or shrinking user choice over time.

This changes the objective. Recommendation is no longer only about user utility. It is also about how a scarce resource, attention, is allocated across the market.

## Producer Fairness Is Not the Same as Relevance

If the platform always serves the highest predicted relevance item, head producers tend to absorb more and more exposure. A marketplace may instead want some mixture of:

- user relevance
- exposure floors
- diversity across suppliers
- long-run ecosystem health

FairRec frames this as a two-sided allocation problem and aims for fairness notions on both sides:

- **MMS-style exposure guarantees** for producers
- **EF1-style fairness** for customers

The algorithm itself is less important here than the framing. Once you admit the platform has multiple stakeholders, single-objective top-$k$ ranking stops looking sufficient.

## What to Measure

A recommender team that ignores this note usually ends up overfitting click metrics. A healthier metric set often includes:

- short-term engagement
- retention or downstream value
- calibration
- exposure concentration
- tail coverage
- creator or seller-side outcomes

None of those replaces A/B tests. They just prevent the offline loop from lying too confidently.

## Related Notes

- [[ml/recommender-systems/ranking-objectives|Ranking Objectives and Implicit Feedback]]
- [[ml/recommender-systems/retrieval-and-ranking|Retrieval and Ranking]]
- [[ml/recommender-systems/predicting-clicks-on-ads-at-facebook|Practical Lessons from Predicting Clicks on Ads at Facebook]]

## Sources

- [Li et al. (2010), A Contextual-Bandit Approach to Personalized News Article Recommendation](https://arxiv.org/pdf/1003.0146)
- [Li et al. (2014), Counterfactual Estimation and Optimization of Click Metrics for Search Engines](https://arxiv.org/pdf/1403.1891)
- [Chaney, Stewart, and Engelhardt (2018), How Algorithmic Confounding in Recommendation Systems Increases Homogeneity and Decreases Utility](https://arxiv.org/pdf/1710.11214)
- [Patro et al. (2020), FairRec](https://arxiv.org/pdf/2002.10764)
