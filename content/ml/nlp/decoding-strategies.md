---
title: Decoding Strategies for Language Models
category: Natural Language Processing
tags:
  - decoding
  - beam search
  - sampling
  - top-k
  - top-p
  - language modeling
date: 2026-08-01
status: draft
description: How autoregressive models are turned into sequences at inference time, covering greedy decoding, beam search, temperature, top-k, top-p, and repetition penalties, with toy-logit code examples.
sources:
  - title: Holtzman et al. (2020), The Curious Case of Neural Text Degeneration
    url: https://arxiv.org/abs/1904.09751
    type: paper
  - title: Murray and Chiang (2018), Correcting Length Bias in Neural Machine Translation
    url: https://aclanthology.org/W18-6322.pdf
    type: paper
  - title: Keskar et al. (2019), CTRL - A Conditional Transformer Language Model for Controllable Generation
    url: https://arxiv.org/abs/1909.05858
    type: paper
  - title: Hugging Face Transformers, Generation strategies
    url: https://huggingface.co/docs/transformers/main/en/generation_strategies
    type: docs
---

## Purpose

A trained autoregressive model gives you $p(x_t \mid x_{<t})$, a distribution over the next token. It does not give you a sequence. This note covers the step that turns the distribution into text: greedy decoding and beam search as search procedures, then temperature, top-k, top-p, and repetition penalties as distribution shaping, and finally where the choice of strategy interacts with the serving stack. The model side of the factorization lives in [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]].

## Decoding as search

A decoder-only model factorizes sequence probability as $p(x_{1:T}) = \prod_t p(x_t \mid x_{<t})$. Finding the most probable sequence under this factorization is a search over a tree that branches by the vocabulary size at every step, so exact search is intractable and every practical decoder is a heuristic.

Greedy decoding takes $\arg\max_x p(x \mid x_{<t})$ at each step. It is cheap and deterministic, and it can commit to a locally likely token that leads to a globally poor continuation, since the product of conditionals is not maximized by maximizing each factor.

Beam search keeps the $k$ highest-scoring partial hypotheses at each step, extends each by every token, and re-prunes to $k$. It approximates the mode of the sequence distribution far better than greedy, which is why it became standard in machine translation. The [Hugging Face generation docs](https://huggingface.co/docs/transformers/main/en/generation_strategies) recommend it for input-grounded tasks like translation and captioning, where the output is tightly constrained by the input and the mode is a sensible target.

### The beam curse and length bias

Wider beams should find higher-probability sequences, and they do. In translation this makes BLEU worse, not better. [Murray and Chiang (2018)](https://aclanthology.org/W18-6322.pdf) show that wider beams find shorter translations, and trace both problems to label bias: locally normalized models multiply a factor less than one per token, so shorter hypotheses accumulate less probability decay and the true mode of the model is biased toward brevity. Their experiments show that correcting the brevity problem almost eliminates the beam problem.

The standard corrections rescore a hypothesis $e$ with score $s(e)$ by length $|e|$:

- Length normalization: $s'(e) = s(e) / |e|^{\alpha}$ with tunable $\alpha$.
- Per-word reward: $s'(e) = s(e) + \gamma\,|e|$, which [Murray and Chiang](https://aclanthology.org/W18-6322.pdf) find works slightly better and is easier to apply to partial hypotheses inside the beam.

## Decoding as distribution shaping

Open-ended generation flips the problem. [Holtzman et al. (2020)](https://arxiv.org/abs/1904.09751) show that maximizing likelihood at decode time produces text that is bland and repetitive, and that models fall into repetition loops that likelihood actually rewards. Human text is not a sequence of maximally probable tokens. So instead of searching for the mode, sampling-based decoding draws from a reshaped version of the model's distribution.

All of the following operate on the logits $x_i$ before the softmax, or on the resulting probabilities, at each step.

**Temperature** rescales logits before the softmax:

$$
p_i = \frac{\exp(x_i / T)}{\sum_j \exp(x_j / T)}
$$

$T < 1$ sharpens the distribution toward the argmax, $T > 1$ flattens it, and $T \to 0$ recovers greedy decoding. Temperature alone cannot remove the tail, only reweight it.

**Top-k** keeps the $k$ most probable tokens, renormalizes, and samples. The truncation size is fixed, which is the weakness: when the distribution is flat, $k$ tokens may cut off many reasonable options, and when it is peaked, $k$ tokens include junk.

**Top-p (nucleus) sampling** truncates adaptively. [Holtzman et al.](https://arxiv.org/abs/1904.09751) define the nucleus $V^{(p)}$ as the smallest set of tokens whose cumulative probability reaches $p$:

$$
\sum_{x \in V^{(p)}} p(x \mid x_{<t}) \ge p
$$

Sampling then renormalizes over $V^{(p)}$. Their argument is that the tail of the distribution is unreliable, individually low-probability tokens that jointly hold real mass, and sampling from it is what derails generations. The nucleus adapts per step: they observe it typically ranges from one to around a thousand candidates, and with GPT-2 large, $p \approx 0.95$ produced text closest to human statistics on their metrics.

**Repetition penalty** discounts tokens that already appeared. The formulation from [CTRL](https://arxiv.org/abs/1909.05858) divides the logit of any previously generated token by $\theta$ inside the softmax, with $\theta \approx 1.2$ reported as a good balance between staying truthful to the model and avoiding loops. Hugging Face exposes this as `repetition_penalty`, plus a hard variant `no_repeat_ngram_size` that forbids repeating any n-gram outright, which can misfire on text that legitimately repeats, like a name appearing many times.

These compose. A common stack is temperature, then top-k or top-p truncation, then renormalize and sample.

## Sampling from toy logits

The whole pipeline is a few lines over a logit vector. This example applies temperature, top-k, and top-p to a toy distribution:

```python
import numpy as np

rng = np.random.default_rng(0)
logits = np.array([4.0, 3.0, 2.5, 1.0, 0.5, -1.0, -2.0, -5.0])

def softmax(x):
    z = np.exp(x - x.max())
    return z / z.sum()

def sample(logits, temperature=1.0, top_k=None, top_p=None):
    logits = logits / temperature
    probs = softmax(logits)
    order = np.argsort(probs)[::-1]          # tokens by descending probability
    keep = np.ones_like(probs, dtype=bool)
    if top_k is not None:
        keep[order[top_k:]] = False
    if top_p is not None:
        csum = np.cumsum(probs[order])
        cut = np.searchsorted(csum, top_p) + 1   # smallest prefix with mass >= p
        keep[order[cut:]] = False
    probs = np.where(keep, probs, 0.0)
    probs /= probs.sum()
    return rng.choice(len(probs), p=probs), probs

token, probs = sample(logits, temperature=0.8, top_p=0.9)
print(np.round(probs, 3))   # [0.695 0.199 0.107 0.    0.    0.    0.    0.   ]
print(token)                # 0
```

At $T = 0.8$ with $p = 0.9$, the nucleus holds three of eight tokens and the tail five are zeroed out. Raise the temperature to 1.5 and the same $p = 0.9$ nucleus grows to four tokens, which is the adaptivity that fixed top-k lacks.

Greedy and beam search over the same interface are a search loop rather than a sampling call. A minimal beam step scores every extension of every hypothesis and keeps the top $k$ by summed log-probability, which is where the length bias enters: each extension adds a negative term, so shorter hypotheses look better unless the score is corrected.

## Task tradeoffs

The search-versus-sampling split follows the task. When the output is heavily determined by the input, translation, summarization, speech transcription, the mode is meaningful and beam search with a length correction is the right tool. When the task is open-ended, continuation, dialogue, story generation, the mode is degenerate and truncated sampling wins; this is the central empirical claim of [Holtzman et al.](https://arxiv.org/abs/1904.09751), who found beam search text far more repetitive than human text while nucleus sampling matched human statistics most closely. The objective mismatch is the same in both cases. Likelihood was the training objective, and decoding gets to choose how literally to take it.

## Serving constraints

Decoding policy is not free at serving time. Beam search multiplies the KV-cache footprint by the beam width, since each hypothesis needs its own cache, which cuts directly into the memory budget described in [[ml/serving-systems/memory-management|Memory Management in LLM Serving Systems]]. Sampling parameters vary per request, so a batched server applies temperature and truncation per row of the logit matrix, cheap relative to the forward pass but part of every decode step in the loop described in [[ml/serving-systems/batching|Batching]]. Speculative decoding interacts with the sampling policy itself: the rejection rule in [[ml/serving-systems/speculative-decoding|Speculative Decoding]] preserves the target distribution under sampling, and greedy or heavily truncated policies change draft acceptance rates. Assisted generation in the [Hugging Face docs](https://huggingface.co/docs/transformers/main/en/generation_strategies) is the same idea exposed as a decoding strategy.

## Sources

- [Holtzman et al. (2020), The Curious Case of Neural Text Degeneration](https://arxiv.org/abs/1904.09751)
- [Murray and Chiang (2018), Correcting Length Bias in Neural Machine Translation](https://aclanthology.org/W18-6322.pdf)
- [Keskar et al. (2019), CTRL: A Conditional Transformer Language Model for Controllable Generation](https://arxiv.org/abs/1909.05858)
- [Hugging Face Transformers, Generation strategies](https://huggingface.co/docs/transformers/main/en/generation_strategies)

## Related notes

- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
- [[ml/serving-systems/speculative-decoding|Speculative Decoding in LLM Serving Systems]]
- [[ml/nlp/prompting|Prompting Language Models]]
