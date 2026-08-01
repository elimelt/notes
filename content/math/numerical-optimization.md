---
title: Numerical Optimization for Machine Learning
category: Mathematics
tags:
  - optimization
  - gradient descent
  - sgd
  - momentum
  - adam
  - learning-rate schedules
date: 2026-08-01
status: draft
description: The optimizers that actually train models, from gradient descent and conditioning through momentum, Nesterov, Adam, and decoupled weight decay, separating theorems from empirical heuristics, with a measured NumPy experiment.
sources:
  - title: Goodfellow, Bengio, and Courville, Deep Learning, chapter 8
    url: https://www.deeplearningbook.org/contents/optimization.html
    type: book
  - title: Kingma and Ba (2015), Adam - A Method for Stochastic Optimization
    url: https://arxiv.org/abs/1412.6980
    type: paper
  - title: Sutskever et al. (2013), On the importance of initialization and momentum in deep learning
    url: https://proceedings.mlr.press/v28/sutskever13.html
    type: paper
  - title: Loshchilov and Hutter (2019), Decoupled Weight Decay Regularization
    url: https://arxiv.org/abs/1711.05101
    type: paper
  - title: Nesterov Accelerated Gradient and Momentum (mize docs)
    url: https://jlmelville.github.io/mize/nesterov.html
    type: docs
---

## Purpose

This note covers the optimizers that show up in real training loops and the small amount of theory that explains their behavior: gradient descent and conditioning, stochastic gradients, momentum and Nesterov, Adam and decoupled weight decay, and schedules. Throughout, claims are tagged as theorems (proved for restricted function classes, usually convex quadratics) or heuristics (empirical, justified by what trains well). The gradients being descended are derived in [[math/matrix-calculus|Matrix Calculus for Machine Learning]]; convex background is in [[math/convexity-lagrangians-kkt|Convexity, Lagrangians, and KKT]].

## Gradient descent and conditioning

Gradient descent iterates $\theta_{t+1} = \theta_t - \alpha \nabla J(\theta_t)$. On a strongly convex quadratic $J(\theta) = \frac{1}{2}\theta^T H \theta$ with eigenvalues $0 < \mu = \lambda_{\min} \le \lambda_{\max} = L$, the error contracts linearly, and with the optimal fixed step $\alpha = 2/(\mu + L)$ the rate is governed by the condition number $\kappa = L/\mu$:

$$
\lVert \theta_t - \theta^\star \rVert \le \left(\frac{\kappa - 1}{\kappa + 1}\right)^{t} \lVert \theta_0 - \theta^\star \rVert.
$$

This is a theorem (standard; see Nesterov's *Introductory Lectures* or B&V §9.3). Its content: a well-conditioned problem ($\kappa$ near 1) converges in a few steps, and an ill-conditioned one crawls, because the step size is hostage to the steepest direction while progress is needed along the flattest. [Deep Learning ch. 8](https://www.deeplearningbook.org/contents/optimization.html) treats ill-conditioning as the first of the fundamental difficulties in neural net training. The other headline difficulty is saddle points: for high-dimensional nonconvex problems, critical points are overwhelmingly saddles rather than bad local minima ([Dauphin et al. 2014](https://arxiv.org/abs/1406.2572), an empirical-plus-random-matrix argument, not a theorem about neural nets).

## Stochastic gradients

SGD replaces $\nabla J$ with an unbiased minibatch estimate. The classical convergence guarantee (Robbins and Monro, 1951) requires the step sizes to satisfy

$$
\sum_t \alpha_t = \infty, \qquad \sum_t \alpha_t^2 < \infty,
$$

enough total step to get anywhere, but decaying fast enough that gradient noise stops moving you ([DL ch. 8.3.1](https://www.deeplearningbook.org/contents/optimization.html)). In practice nobody anneals to zero; constant-then-decay schedules are heuristics tuned by validation loss.

Batch size trades gradient variance against per-step cost. Variance of the minibatch gradient falls as $1/B$, so returns diminish: doubling the batch halves the variance but doubles the compute, a sublinear win in wall-clock terms once parallel hardware saturates ([DL ch. 8.1.3](https://www.deeplearningbook.org/contents/optimization.html)). The claim that small-batch noise acts as a regularizer and large batches can generalize worse is empirical, not settled theory.

## Momentum and Nesterov

Classical momentum (Polyak) accumulates a velocity:

$$
v_{t+1} = \mu v_t - \alpha \nabla J(\theta_t), \qquad \theta_{t+1} = \theta_t + v_{t+1}.
$$

Along directions where gradients agree step after step, velocity builds toward a terminal speed $\alpha \lVert g \rVert / (1 - \mu)$, a $1/(1-\mu)$ amplification, 10x at $\mu = 0.9$; along oscillating directions, contributions cancel. That is exactly the medicine for ill-conditioning. On quadratics this is a theorem: momentum improves the iteration count from $O(\kappa)$ to $O(\sqrt{\kappa})$ with the optimal $\mu = (\sqrt{\kappa}-1)/(\sqrt{\kappa}+1)$ ([Sutskever et al. 2013](https://proceedings.mlr.press/v28/sutskever13.html), citing Polyak 1964).

Nesterov's variant evaluates the gradient at the look-ahead point:

$$
v_{t+1} = \mu v_t - \alpha \nabla J(\theta_t + \mu v_t), \qquad \theta_{t+1} = \theta_t + v_{t+1}.
$$

The correction matters most when velocity is about to overshoot: the look-ahead gradient sees the far wall one step early. [Sutskever et al.](https://proceedings.mlr.press/v28/sutskever13.html) showed the two differ only in where the gradient is taken, that NAG is more tolerant of large $\mu$, and that momentum plus careful initialization lets plain first-order methods train deep networks previously thought to need second-order machinery. The [mize notes](https://jlmelville.github.io/mize/nesterov.html) give the standard reparameterization that implements NAG as a small correction term on classical momentum, which is how frameworks implement `nesterov=True`.

## Adam and weight decay

[Adam](https://arxiv.org/abs/1412.6980) keeps exponential moving averages of the gradient and its square, corrects their initialization bias, and scales each coordinate's step by its own noise level:

$$
\begin{aligned}
m_t &= \beta_1 m_{t-1} + (1-\beta_1) g_t, \qquad & \hat{m}_t &= m_t / (1 - \beta_1^t), \\
v_t &= \beta_2 v_{t-1} + (1-\beta_2) g_t^2, & \hat{v}_t &= v_t / (1 - \beta_2^t), \\
\theta_{t+1} &= \theta_t - \alpha\, \hat{m}_t / (\sqrt{\hat{v}_t} + \epsilon). &&
\end{aligned}
$$

Defaults from the paper: $\alpha = 0.001$, $\beta_1 = 0.9$, $\beta_2 = 0.999$, $\epsilon = 10^{-8}$. The per-coordinate scaling makes updates invariant to diagonal rescaling of the gradient and bounds the effective step near $\alpha$, which is why Adam tolerates sloppy learning-rate choices that would blow up SGD. The bias correction exists because $m_0 = v_0 = 0$ drags early averages toward zero; dividing by $1 - \beta^t$ undoes it, and it matters precisely when $\beta_2$ is close to 1.

Weight decay in Adam has a subtlety worth knowing. Adding $\frac{\lambda}{2}\lVert\theta\rVert^2$ to the loss (L2 regularization) feeds $\lambda\theta$ through the adaptive machinery, so parameters with large historical gradients get *less* decay, coupling regularization strength to gradient history. [Loshchilov and Hutter](https://arxiv.org/abs/1711.05101) decouple it, applying $-\alpha\lambda\theta_t$ directly in the update, outside the $\hat{m}/\sqrt{\hat{v}}$ scaling. That is AdamW. Their evidence is empirical, restoring Adam's generalization to SGD-with-momentum levels on image classification, and AdamW is now the default in most transformer training. In PyTorch these are literally `torch.optim.Adam(weight_decay=...)` (coupled L2) versus `torch.optim.AdamW` (decoupled); the two optimize different effective objectives.

Learning-rate schedules (step decay, cosine, warmup) are heuristics layered on top. Warmup interacts specifically with Adam: early in training $\hat{v}$ is estimated from few samples, so the first steps can be badly scaled, and ramping $\alpha$ up over the first few thousand steps is the standard mitigation.

## A measured comparison

The claims about conditioning and momentum are checkable on the quadratic where the theory is exact. $J(\theta) = \frac{1}{2}\theta^T \mathrm{diag}(1, 100)\,\theta$, so $\kappa = 100$:

```python
import numpy as np

H = np.diag([1.0, 100.0])
def grad(th): return H @ th

def run(update, steps=200):
    th, state = np.array([1.0, 1.0]), None
    hist = []
    for t in range(steps):
        th, state = update(th, state, t)
        hist.append(np.sqrt(th @ H @ th))
    return hist

a = 2 / (1 + 100)                       # optimal GD step for this spectrum
gd   = run(lambda th, s, t: (th - a * grad(th), None))

mu = (np.sqrt(100) - 1) / (np.sqrt(100) + 1)   # optimal momentum
am = (2 / (1 + np.sqrt(1/100)))**2 / 100       # matching step size
def mom(th, v, t):
    v = mu * (v if v is not None else 0) - am * grad(th)
    return th + v, v
heavy = run(mom)

print(f"GD after 200 steps:       {gd[-1]:.3e}")     # 1.840e-01
print(f"momentum after 200 steps: {heavy[-1]:.3e}")  # 5.583e-08
```

Measured on this machine (NumPy 2.x, the script above verbatim): plain GD with its optimal step ends at error norm $1.84 \times 10^{-1}$ after 200 iterations. The initial norm is $\sqrt{101} \approx 10.05$, so the contraction factor is $0.184/10.05 \approx 0.0183$, matching the theory's $((\kappa-1)/(\kappa+1))^{200} = (99/101)^{200} \approx 0.0183$ to three digits. Heavy-ball momentum with the optimal $\mu = 9/11 \approx 0.818$ reaches $5.6 \times 10^{-8}$, better by more than six orders of magnitude. The $O(\kappa)$ versus $O(\sqrt{\kappa})$ gap is not an asymptotic nicety; at $\kappa = 100$ it is the difference between converged and not.

## Sources

- [Goodfellow, Bengio, and Courville, Deep Learning, chapter 8](https://www.deeplearningbook.org/contents/optimization.html)
- [Kingma and Ba (2015), Adam: A Method for Stochastic Optimization](https://arxiv.org/abs/1412.6980)
- [Sutskever et al. (2013), On the importance of initialization and momentum in deep learning](https://proceedings.mlr.press/v28/sutskever13.html)
- [Loshchilov and Hutter (2019), Decoupled Weight Decay Regularization](https://arxiv.org/abs/1711.05101)
- [Dauphin et al. (2014), Identifying and attacking the saddle point problem](https://arxiv.org/abs/1406.2572)
- [Nesterov Accelerated Gradient and Momentum (mize docs)](https://jlmelville.github.io/mize/nesterov.html)

## Related notes

- [[math/matrix-calculus|Matrix Calculus for Machine Learning]]
- [[math/convexity-lagrangians-kkt|Convexity, Lagrangians, and KKT Conditions]]
- [[ml/deep-learning/neural-networks-from-scratch|Neural Networks from Scratch]]
- [[ml/deep-learning/modeling-architecture-and-data|Modeling, Architecture, and Data]]
