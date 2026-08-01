---
title: Modeling, Architecture, and Data
category: Deep Learning
tags:
  - deep learning
  - modeling
  - architecture
  - data representation
  - regularization
  - attention
  - resnet
date: 2026-07-31
updated: 2026-08-01
status: evergreen
description: How to choose a model class, objective, data representation, and training setup, with emphasis on inductive bias, optimization stability, scaling laws, compute-optimal training, and inference economics.
sources:
  - title: Deep Residual Learning for Image Recognition
    url: https://arxiv.org/abs/1512.03385
    type: paper
  - title: Attention Is All You Need
    url: https://arxiv.org/abs/1706.03762
    type: paper
  - title: Ioffe and Szegedy (2015), Batch Normalization
    url: https://arxiv.org/abs/1502.03167
    type: paper
  - title: Kaplan et al. (2020), Scaling Laws for Neural Language Models
    url: https://arxiv.org/abs/2001.08361
    type: paper
  - title: Hoffmann et al. (2022), Training Compute-Optimal Large Language Models
    url: https://arxiv.org/abs/2203.15556
    type: paper
  - title: Touvron et al. (2023), LLaMA - Open and Efficient Foundation Language Models
    url: https://arxiv.org/abs/2302.13971
    type: paper
  - title: Srivastava et al. (2014), Dropout
    url: https://www.cs.toronto.edu/~rsalakhu/papers/srivastava14a.pdf
    type: paper
---

## Purpose

Choosing an architecture is usually not the first hard decision. The first hard decision is deciding what the model is supposed to predict, what structure the data has, and what resource is actually scarce. This note is about that layer of design.

## Start from the Interface

A supervised learning problem is not defined by its model class. It is defined by:

- input space $x$
- output space $y$
- loss $\mathcal{L}(\hat{y}, y)$
- deployment constraints

Examples:

- token sequence to next token
- image to class label
- image to dense segmentation mask
- graph to node labels
- feature vector to scalar score

The head and the loss should follow from that interface. Classification wants cross-entropy. Regression wants a real-valued loss. Autoregressive generation wants a factorized log-likelihood.

## Architecture Is an Inductive Bias

Different architectures encode different assumptions.

| Data structure | Bias | Typical architecture |
| --- | --- | --- |
| tabular or fixed vectors | dense interactions | MLP |
| 2D grids | locality and translation equivariance | CNN |
| ordered sequences | state evolution through time | RNN / LSTM / GRU |
| long-range relational sequences | content-based routing | Transformer |
| irregular graphs | neighborhood message passing | GNN |

The architecture is a guess about which symmetries matter. A good guess saves parameters and data. A bad guess makes optimization work harder for no gain.

> [!abstract] Architecture selection is prior selection
> Every row of this table is a claim about the data: CNNs claim the same pattern matters anywhere in the grid, RNNs claim the past summarizes into a state, GNNs claim neighbors are informative. Picking an architecture is choosing which of these claims to hard-code rather than spend data learning.

## The Bias-Variance Question Shows Up as Architecture

A high-capacity model can fit strange functions. That is not the same thing as learning the right one under finite data and finite compute.

If structure is known, it is often wise to encode it:

- local convolutions instead of a fully connected image classifier
- causal masking instead of unconstrained sequence attention
- message passing instead of flattening a graph into arbitrary order

This is one of the few genuinely transferable design heuristics in deep learning.

## Optimization Choices Are Architectural Choices

Several famous papers are often described as "training tricks." They are better understood as changes to the effective architecture.

### Residual Connections

ResNet reframes a block as

$$
y = x + F(x)
$$

instead of asking the block to learn $H(x)$ directly. The paper's motivation is the **degradation problem**: deeper plain nets can have higher training error than shallower ones even though a deeper model contains the shallower solution as a special case via identity layers.

Residual connections matter because they preserve an easy signal path. The identity path carries both activations and gradients.

### Normalization

BatchNorm inserts

$$
\hat{x}^{(k)} = \frac{x^{(k)} - \mu_\mathcal{B}^{(k)}}{\sqrt{(\sigma_\mathcal{B}^{(k)})^2 + \epsilon}},
\qquad
y^{(k)} = \gamma^{(k)} \hat{x}^{(k)} + \beta^{(k)}
$$

into the network. This changes what parameter scales are easy to optimize. In practice it often permits larger learning rates and makes initialization less fragile.

### Regularization

Dropout changes the training distribution itself. Instead of one deterministic hidden layer, training samples many subnetworks. Weight decay changes which solutions are cheap. Data augmentation changes which invariances are rewarded.

These are not afterthoughts. They often dominate the outcome when the architecture is already reasonable.

## Data Choices Are Model Choices

A model only sees the world through the tensors you provide. Important choices include:

- tokenization
- feature extraction
- target construction
- balancing or reweighting
- negative sampling
- train/validation split
- augmentation
- deduplication

For sequence models this can change the task completely. Bahdanau attention was motivated by the failure of fixed-length sentence encodings. GPT-style language modeling depends heavily on tokenization and context length. Recommender training depends heavily on how negatives are sampled.

## Compute, Data, and Scale

For language models, the relationship between loss, model size, data, and compute is quantified well enough to plan against. The variables: $N$ is non-embedding parameter count, $D$ is training tokens, $C$ is training compute in FLOPs, and $L$ is autoregressive cross-entropy loss in nats per token. For dense transformers, training cost is approximately

$$
C \approx 6ND
$$

FLOPs — a forward pass costs about $2N$ FLOPs per token, the backward about $4N$ ([Kaplan et al. 2020](https://arxiv.org/abs/2001.08361), §2.1). Everything below is an empirical fit to training runs, not a derived law; the fits hold impressively over many orders of magnitude but extrapolation beyond the measured range is conjecture.

### Kaplan-style scaling

[Kaplan et al. (2020)](https://arxiv.org/abs/2001.08361) found that when only one resource binds, loss follows a power law in that resource:

$$
L(N) = \left(\frac{N_c}{N}\right)^{\alpha_N}, \quad
L(D) = \left(\frac{D_c}{D}\right)^{\alpha_D}, \quad
\alpha_N \approx 0.076, \;\; \alpha_D \approx 0.095,
$$

with $N_c \approx 8.8 \times 10^{13}$, $D_c \approx 5.4 \times 10^{13}$, and loss along the compute-efficient frontier falling as $L \propto C^{-0.050}$. Width-versus-depth choices matter little inside a reasonable regime; scale dominates shape. Two consequences: larger models are more sample-efficient, and compute-optimal training stops well before convergence. Allocating a fixed budget, the paper concluded $N \propto C^{0.73}$ — spend most of the marginal compute on model size, training **very large models on a relatively modest amount of data and stopping significantly before convergence**.

### Chinchilla: compute-optimal rebalanced

[Hoffmann et al. (2022)](https://arxiv.org/abs/2203.15556) redid the measurement with the learning-rate schedule matched to each token budget — Kaplan's runs reused schedules tuned for longer horizons, which understated how much extra data helps — and fit a parametric loss surface (their eq. 10):

$$
L(N, D) = E + \frac{A}{N^{\alpha}} + \frac{B}{D^{\beta}},
\qquad
E \approx 1.69,\; A \approx 406.4,\; B \approx 410.7,\; \alpha \approx 0.34,\; \beta \approx 0.28.
$$

$E$ is the irreducible entropy of text; the other two terms are the finite-model and finite-data penalties. Minimizing subject to $C = 6ND$ gives $N^\star \propto C^{0.46}$, $D^\star \propto C^{0.54}$: parameters and tokens should scale **together**, roughly 20 tokens per parameter at their measured scales, not $C^{0.73}$ on parameters. The headline validation: Chinchilla (70B params, 1.4T tokens) beat Gopher (280B params, 300B tokens) across benchmarks on the same training budget. The fitted surface shows why — plugging into $L(N,D)$ with both at $C \approx 5.8 \times 10^{23}$ gives 1.937 for Chinchilla's allocation versus 1.993 for Gopher's, and a 4x smaller model is also 4x cheaper at inference.

### A worked sizing example

Suppose the training budget is $C = 10^{23}$ FLOPs. Sweep $N$ with $D = C/6N$ through the Chinchilla fit (computed with the constants above; script run in the repo venv):

| Allocation | $N$ | $D$ | predicted $L$ |
| --- | --- | --- | --- |
| fit optimum | 15B | 1.1T | 2.005 |
| 2x larger model | 30B | 0.56T | 2.013 |
| Gopher-style | 280B | 60B | 2.137 |

The optimum at this budget sits near 15B parameters and 1.1T tokens (about 78 tokens per parameter — the fitted exponents $\alpha \ne \beta$ make the ratio drift upward with budget rather than staying at exactly 20). The instructive part is the asymmetry: doubling parameters past the optimum costs little, but a Gopher-style allocation starved of tokens gives up 0.13 nats, which at these scales is roughly the gap between successive model generations.

### Inference changes the optimum

Compute-optimal is the right target only if training is the only cost. Serving cost scales with $N$ per token generated, forever. [LLaMA](https://arxiv.org/abs/2302.13971) made this argument explicit: the Chinchilla objective "disregards the inference budget," and given a target quality level "the preferred model is not the fastest to train, but the fastest at inference" — so they trained 7B-65B models on 1-1.4T tokens, far past the ~20 tokens/parameter guideline, and [Llama 2](https://arxiv.org/abs/2307.09288) pushed to 2T. The pattern across the well-known models:

| Model | $N$ | $D$ | tokens/param |
| --- | --- | --- | --- |
| GPT-3 (2020) | 175B | 300B | ~1.7 |
| Gopher (2021) | 280B | 300B | ~1.1 |
| Chinchilla (2022) | 70B | 1.4T | 20 |
| LLaMA-7B (2023) | 7B | 1T | ~143 |
| Llama 2-70B (2023) | 70B | 2T | ~29 |

Pre-Chinchilla models were undertrained; post-LLaMA open models are deliberately overtrained, paying extra training compute once to save inference compute on every deployed token. The fitted loss surface quantifies the price: LLaMA-7B's allocation predicts $L \approx 2.052$ where the same $4.2 \times 10^{22}$ FLOPs spent compute-optimally predicts $2.050$ — essentially nothing lost, while inference cost drops by the ratio of model sizes against a compute-optimal ~10B alternative. The flat optimum is what makes overtraining cheap.

> [!tip] The loss optimum is flat; the inference bill is not
> Moving along the fixed-compute curve away from the Chinchilla optimum costs thousandths of a nat, but halving $N$ halves the cost of every token the model ever serves. Whenever deployment volume is large, that asymmetry makes the smaller, overtrained model the right choice even though it is "suboptimal" by the training-only criterion.

Architecture interacts with the same economics. Sparse mixture-of-experts models decouple parameter count from per-token FLOPs, buying capacity without proportional inference cost, at the price of memory, routing complexity, and harder [[ml/serving-systems/parallelism|parallelism]]; small dense overtrained models are the opposite trade, maximally simple to serve.

### Data-side caveats

Token count is not a sufficient statistic for $D$. Deduplication matters (repeated near-duplicates waste budget and encourage memorization), mixture composition matters (code, web, books scale differently and interact with downstream tasks), and data can run out: [Muennighoff et al. (2023)](https://arxiv.org/abs/2305.16264) measured that repeating a fixed corpus for up to ~4 epochs costs almost nothing versus fresh data, with returns decaying to zero by ~16 epochs. All the scaling fits also assume the data distribution is fixed while only quantity varies — a data-quality intervention moves the constants, which is precisely why it can be worth more than parameters.

> [!warning] Scaling fits are interpolations, not laws
> The power-law fits hold over the measured range with the measured data distribution. Extrapolating orders of magnitude beyond the fitted runs, or applying the constants after a major change in data mixture or quality, is conjecture — Chinchilla itself was a correction to Kaplan's fit caused by a subtle learning-rate-schedule confound.

Once the architecture family is competent, data quality and compute allocation usually matter more than small structural edits. The scaling results sharpen that: they say how much loss each marginal parameter or token buys, and the answer is "a power law with a small exponent" for both — so the leverage is in not misallocating between them, and in the constants that data quality controls.

## A Practical Decision Order

When starting a model, I want answers to these:

1. What downstream decision consumes the model output?
2. Which invariances or constraints should the model obey?
3. Is training compute scarce, inference latency scarce, or labeled data scarce?
4. What kinds of errors are expensive?
5. What part of the data pipeline is policy-shaped, biased, or weakly labeled?

That usually narrows the design space quickly.

## Example: Translation

A translation model has:

- one fully observed source sequence
- one generated target sequence
- alignment between them

That points naturally toward an encoder-decoder architecture with cross-attention. The original transformer is exactly that design.

## Example: Long-Context Language Modeling

A language model needs:

- causal dependence
- parallel training over positions
- long-range interaction

That points toward a decoder-only transformer rather than a vanilla RNN.

## Example: Small Scientific Dataset

If data is scarce and structure is known, a smaller model with a stronger prior is often better than a huge flexible one. In that regime, the main failure mode is variance.

## Minimal PyTorch Spec

```python
from dataclasses import dataclass
import torch.nn as nn

@dataclass
class Spec:
    input_dim: int
    output_dim: int
    task: str

def make_head(spec: Spec) -> nn.Module:
    if spec.task == "classification":
        return nn.Linear(spec.input_dim, spec.output_dim)
    if spec.task == "regression":
        return nn.Linear(spec.input_dim, spec.output_dim)
    if spec.task == "autoregressive":
        return nn.Linear(spec.input_dim, spec.output_dim, bias=False)
    raise ValueError(spec.task)
```

This is simple on purpose. Good modeling work starts by pinning down the interface before indulging architecture taste.

## Failure Modes

- loss mismatched to the downstream objective
- architecture blind to known structure
- evaluation split not representative of deployment
- target leakage in preprocessing
- over-investing in parameter count when the bottleneck is noisy or biased data
- over-investing in architectural novelty when the bottleneck is compute or token budget

## Related Notes

- [[ml/deep-learning/neural-networks-from-scratch|Neural Networks from Scratch]]
- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
- [[ml/deep-learning/convolutional-neural-networks|Convolutional Neural Networks]]
- [[ml/serving-systems/parallelism|Parallelism]]
- [[ml/serving-systems/performance-modeling|Performance Modeling]]

## Sources

- [He et al. (2015), Deep Residual Learning for Image Recognition](https://arxiv.org/abs/1512.03385)
- [Vaswani et al. (2017), Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Ioffe and Szegedy (2015), Batch Normalization](https://arxiv.org/abs/1502.03167)
- [Kaplan et al. (2020), Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361)
- [Hoffmann et al. (2022), Training Compute-Optimal Large Language Models](https://arxiv.org/abs/2203.15556)
- [Touvron et al. (2023), LLaMA: Open and Efficient Foundation Language Models](https://arxiv.org/abs/2302.13971)
- [Touvron et al. (2023), Llama 2: Open Foundation and Fine-Tuned Chat Models](https://arxiv.org/abs/2307.09288)
- [Muennighoff et al. (2023), Scaling Data-Constrained Language Models](https://arxiv.org/abs/2305.16264)
- [Srivastava et al. (2014), Dropout](https://www.cs.toronto.edu/~rsalakhu/papers/srivastava14a.pdf)
