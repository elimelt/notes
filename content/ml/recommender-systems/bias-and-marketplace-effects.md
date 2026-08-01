---
title: Bias, Marketplace Effects, and Counterfactual Evaluation
category: Recommender Systems
tags:
  - recommender systems
  - selection bias
  - exposure bias
  - contextual bandits
  - counterfactual evaluation
  - fairness
  - ads
date: 2026-07-31
updated: 2026-08-01
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
  - title: Dudík, Langford, and Li (2011), Doubly Robust Policy Evaluation and Learning
    url: https://arxiv.org/pdf/1103.4601
    type: paper
  - title: Swaminathan and Joachims (2015), The Self-Normalized Estimator for Counterfactual Learning
    url: https://proceedings.neurips.cc/paper_files/paper/2015/hash/39027dfad5138c9ca0c474d71db915c3-Abstract.html
    type: paper
  - title: Chapelle, Joachims, Radlinski, and Yue (2012), Large-Scale Validation and Analysis of Interleaved Search Evaluation
    url: https://www.cs.cornell.edu/people/tj/publications/chapelle_etal_12a.pdf
    type: paper
  - title: Kuang et al. (2018), Stable Prediction across Unknown Environments
    url: https://arxiv.org/pdf/1806.06270
    type: paper
  - title: Zou et al. (2019), Reinforcement Learning to Optimize Long-term User Engagement in Recommender Systems
    url: https://arxiv.org/pdf/1902.05570
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

The estimator is unbiased in the idealized setting: take the expectation over $a_t \sim \pi_0(\cdot \mid x_t)$ and the resulting reward, and each term contributes $\sum_a \pi_0(a\mid x)\frac{\pi(a\mid x)}{\pi_0(a\mid x)}r(x,a) = \sum_a \pi(a\mid x) r(x,a) = V(\pi \mid x)$, the true value of $\pi$ at that context. But the estimator is also noisy, and the noise has a specific cause. If $\pi_0(a\mid x)$ is small for an action that $\pi$ favors, that log line gets a huge weight $\pi(a\mid x)/\pi_0(a\mid x)$, and a handful of such lines can dominate the whole average. That is why randomized data collection is not optional bookkeeping. It is the price of honest offline evaluation.

### Self-Normalized IPS (SNIPS)

Plain IPS has an annoying property: it is unbiased for the value, but it is not invariant to how the reward is scaled or shifted, and its variance can be dominated by a single logged example with a tiny denominator. Swaminathan and Joachims call this **propensity overfitting**: when IPS is used as a training objective rather than just an evaluation metric, the optimizer can improve the estimate by driving down $\pi(a\mid x)$ on the specific actions that happened to get sampled, rather than by improving the policy.

The self-normalized (SNIPS) estimator divides by the sum of the importance weights instead of by $n$:

$$
\hat{V}_{\text{SNIPS}}(\pi) = \frac{\sum_{t=1}^{n} \frac{\pi(a_t \mid x_t)}{\pi_0(a_t \mid x_t)} r_t}{\sum_{t=1}^{n} \frac{\pi(a_t \mid x_t)}{\pi_0(a_t \mid x_t)}}
$$

This is a ratio estimator, so it is biased at finite $n$, but the bias shrinks as $n$ grows and the reduction in variance is usually worth it. The intuition: if the importance weights happen to sum to more than $n$ on a given sample (an unlucky draw that over-favors $\pi$'s actions), IPS reports too much value and SNIPS automatically discounts for it, because the same inflated weights appear in the denominator.

### Direct Method (DM)

The direct method skips importance weighting entirely. Fit a reward model $\hat{r}(x, a)$ from the logs by regression, then estimate policy value by averaging the model's prediction under $\pi$:

$$
\hat{V}_{\text{DM}}(\pi) = \frac{1}{n} \sum_{t=1}^{n} \sum_{a} \pi(a \mid x_t)\, \hat{r}(x_t, a)
$$

DM has low variance because there is no importance ratio to blow up. Its problem is bias: if $\hat{r}$ is wrong on actions the logging policy rarely took (which is exactly where $\pi$ wants to send traffic), DM will confidently report a wrong number, and there is no mechanism inside the estimator to signal that it is extrapolating into a region it has never seen.

### Doubly Robust (DR) Estimator

Dudík, Langford, and Li combine DM and IPS so that each covers the other's weak point. The DR estimator is

$$
\hat{V}_{\text{DR}}(\pi) = \frac{1}{n} \sum_{t=1}^{n} \left[ \hat{r}(x_t, \pi) + \frac{\pi(a_t \mid x_t)}{\pi_0(a_t \mid x_t)} \bigl(r_t - \hat{r}(x_t, a_t)\bigr) \right], \qquad \hat{r}(x,\pi) := \sum_a \pi(a\mid x)\hat r(x,a)
$$

The first term is the DM baseline. The second term is an IPS correction applied not to the raw reward but to the *residual* between the observed reward and the model's prediction for the action actually taken.

Here is the algebra behind the name. Fix a context $x$, let $a \sim \pi_0(\cdot \mid x)$, and let $r$ have $\mathbb{E}[r \mid x, a] = r(x,a)$, the true expected reward. Taking the expectation of one DR term over the logging policy's action distribution:

$$
\mathbb{E}_{a, r}\left[\hat r(x,\pi) + \frac{\pi(a\mid x)}{\pi_0(a\mid x)}\bigl(r - \hat r(x,a)\bigr)\right] = \hat r(x,\pi) + \sum_a \pi_0(a\mid x)\frac{\pi(a\mid x)}{\pi_0(a\mid x)}\bigl(r(x,a) - \hat r(x,a)\bigr)
$$

$$
= \hat r(x,\pi) + \sum_a \pi(a\mid x)\bigl(r(x,a) - \hat r(x,a)\bigr) = \hat r(x,\pi) + V(\pi\mid x) - \hat r(x,\pi) = V(\pi\mid x)
$$

Notice that $\hat r$ cancels regardless of whether it is any good, as long as $\pi_0(a\mid x) > 0$ wherever this cancellation needs to divide by it. That is the first robustness case: **the propensities are correct, the reward model can be arbitrarily wrong, and the estimator is still unbiased.**

Now consider the other case: propensities are estimated (call them $\hat\pi_0$, possibly biased) but the reward model happens to be exactly correct, $\hat r(x,a) = r(x,a)$. Then the residual $r_t - \hat r(x_t,a_t)$ has expectation zero for every $t$ regardless of what $\hat\pi_0$ is, so the whole correction term vanishes in expectation and $\hat V_{\text{DR}}(\pi)$ collapses to $\hat r(x,\pi) = V(\pi\mid x)$ exactly. That is the second robustness case: **the reward model is correct, the propensities can be wrong, and the estimator is still unbiased.**

DR is unbiased if either piece is right. It also tends to have lower variance than plain IPS in practice, because a decent reward model absorbs most of the signal and the importance-weighted term only has to correct a residual, which is typically smaller and less heavy-tailed than the raw reward.

### Support Mismatch and Variance Blow-Up

All three importance-weighted estimators (IPS, SNIPS, DR) share one fatal weakness: they need $\pi_0(a\mid x) > 0$ everywhere $\pi(a\mid x) > 0$. If the logging policy never explored an action that the target policy wants to take, the ratio $\pi(a\mid x)/\pi_0(a\mid x)$ is either undefined or, just as bad, estimated from a near-zero denominator with huge sampling error. Dudík, Langford, and Li's empirical results and Li et al.'s search-engine deployment both stress this: propensity overlap is a precondition, not a nice-to-have.

In practice this shows up as one or two logged examples carrying almost all the weight in the sum, which means the effective sample size is far smaller than $n$ suggests. A rule of thumb: if the largest few importance weights account for a large share of the total weight mass, distrust the point estimate no matter how tight the naive confidence interval looks.

### Practical Logging-Policy Design

Because overlap is the precondition for everything above, the logging policy has to be designed with future counterfactual evaluation in mind, not just with today's user experience in mind:

- keep a randomization floor on every action with nonzero business value, even a small one, so $\pi_0(a\mid x)$ never actually hits zero
- log the propensity $\pi_0(a_t \mid x_t)$ alongside every impression, not just the action and outcome, since it cannot be reconstructed later if the serving logic changes
- prefer stratified or epsilon-greedy exploration over policies with sharp decision boundaries, since sharp boundaries create regions with effectively zero support
- treat propensity logging as part of the schema contract for the serving system, since a silent regression there quietly invalidates every downstream offline evaluation

### Interleaving vs. A/B Testing

Interleaving is a different way to compare two rankers without a full traffic split: for a single query, merge the two rankers' results into one list (for example with team-draft interleaving) and attribute the win to whichever ranker contributed the clicked result. Chapelle, Joachims, Radlinski, and Yue's large-scale study across two commercial search engines found interleaving to be dramatically more sample-efficient than A/B testing at detecting the same ranking preference, because every single impression is a paired comparison rather than a between-subjects one.

The tradeoff is scope. Interleaving answers "which ranker do users prefer," a relative, single-query judgment. It does not directly answer "how does this change move revenue, retention, or long-run engagement," which is what an A/B test measures and what a marketplace ultimately cares about. Counterfactual estimators, interleaving, and A/B tests form a ladder of increasing cost and increasing fidelity: use cheap offline estimators to screen ideas, interleaving to confirm a ranking preference cheaply, and A/B tests to sign off on end-to-end business metrics before a full rollout.

### A Toy Comparison: IPS vs. SNIPS vs. DR

The following is a synthetic, illustrative example, not a measurement from a real system. Suppose a logging policy $\pi_0$ chooses between two actions, $a_1$ and $a_2$, with $\pi_0(a_1\mid x) = 0.9$ and $\pi_0(a_2\mid x) = 0.1$ for a fixed context $x$, and the true rewards are $r(x,a_1) = 0$ and $r(x,a_2) = 1$. A target policy $\pi$ always picks $a_2$, so the true value is $V(\pi\mid x) = 1$.

Log five interactions: four draws of $a_1$ (reward 0 each) and one draw of $a_2$ (reward 1), matching the $0.9/0.1$ split exactly.

- **IPS**: weight on the $a_2$ row is $\pi(a_2\mid x)/\pi_0(a_2\mid x) = 1/0.1 = 10$, weight on every $a_1$ row is $0/0.9 = 0$. $\hat V_{\text{IPS}} = \frac{1}{5}(0+0+0+0+10 \cdot 1) = 2.0$, badly overestimating the true value of $1$ purely from finite-sample noise in one rare draw.
- **SNIPS**: same numerator, but divide by the sum of weights instead of $n$: $\hat V_{\text{SNIPS}} = \frac{10}{0+0+0+0+10} = 1.0$, exactly right on this sample because the one nonzero weight is also the only term in the denominator.
- **DR** with a mediocre reward model $\hat r(x,a_1)=0.2, \hat r(x,a_2)=0.6$: $\hat r(x,\pi) = 0.6$. The correction term only fires on the $a_2$ row: $10 \cdot (1 - 0.6) = 4$. Averaging over five rows, $\hat V_{\text{DR}} = \frac{1}{5}(0.6+0.6+0.6+0.6+0.6+4) = \frac{1}{5}(3+4) = 1.4$, closer to the true value of $1$ than IPS despite a mediocre reward model, because the model absorbs most of the $a_1$ rows and the importance weighting only has to correct the residual on $a_2$.

The point of the toy example is not that SNIPS wins outright. It is that with one action drawn only 10% of the time, a single logged row can swing IPS by a factor of two, and both SNIPS and DR have mechanisms (normalization, residual correction) that dampen exactly that failure mode.

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

## Distribution Shift Compounds the Feedback Loop

The exposure loop described at the top of this note is a special case of a more general problem: a model trained on today's distribution gets deployed into tomorrow's distribution, which its own decisions helped create. Kuang, Cui, Athey, Xiong, and Li study this directly for tabular prediction, where a classifier trained on one environment is later applied to an environment with a shifted feature-outcome relationship. Their fix, global balancing, reweights training examples so that each feature's estimated effect is decorrelated from the other features, which produces a classifier whose accuracy degrades more gracefully when the deployment distribution moves. The recommender analogue is direct: a ranker trained purely on exposure-filtered clicks has implicitly fit spurious feature correlations that only held under the old exposure policy, and those correlations do not have to survive a policy change.

Zou, Xia, Ding, Song, Liu, and Yin push on a related but distinct problem: even a distribution-stable model can optimize the wrong horizon. A ranker trained to predict the next click is a myopic model of engagement. Their FeedRec system frames session-level feed ranking as a reinforcement learning problem with reward defined over both click-type signals (clicks, orders) and richer engagement signals (dwell time, return visits), explicitly to counter policies that inflate short-term clicks at the expense of long-term stickiness. The mechanism worth remembering is not the specific RL architecture, it is the framing: a purely supervised, single-step objective cannot represent the tradeoff between an immediately engaging recommendation and one that keeps a user coming back next week, and a system that only measures next-click accuracy will look great right up until retention quietly erodes.

Both papers point at the same operational conclusion for this note: counterfactual estimators and interleaving tell you whether a policy change helped relative to the current traffic mix, but neither one detects a policy that is *stably* better on today's distribution and quietly worse once its own exposure decisions reshape tomorrow's distribution. That is a reason to keep the longer-horizon metrics below in rotation even when short-term online tests look clean.

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
- [Dudík, Langford, and Li (2011), Doubly Robust Policy Evaluation and Learning](https://arxiv.org/pdf/1103.4601)
- [Swaminathan and Joachims (2015), The Self-Normalized Estimator for Counterfactual Learning](https://proceedings.neurips.cc/paper_files/paper/2015/hash/39027dfad5138c9ca0c474d71db915c3-Abstract.html)
- [Chapelle, Joachims, Radlinski, and Yue (2012), Large-Scale Validation and Analysis of Interleaved Search Evaluation](https://www.cs.cornell.edu/people/tj/publications/chapelle_etal_12a.pdf)
- [Kuang et al. (2018), Stable Prediction across Unknown Environments](https://arxiv.org/pdf/1806.06270)
- [Zou et al. (2019), Reinforcement Learning to Optimize Long-term User Engagement in Recommender Systems](https://arxiv.org/pdf/1902.05570)
