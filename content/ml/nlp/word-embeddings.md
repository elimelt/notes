---
title: Word Embeddings and Distributional Semantics
category: Natural Language Processing
tags:
  - word embeddings
  - distributional semantics
  - word2vec
  - glove
  - representation learning
date: 2026-08-01
status: draft
description: Dense lexical representations from the distributional hypothesis through word2vec and GloVe, why they work, where their geometry misleads, and how they connect to transformer token embeddings, with a verified toy skip-gram implementation.
sources:
  - title: Mikolov et al. (2013), Efficient Estimation of Word Representations in Vector Space
    url: https://arxiv.org/abs/1301.3781
    type: paper
  - title: Mikolov et al. (2013), Distributed Representations of Words and Phrases and their Compositionality
    url: https://arxiv.org/abs/1310.4546
    type: paper
  - title: Pennington et al. (2014), GloVe - Global Vectors for Word Representation
    url: https://aclanthology.org/D14-1162.pdf
    type: paper
  - title: Bengio et al. (2003), A Neural Probabilistic Language Model
    url: https://www.jmlr.org/papers/volume3/bengio03a/bengio03a.pdf
    type: paper
---

## Purpose

This note fills the gap between sparse count representations like [[ml/nlp/ppmi|PPMI]] and [[ml/nlp/reading/information-retrieval|tf-idf]] on one side and transformer models on the other: how dense word vectors are trained, why they capture meaning, and where their geometry misleads. It ends at the boundary where static embeddings hand off to the learned embedding matrices inside [[ml/deep-learning/decoder-only-transformers|decoder-only transformers]].

## The distributional hypothesis

The idea predates neural networks by decades. Harris (1954) argued that "difference of meaning correlates with difference of distribution," and Firth (1957) gave it the slogan: you shall know a word by the company it keeps. Operationally: represent each word by statistics of the contexts it appears in, and words with similar meanings end up with similar representations, because they occur in similar contexts.

Sparse methods implement this directly. A co-occurrence matrix (optionally reweighted, as in [[ml/nlp/ppmi|PPMI]]) gives each word a vector as long as the vocabulary. These vectors work for retrieval-style tasks but have two structural problems: dimensionality equal to vocabulary size, and no sharing between related contexts. Seeing "the cat sat" teaches a count model nothing about "the dog sat" — the counts live in different columns.

[Bengio et al. (2003)](https://www.jmlr.org/papers/volume3/bengio03a/bengio03a.pdf) diagnosed this as the curse of dimensionality for n-gram language models and made the key move: learn a shared real-valued vector per word (they used ~60 dimensions) jointly with a neural next-word predictor, so that one observed sentence transfers probability mass to the exponentially many similar sentences reachable by swapping semantically close words. Their neural LM beat modified Kneser-Ney trigrams on Brown and AP News perplexity, at a steep 2003-era cost (weeks on 40 CPUs). The lasting contribution was not the LM but the recipe: embeddings as the first layer of a network trained on a prediction task.

## word2vec: prediction as the training signal

[Mikolov et al. (2013)](https://arxiv.org/abs/1301.3781) stripped Bengio's model down to the embeddings themselves — no hidden layer, just a log-linear predictor — which made training fast enough for billions of tokens. Two architectures:

- **CBOW** averages the context vectors and predicts the center word.
- **Skip-gram** uses the center word to predict each context word within a window of radius $c$, maximizing

$$
\frac{1}{T}\sum_{t=1}^{T} \sum_{\substack{-c \le j \le c \\ j \ne 0}} \log p(w_{t+j} \mid w_t).
$$

Skip-gram tends to win on rare words; CBOW is faster. The bottleneck in both is the softmax over the vocabulary, $p(w_O \mid w_I) = \exp(v'^{\top}_{w_O} v_{w_I}) / \sum_w \exp(v'^{\top}_w v_{w_I})$, whose denominator costs $O(|V|)$ per update.

[The follow-up paper](https://arxiv.org/abs/1310.4546) replaced it with **negative sampling**: turn the multiclass prediction into a set of binary discriminations, one real (word, context) pair against $k$ sampled fake ones:

$$
\log \sigma(v'^{\top}_{w_O} v_{w_I}) + \sum_{i=1}^{k} \mathbb{E}_{w_i \sim P_n(w)} \left[ \log \sigma(-v'^{\top}_{w_i} v_{w_I}) \right],
$$

with noise distribution $P_n(w) \propto U(w)^{3/4}$ (the 3/4 power flattens the unigram distribution so rare words get sampled more) and $k$ = 5-20 for small corpora, 2-5 at billion-word scale. Two further tricks from the same paper: subsampling frequent words (discard tokens of very common words with probability tied to their frequency, since "the" co-occurring with everything carries little signal) and, jointly, these cut training to under a day for 1.6B words on one machine.

The famous result is the analogy geometry: $\text{vec}(\text{king}) - \text{vec}(\text{man}) + \text{vec}(\text{woman})$ lands nearest $\text{vec}(\text{queen})$. On the paper's semantic/syntactic analogy test set, 300-dimensional skip-gram reached roughly 50-65% total accuracy depending on training data, where prior NNLM embeddings scored under 25% ([Mikolov et al. 2013](https://arxiv.org/abs/1301.3781), Tables 3-4). Relations like capital-country and adjective-adverb are approximately parallel offsets in the space, which is the concrete sense in which "meaning" became linear structure.

## GloVe: regression on global counts

[Pennington et al. (2014)](https://aclanthology.org/D14-1162.pdf) observed that what discriminates meaning is not co-occurrence probabilities but their *ratios*. From their corpus (their Table 1): for the pair ice/steam, the probe word "solid" has $P(\text{solid}\mid\text{ice})/P(\text{solid}\mid\text{steam}) = 8.9$, "gas" has ratio $0.085$, while "water" and "fashion" — related to both or neither — have ratios near 1. The ratio isolates the axis that separates the pair; raw probabilities are dominated by overall word frequency.

GloVe builds this in by fitting log co-occurrence counts with a weighted least-squares objective over the global count matrix $X$:

$$
J = \sum_{i,j=1}^{|V|} f(X_{ij}) \left( w_i^\top \tilde{w}_j + b_i + \tilde{b}_j - \log X_{ij} \right)^2,
\qquad
f(x) = \begin{cases} (x/x_{\max})^{\alpha} & x < x_{\max} \\ 1 & \text{otherwise} \end{cases}
$$

with $x_{\max} = 100$, $\alpha = 3/4$. The weighting keeps the huge mass of frequent pairs from dominating while ignoring the noise in singleton counts (and zero counts drop out entirely, so the sum is over observed pairs). Because differences of the fitted quantities are log-ratios, the ratio structure becomes vector arithmetic by construction. Where skip-gram makes many stochastic passes over windows, GloVe makes one pass to build counts and then fits them, using the same information (word2vec with negative sampling is implicitly factorizing a shifted PMI matrix, which is why the two land in similar places). On the analogy task GloVe reported results competitive with or better than word2vec at equal dimension and corpus.

## Where the geometry misleads

> [!warning] Distributional similarity is not semantic similarity
> These spaces put words close together when they appear in similar contexts. Antonyms, senses of a polysemous word, and hub vectors all exploit that gap in different ways.

Nearest-neighbor structure in these spaces rewards distributional similarity, which is not the same as semantic similarity:

- **Antonyms cluster together.** "cheap" and "expensive" occur in nearly identical contexts, so their vectors are close. Distance cannot distinguish synonym from antonym.
- **One vector per type.** Polysemous words get the frequency-weighted average of their senses; "bank" sits between finance and rivers, near neither cleanly. This is the limitation contextual models were built to fix.
- **Hubness.** In high dimensions some vectors become nearest neighbors of a disproportionate number of words, degrading k-NN retrieval; cross-lingual embedding work introduced corrections like CSLS specifically for this.
- **Analogy arithmetic is fragile.** The standard evaluation excludes the three input words from the candidate set; without that exclusion, the nearest vector to king - man + woman is usually king itself. Accuracy also drops sharply for rare words and relations beyond the curated test set.

## Toy skip-gram with negative sampling

A minimal implementation on a synthetic corpus with two topic clusters, verified in the repo venv. Words within a topic co-occur; the embedding should recover the cluster structure.

```python
import numpy as np

rng = np.random.default_rng(0)
animals = ["cat", "dog", "horse", "cow"]
tech = ["cpu", "gpu", "ram", "disk"]
vocab = animals + tech
idx = {w: i for i, w in enumerate(vocab)}

corpus = []
for _ in range(2000):                       # sentences stay within one topic
    topic = animals if rng.random() < 0.5 else tech
    corpus.append([idx[w] for w in rng.choice(topic, size=5)])

V, d, k, lr = len(vocab), 8, 3, 0.05
W_in = rng.normal(0, 0.1, (V, d))           # center-word vectors
W_out = rng.normal(0, 0.1, (V, d))          # context-word vectors
sigmoid = lambda x: 1 / (1 + np.exp(-x))

for epoch in range(5):
    for sent in corpus:
        for t, center in enumerate(sent):
            for ctx in sent[max(0, t-2):t] + sent[t+1:t+3]:
                negs = rng.integers(0, V, size=k)
                for target, label in [(ctx, 1.0)] + [(n, 0.0) for n in negs]:
                    v, u = W_in[center].copy(), W_out[target].copy()
                    g = sigmoid(v @ u) - label   # d loss / d score
                    W_out[target] -= lr * g * v  # symmetric updates from
                    W_in[center] -= lr * g * u   # pre-update copies

sims = W_in @ W_in.T / (np.linalg.norm(W_in, axis=1)[:, None] * np.linalg.norm(W_in, axis=1))
same = np.mean([sims[idx[a], idx[b]] for a in animals for b in animals if a != b])
cross = np.mean([sims[idx[a], idx[b]] for a in animals for b in tech])
print(f"within-topic cosine: {same:.3f}, cross-topic: {cross:.3f}")
```

Measured output: `within-topic cosine: 0.990, cross-topic: 0.132`. Words that share contexts collapse onto nearly the same direction while the two topics stay separated — the distributional hypothesis reduced to eight words and forty lines. (With only two hard topic clusters the within-topic similarity is more extreme than in real corpora, where 0.5-0.8 between close neighbors is typical.)

## Bridge to transformers

A transformer's input layer is the same object: a learned embedding matrix $E \in \mathbb{R}^{|V| \times d}$ over [[ml/nlp/reading/tokenization|subword tokens]] rather than words, trained end-to-end on next-token prediction — skip-gram's training signal generalized from a window to the full causal context, with the log-linear predictor replaced by the transformer stack. The difference is what happens above the lookup: static embeddings stop there, so every occurrence of a type shares one vector, while attention layers produce token representations conditioned on the sentence, which is what resolves polysemy. Static embeddings survive where their economics win: initialization in low-resource settings, lightweight similarity and retrieval, and interpretability studies.

## Sources

- [Mikolov et al. (2013), Efficient Estimation of Word Representations in Vector Space](https://arxiv.org/abs/1301.3781)
- [Mikolov et al. (2013), Distributed Representations of Words and Phrases and their Compositionality](https://arxiv.org/abs/1310.4546)
- [Pennington et al. (2014), GloVe: Global Vectors for Word Representation](https://aclanthology.org/D14-1162.pdf)
- [Bengio et al. (2003), A Neural Probabilistic Language Model](https://www.jmlr.org/papers/volume3/bengio03a/bengio03a.pdf)

## Related notes

- [[ml/nlp/ppmi|PPMI]]
- [[ml/nlp/reading/tokenization|Tokenization, Segmentation, and Edit Distance]]
- [[ml/nlp/reading/information-retrieval|Indexing and Information Retrieval]]
- [[ml/nlp/reading/neural-networks|Feedforward Neural Networks]]
- [[ml/deep-learning/decoder-only-transformers|Decoder-Only Transformers]]
