---
title: Practical Lessons from Predicting Clicks on Ads at Facebook
aliases:
  - recc-sys/predicting-clicks-on-ads-at-facebook
category: Recommender Systems
tags:
  - recommender systems
  - machine-learning
  - ads
  - ctr prediction
  - gradient boosted decision trees
  - logistic regression
  - online learning
  - spark
date: 2025-05-17
updated: 2026-07-31
status: evergreen
description: Notes on He et al. (2014) covering the GBDT plus logistic regression architecture, data freshness, online learning, and the systems work needed to train CTR models in real time.
sources:
  - title: He et al. (2014), Practical Lessons from Predicting Clicks on Ads at Facebook
    url: https://quinonero.net/Publications/predicting-clicks-facebook.pdf
    type: paper
---

## Purpose

This note records the main modeling and systems lessons from He et al.'s Facebook ads CTR paper. The paper is worth reading because it is not just a model comparison. It shows where the gains came from, how much freshness mattered, and what extra infrastructure was needed to make online training usable in production. This is a concrete ranking case study for [[ml/recommender-systems/retrieval-and-ranking|retrieval and ranking]] and [[ml/recommender-systems/recommender-systems|recommender systems]].

## Citation

- [Practical Lessons from Predicting Clicks on Ads at Facebook (He et al., ADKDD 2014)](https://quinonero.net/Publications/predicting-clicks-facebook.pdf)

## Background

The paper studies the final click prediction stage in Facebook's ads ranking cascade. Facebook did not retrieve ads from a query the way sponsored search systems do. Ads were targeted by demographics and interests, which meant a request could have a very large eligible set. That forced a cascade of models with increasing cost, and this paper focuses on the last stage where the candidate set is already narrow enough that a more expensive model makes sense.

The core problem is to estimate CTR well enough that the downstream auction can trust the score. The paper keeps the objective narrow. It does not optimize revenue directly. It studies prediction quality and calibration.

## Metrics

The main metric is normalized entropy, which is normalized log loss. It compares the model's average log loss against the loss of a baseline that always predicts the background CTR.

$$
\text{NE} = \frac{H}{H_{\max}}
$$

with

$$
H = -\frac{1}{n} \sum_{i=1}^{n} \left( \frac{1 + y_i}{2} \log(p_i) + \frac{1 - y_i}{2} \log(1 - p_i) \right)
$$

and

$$
H_{\max} = -(p \log(p) + (1 - p) \log(1 - p))
$$

Here $p$ is the empirical background CTR and $p_i$ is the model's predicted click probability for impression $i$. Lower is better.

The paper also tracks **calibration**, defined as

$$
\text{Calibration} = \frac{\text{expected clicks}}{\text{observed clicks}}
$$

so the ideal value is 1. This matters because a ranking system that gets the order right but misstates probabilities can still damage delivery and bidding decisions. That is the reason the authors prefer NE to AUC as the main metric.

## Hybrid Model: GBDT Plus Logistic Regression

The central modeling result is simple:

- train boosted decision trees in batch
- use the leaf reached in each tree as a sparse categorical feature
- feed that transformed feature vector into a logistic regression model

This turns each tree path into a learned rule. If an example lands in one leaf of each tree, the linear model sees a sparse binary code saying which rules fired. The point is not that trees and logistic regression are each strong on their own. The point is that trees provide supervised non-linear feature crosses, and logistic regression then learns how to weight those rules cleanly.

The paper's headline result is in Table 1:

| Model | NE relative to trees-only baseline |
| --- | ---: |
| LR + Trees | 96.58% |
| LR only | 99.43% |
| Trees only | 100% |

Since lower NE is better, the hybrid beats either model alone. Relative to plain logistic regression, the tree transform cuts NE by about 2.85%. Relative to trees alone, it cuts NE by about 3.42%. The paper calls that a large effect, and it is. Their point is that most routine feature work only buys a few tenths of a percent.

The useful intuition is that boosted trees handle non-linearity and interactions, while logistic regression keeps the final scorer small, sparse, and cheap.

## Data Freshness Matters

The next result is about staleness. The authors train on one day and test on the following six days. Accuracy degrades steadily as the gap grows. They report that moving from weekly retraining to daily retraining reduces NE by about 1% for both trees and the hybrid LR-plus-tree model.

That is not a flashy number. It is still operationally important. A 1% NE gain from freshness means the system is learning a moving target. User behavior, inventory, and advertiser behavior shift fast enough that stale data leaves money on the floor.

This also sets up the rest of the paper. Trees are expensive enough that fully real-time retraining is awkward. The linear layer is cheap enough that online learning is plausible.

## Online Learning for the Linear Layer

The paper compares five SGD learning-rate schemes for online logistic regression:

1. Per-coordinate learning rate
2. Per-weight square-root decay
3. Per-weight decay
4. Global decay
5. Constant learning rate

The winner is the per-coordinate schedule

$$
\eta_{t,i} = \frac{\alpha}{\beta + \sqrt{\sum_{j=1}^{t} \nabla_{j,i}^2}}
$$

with tuned parameters $\alpha = 0.1$ and $\beta = 1.0$.

The paper reports that this per-coordinate LR scheme gets the best NE, roughly 5% better than the worst scheme. The explanation is practical. Features arrive with very uneven frequencies. A single global schedule decays too fast for rare features. A per-weight schedule still decays too aggressively. Per-coordinate adaptation handles that imbalance better.

The paper also compares this best SGD-trained logistic regression to **Bayesian online probit regression** (BOPR). Table 3 gives:

| Model | NE relative to online LR |
| --- | ---: |
| LR | 100% |
| BOPR | 99.82% |

So BOPR is marginally better in this offline comparison, but the difference is tiny. The paper's operational conclusion is that LR is still attractive because:

- the model stores one weight per active feature instead of a mean and variance pair
- prediction needs one sparse inner product instead of two
- smaller models are friendlier to cache locality and latency

BOPR still has one interesting advantage. Because it is Bayesian, it gives a predictive distribution rather than just a point estimate. The paper notes that this can support explore-exploit schemes.

## Online Joiner

The model result alone is not enough. If the linear layer trains online, the system needs a real-time stream of labeled examples. That is what the paper's **online joiner** does.

The joiner watches two streams:

- impressions, with the features used at ranking time
- clicks, which arrive later if the user clicks

The hard part is that negative labels are implicit. Nobody presses a "no click" button. An impression becomes negative only after waiting long enough that a late click is unlikely.

That creates a direct tradeoff:

- a longer waiting window improves click coverage
- a shorter window reduces delay and memory pressure

The joiner uses a `HashQueue`, basically a FIFO buffer plus a hash map keyed by request ID, to hold impressions while waiting for matching click events. After the join window expires, the system emits either a positive example or a negative one if no click arrived.

Two practical points from this section matter:

- missed late clicks bias the real-time stream downward by making CTR look slightly lower than it is
- streaming systems need anomaly protection, because stale or broken click streams can collapse predicted CTR and reduce ad delivery

The authors say the bias from incomplete click coverage can be kept to decimal points of a percent and corrected for. They also recommend disconnecting the online trainer automatically if the real-time data distribution shifts abruptly.

## Containing Memory and Latency

The paper then shifts from pure accuracy to deployability.

### Number of Trees

More trees improve NE, but with diminishing returns. The paper reports that almost all of the gain comes from the first 500 trees. The last 1,000 trees reduce NE by less than 0.1%.

That is a useful deployment rule. If the last thousand trees barely move NE, they are not free. They cost memory, CPU, and latency.

The paper also sees overfitting in one smaller submodel after 1,000 trees.

### Feature Importance

The boosting model exposes feature importance via cumulative loss reduction. The distribution is very skewed:

- the top 10 features account for about half of total importance
- the last 300 features contribute less than 1%

This means aggressive pruning can keep the system smaller without giving up much.

## Historical Features Beat Contextual Features

The paper splits features into:

- **contextual** features, such as time of day, device, or page context
- **historical** features, such as past ad CTR or user CTR

Historical features dominate the top-ranked features. The top 10 by importance are all historical. Among the top 20, only 2 are contextual.

Table 4 compares feature groups:

| Features used | NE relative to contextual-only baseline |
| --- | ---: |
| All | 95.65% |
| Historical only | 96.32% |
| Contextual only | 100% |

The operational reading is clear:

- removing historical features hurts a lot, about 4.5% in relative NE
- removing contextual features hurts much less, under 1%

That does not make contextual features optional. They are still necessary for cold start, where the user or ad has little history. The paper also reports that contextual features are more sensitive to freshness, while historical features are more stable over time because they summarize accumulated behavior.

## Coping With Massive Training Data

The paper closes with data-volume tradeoffs.

### Uniform Subsampling

The authors train tree models with subsampling rates in $\{0.001, 0.01, 0.1, 0.5, 1\}$. More data helps, but the returns taper off. Their practical claim is that training on only 10% of the data costs about 1% in normalized-entropy performance relative to the full dataset, while keeping calibration effectively unchanged.

That is a good trade if training cost is the constraint.

### Negative Downsampling

Because clicks are rare, the dataset is heavily imbalanced. The paper tries downsampling only the negative class and finds that the sampling rate matters a lot. The best result comes at a negative downsampling rate of **0.025**.

This helps training speed and can improve accuracy, but it breaks calibration unless predictions are mapped back to the real class prior. The paper gives the correction:

$$
q = \frac{p}{p + (1 - p) / w}
$$

where:

- $p$ is the predicted probability in the downsampled training space
- $w$ is the negative downsampling rate
- $q$ is the recalibrated live-space prediction

This is one of the better lessons in the paper. Sampling changes the label distribution the model sees. If you change that distribution, you need to undo it at serving time.

## What I Would Remember

- The biggest win was not a fancy online learner. It was the hybrid architecture: boosted trees to learn sparse rule features, then logistic regression on top.
- Freshness mattered enough that daily retraining beat weekly retraining by about 1% NE, and that justified online updates for the cheap final layer.
- Per-coordinate learning rates were the best SGD choice for online LR because feature frequencies were badly imbalanced.
- Historical features carried most of the predictive power, but contextual features still mattered for cold start.
- Once the main modeling choice was right, the hard work shifted to systems details: joining delayed labels, bounding memory, controlling latency, sampling data, and preserving calibration.

## Related Notes

- [[ml/recommender-systems/two-tower-retrieval|Two-Tower Retrieval and the MovieLens 100K experiment]]
- [[ml/recommender-systems/recommender-systems|Recommender Systems]]
- [[ml/recommender-systems/retrieval-and-ranking|Retrieval and Ranking]]
- [[ml/recommender-systems/intro-mapreduce-spark|MapReduce and Spark]]

## Sources

- [He et al. (2014), Practical Lessons from Predicting Clicks on Ads at Facebook](https://quinonero.net/Publications/predicting-clicks-facebook.pdf)
