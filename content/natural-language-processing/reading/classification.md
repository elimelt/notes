---
title: Classification with Multinomial Naive Bayes
category: Natural Language Processing
tags:
  - classification
  - naive bayes
  - multinomial naive bayes
  - text classification
  - bag of words
  - laplace smoothing
date: 2025-02-12
updated: 2026-07-30
status: evergreen
description: Multinomial Naive Bayes for text classification, covering the bag-of-words representation, the conditional independence assumption, Laplace-smoothed training, and evaluation with precision and recall.
sources:
  - title: Jurafsky & Martin, Speech and Language Processing (3rd ed. draft)
    url: https://web.stanford.edu/~jurafsky/slp3/
    type: textbook
---

## Purpose

Explains multinomial Naive Bayes, a probabilistic text classifier built on Bayes' rule and a strong independence assumption. It covers the model, why the independence assumption makes estimation tractable, and the smoothing fix that makes it work in practice. The classifier developed here is extended in [[natural-language-processing/reading/multinomial-logistic-regression|multinomial logistic regression]] and contrasted with [[natural-language-processing/reading/neural-networks|feedforward neural networks]]. Follows Jurafsky & Martin, [SLP3](https://web.stanford.edu/~jurafsky/slp3/).

## Setup

A classifier takes an input $x$ and a fixed set of output classes $Y = \{y_1, y_2, \ldots, y_M\}$ and returns a predicted class $y \in Y$. Text classification often writes $c$ for class instead of $y$, and $d$ for document instead of $x$.

In the supervised setting we have a training set of $N$ documents, each hand-labeled with a class: $\{(d_1, c_1), \ldots, (d_N, c_N)\}$. The goal is a classifier that maps a new document $d$ to its correct class $c \in C$, where $C$ is some set of useful document classes.

## Multinomial Naive Bayes

Represent the document as a **bag of words**: keep the word counts, discard the order. For a document $d$, output the class $\hat{c}$ that maximizes the posterior $P(c|d)$:

$$
\begin{aligned}
\hat{c} &= \arg \max_{c \in C} P(c|d) \\
  &= \arg \max_{c \in C} \frac{P(d|c)P(c)}{P(d)}
\end{aligned}
$$

$P(d|c)$ is the likelihood and $P(c)$ is the prior. $P(d)$ is the same for every class, so it drops out of the argmax. Writing the document as features $f_1, f_2, \ldots, f_n$:

$$
\hat{c} = \arg \max_{c \in C} P(f_1, f_2, \ldots, f_n | c)P(c)
$$

### The Naive Bayes assumption

Estimating the joint likelihood $P(f_1, \ldots, f_n | c)$ directly is hopeless, since the number of feature combinations blows up with document length. Naive Bayes assumes the features are conditionally independent given the class, so the likelihood factors:

$$
P(f_1, f_2, \ldots, f_n | c) = \prod_{i=1}^n P(f_i | c)
$$

For text, the features are the words at each position, giving:

$$
c_{\text{NB}} = \arg \max_{c \in C} P(c) \prod_{i=1}^n P(w_i | c)
$$

Multiplying many small probabilities underflows floating point, so compute in log space. The log is monotonically increasing, so it preserves the argmax:

$$
c_{\text{NB}} = \arg \max_{c \in C} \left[ \log P(c) + \sum_{i=1}^n \log P(w_i | c) \right]
$$

### Training

Estimate the prior as the fraction of training documents with class $c$:

$$
\hat{P}(c) = \frac{N_c}{N_{\text{doc}}}
$$

The maximum likelihood estimate of the word likelihood is a count ratio over the concatenation of all training documents in class $c$:

$$
\hat{P}(w_i | c) = \frac{count(w_i, c)}{\sum_{w \in V} count(w, c)}
$$

This breaks on any word that never appears with class $c$ in training. Its estimated probability is zero, and one zero factor wipes out the entire product no matter how strong the other evidence is. Laplace (add-one) smoothing fixes it:

$$
\hat{P}(w_i | c) = \frac{count(w_i, c) + 1}{\sum_{w \in V} count(w, c) + |V|}
$$

```text
function TRAIN_NAIVE_BAYES(D, C) returns V, log_P(c), log_P(w|c)
  for each class c ∈ C do
    Ndoc = number of documents in D
    Nc = number of documents from D in class c
    logprior[c] = log(Nc / Ndoc)
    V = vocab of D
    bigdoc[c] = concat(d ∈ D where d.class = c)
    for each word w ∈ V do
      count[w, c] = number of times w appears in bigdoc[c]
      loglikelihood[w, c] = log [(count[w, c] + 1) / (sum_{w' ∈ V} count[w', c] + |V|)]

  return logprior, loglikelihood, V

function TEST_NAIVE_BAYES(testdoc, logprior, loglikelihood, C, V) returns best_c
  for each class c ∈ C do
    sum[c] = logprior[c]
    for each position i in testdoc do
      word = testdoc[i]
      if word ∈ V then
        sum[c] = sum[c] + loglikelihood[word, c]

  return argmax_c sum[c]
```

### Evaluation

Evaluate against gold labels with a confusion matrix. Precision is the fraction of predicted positives that are correct, and recall is the fraction of actual positives the classifier finds. F1 combines the two as their harmonic mean.

## Sources

- [Jurafsky & Martin, Speech and Language Processing (3rd ed. draft)](https://web.stanford.edu/~jurafsky/slp3/)
