---
title: Probability, Expectation, and Concentration Bounds
category: Mathematics
tags:
  - probability
  - expectation
  - variance
  - concentration bounds
  - random variables
  - statistics
date: 2026-08-01
status: draft
description: Reference for random variables, expectation, variance, covariance, conditional expectation, and the Markov-Chebyshev-Chernoff-Hoeffding chain, with sample-size implications and a NumPy simulation.
sources:
  - title: Pishro-Nik, Introduction to Probability, Statistics, and Random Processes
    url: https://probabilitycourse.com/
    type: book
  - title: Aldous, Hoeffding's inequality (course handout)
    url: https://www.stat.berkeley.edu/~aldous/Real-World/hoeffding.pdf
    type: lecture
  - title: Cornell CS 4780, lecture note 2, ML setup and notation
    url: https://www.cs.cornell.edu/courses/cs4780/2018fa/lectures/lecturenote02_mlnotation.pdf
    type: lecture
---

## Purpose

This is the probability note other sections can cite instead of re-deriving concentration arguments ad hoc. It fixes definitions for expectation, variance, covariance, and conditional expectation, then builds the inequality chain Markov, Chebyshev, Chernoff, Hoeffding, each one a strictly stronger use of information about the random variable. The payoff is quantitative: how many samples you need before an empirical average can be trusted, which is the question underneath A/B tests, offline recommender metrics, and benchmark noise.

## Random variables and expectation

A random variable $X$ is a function from outcomes to numbers; we describe it by its distribution. Expectation is the probability-weighted average ([Pishro-Nik ch. 6](https://probabilitycourse.com/)):

$$
\mathbb{E}[X] = \sum_x x\, p(x) \quad \text{(discrete)}, \qquad
\mathbb{E}[X] = \int x f(x)\, dx \quad \text{(continuous)}.
$$

The single most used fact is linearity: $\mathbb{E}[aX + bY] = a\,\mathbb{E}[X] + b\,\mathbb{E}[Y]$ with no independence assumption. Independence is only needed for products: if $X \perp Y$ then $\mathbb{E}[XY] = \mathbb{E}[X]\,\mathbb{E}[Y]$.

Variance measures spread, covariance measures co-movement:

$$
\mathrm{Var}(X) = \mathbb{E}[(X - \mu)^2] = \mathbb{E}[X^2] - \mu^2, \qquad
\mathrm{Cov}(X, Y) = \mathbb{E}[XY] - \mathbb{E}[X]\,\mathbb{E}[Y].
$$

Variance is not linear: $\mathrm{Var}(aX) = a^2 \mathrm{Var}(X)$, and $\mathrm{Var}(X + Y) = \mathrm{Var}(X) + \mathrm{Var}(Y) + 2\,\mathrm{Cov}(X, Y)$, which collapses to a plain sum for independent (or merely uncorrelated) variables. That collapse is the reason averaging works: for iid $X_1, \dots, X_n$ with mean $\mu$ and variance $\sigma^2$, the empirical mean $\hat{\mu}_n = \frac{1}{n}\sum_i X_i$ has

$$
\mathbb{E}[\hat{\mu}_n] = \mu, \qquad \mathrm{Var}(\hat{\mu}_n) = \frac{\sigma^2}{n}.
$$

Conditional expectation $\mathbb{E}[X \mid Y]$ is the best guess of $X$ given $Y$, itself a random variable, and the tower property $\mathbb{E}[X] = \mathbb{E}[\mathbb{E}[X \mid Y]]$ lets you compute expectations by conditioning on whatever makes the problem factor ([Pishro-Nik §6.3-6.4](https://probabilitycourse.com/)). The ML framing in [Cornell CS 4780's notation note](https://www.cs.cornell.edu/courses/cs4780/2018fa/lectures/lecturenote02_mlnotation.pdf) is a direct application: data are iid draws from an unknown $P$, the test error is an expectation over $P$, and everything you compute from a sample is an estimator of some expectation.

## The inequality chain

Each inequality below uses one more piece of structure and buys an exponentially better tail.

**Markov** (needs: nonnegativity and a mean). For $X \ge 0$ and $a > 0$:

$$
\Pr[X \ge a] \le \frac{\mathbb{E}[X]}{a}.
$$

Proof in one line: $\mathbb{E}[X] \ge \mathbb{E}[X \cdot \mathbf{1}\{X \ge a\}] \ge a \Pr[X \ge a]$. The bound decays only like $1/a$, but it is the engine for everything else.

**Chebyshev** (needs: a variance). Apply Markov to the nonnegative variable $(X - \mu)^2$ with threshold $\epsilon^2$:

$$
\Pr[|X - \mu| \ge \epsilon] = \Pr[(X-\mu)^2 \ge \epsilon^2] \le \frac{\mathrm{Var}(X)}{\epsilon^2}.
$$

Combined with $\mathrm{Var}(\hat{\mu}_n) = \sigma^2/n$ this already proves the weak law of large numbers: the empirical mean converges to $\mu$ in probability. The decay in $n$ is only polynomial, $O(1/n\epsilon^2)$.

**Chernoff** (needs: a moment generating function). Apply Markov to $e^{tX}$, then optimize the free parameter $t > 0$:

$$
\Pr[X \ge a] = \Pr[e^{tX} \ge e^{ta}] \le e^{-ta}\, \mathbb{E}[e^{tX}].
$$

Because the MGF of a sum of independent variables factors into a product, the exponent scales linearly in $n$ and the tail decays exponentially. For a sum $S_n$ of independent Bernoullis with mean $\mu = \mathbb{E}[S_n]$, the multiplicative form is $\Pr[S_n \ge (1+\delta)\mu] \le \exp(-\mu\,[(1+\delta)\ln(1+\delta) - \delta])$.

**Hoeffding** (needs: bounded ranges). For independent $X_i \in [a_i, b_i]$ ([Aldous's handout](https://www.stat.berkeley.edu/~aldous/Real-World/hoeffding.pdf)):

$$
\Pr\!\left[\Big|\sum_i X_i - \mathbb{E}\Big[\sum_i X_i\Big]\Big| \ge t\right]
\le 2 \exp\!\left(\frac{-2t^2}{\sum_i (b_i - a_i)^2}\right).
$$

For iid $X_i \in [0,1]$ and the empirical mean, this specializes to the form worth memorizing:

$$
\Pr[|\hat{\mu}_n - \mu| \ge \epsilon] \le 2 e^{-2n\epsilon^2}.
$$

## Sample sizes, A/B tests, and measurement noise

Invert the Hoeffding bound. To estimate a $[0,1]$-bounded mean within $\pm\epsilon$ with probability $1 - \delta$, set $2e^{-2n\epsilon^2} \le \delta$ and solve:

$$
n \ge \frac{\ln(2/\delta)}{2\epsilon^2}.
$$

The shape of this formula explains a lot of practice. Precision is expensive, $n$ grows as $1/\epsilon^2$, so halving the error bar quadruples the sample size. Confidence is cheap, $\delta$ sits inside a log, so going from 95% to 99.9% confidence costs a small constant factor. Concretely, $\epsilon = 0.01$ and $\delta = 0.05$ needs $n \ge \ln(40)/0.0002 \approx 18{,}445$ samples. An A/B test comparing click-through rates is estimating two such means, and detecting a difference of a fraction of a percent forces the $1/\epsilon^2$ price. The same arithmetic bounds how many queries an offline recommender evaluation needs before a metric delta is signal rather than sampling noise, and how many benchmark iterations to run before comparing two systems, the concern in the [[systems/operating-systems/benchmarks/README|OS benchmarks notes]]. Hoeffding assumes independent samples; correlated benchmark iterations (warm caches, interference) violate that and make the bound optimistic.

## Simulation check

Hoeffding is a worst-case bound, and a simulation shows both that it holds and how much slack it has:

```python
import numpy as np

rng = np.random.default_rng(0)
n, eps, trials = 500, 0.05, 200_000
X = rng.random((trials, n))          # iid Uniform[0,1], mu = 0.5
dev = np.abs(X.mean(axis=1) - 0.5)
empirical = (dev >= eps).mean()
hoeffding = 2 * np.exp(-2 * n * eps**2)
print(empirical, hoeffding)          # 8e-05 vs 0.1642
```

The measured tail probability is $8 \times 10^{-5}$ against a Hoeffding bound of 0.164, three orders of magnitude of slack for uniform variables. The gap is expected: Hoeffding only uses the range $[0,1]$ and must cover the worst distribution with that range (Bernoulli at the endpoints), while Uniform[0,1] has variance $1/12$, a third of Bernoulli's $1/4$. A quick sanity check against the CLT explains the measured number: the empirical mean has standard deviation $\sqrt{1/(12 \cdot 500)} \approx 0.0129$, so $\epsilon = 0.05$ is a 3.9-sigma deviation, and the two-sided normal tail at 3.9 sigma is about $1 \times 10^{-4}$, matching the simulation. Variance-aware bounds like Bernstein's capture this; the ones here are the standard first tools.

## Sources

- [Pishro-Nik, Introduction to Probability, Statistics, and Random Processes, chapters 6-7](https://probabilitycourse.com/)
- [Aldous, Hoeffding's inequality, course handout](https://www.stat.berkeley.edu/~aldous/Real-World/hoeffding.pdf)
- [Cornell CS 4780 (2018), lecture note 2, ML setup and notation](https://www.cs.cornell.edu/courses/cs4780/2018fa/lectures/lecturenote02_mlnotation.pdf)

## Related notes

- [[ml/recommender-systems/bias-and-marketplace-effects|Bias, Marketplace Effects, and Counterfactual Evaluation]]
- [[systems/operating-systems/benchmarks/README|OS Benchmarks]]
- [[math/linear-algebra/cheatsheet|Matrix Theory]]
