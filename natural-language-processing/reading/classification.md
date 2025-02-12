---
title: Classification with Multinomial Naive Bayes
category: Natural Language Processing
tags: classification, naive bayes, multinomial naive bayes, text classification, bag of words, laplace smoothing
description: Overview of classification with Multinomial Naive Bayes, including the Naive Bayes assumption, training, and evaluation.
---

# Classification

Take an input $x$ and a fixed set of output classes $Y = \{y_1, y_2, \ldots, y_M\}$ and return a predicted class $y \in Y$.

Text classification sometimes uses $c$ for class instead of $y$ as output, and $d$ for document instead of $x$ as input.

In the supervised situation we have a training set of $N$ documents that have each been hand labeled with a class: $\{(d_1, c_1),....,(d_N, c_N)\}$. Our goal is to learn a classifier that is capable of mapping from a new document $d$ to its correct class $c \in C$, where $C$ is some set of useful document classes.

## Multinomial Naive Bayes

Represent text as **bag of words**. For a document $d$ out of all all classes $c \in C$, outputs $\hat{c}$ that maximizes $P(c|d)$.

$$
\begin{align*}
\hat{c} &= \arg \max_{c \in C} P(c|d) \\
  &= \arg \max_{c \in C} \frac{P(d|c)P(c)}{P(d)}
\end{align*}
$$

Where $P(d | c)$ is the likelihood, and $P(c)$ is the prior. Or with features $f_1, f_2, \ldots, f_n$:

$$
\hat{c} = \arg \max_{c \in C} P(f_1, f_2, \ldots, f_n | c)P(c)
$$

### Naive Bayes Assumption

$$
P(f_1, f_2, \ldots, f_n | c) = \prod_{i=1}^n P(f_i | c)
$$

$$
\begin{align*}
C_{\text{NB}} &= \arg \max_{c \in C} P(c) \prod_{i=1}^n P(w_i | c) \\
&= \arg \max_{c \in C} \log P(c) + \sum_{i=1}^n \log P(w_i | c)
\end{align*}
$$

### Training

Estimate $P(c)$: the prior probability of each class.

$$
\hat{P}(w_i | c) = \frac{count(w_i, c) + 1}{\sum_{w \in V} count(w, c) + |V|}
$$

Or with Laplace smoothing:

$$
\hat{P}(w_i | c) = \frac{count(w_i, c) + 1}{\sum_{w \in V} count(w, c) + |V|}
$$

```
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

Use a confusion matrix, precision, recall, and F1 score.
