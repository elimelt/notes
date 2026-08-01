---
title: Indexing and Information Retrieval
aliases:
  - natural-language-processing/reading/information-retrieval
  - /ml/nlp/ppmi
category: Natural Language Processing
tags:
  - tf-idf
  - inverted index
  - precision
  - recall
  - interpolated_precision_curve
  - mean_average_precision
  - dense_vectors
  - bert
date: 2025-01-08
updated: 2026-07-30
status: evergreen
description: Indexing and retrieval techniques for IR systems, covering tf-idf and BM25 term weighting, inverted index construction, evaluation with precision, recall, and MAP, and dense retrieval with BERT-style encoders.
sources:
  - title: Jurafsky & Martin, Speech and Language Processing (3rd ed. draft)
    url: https://web.stanford.edu/~jurafsky/slp3/
    type: textbook
  - title: Chen et al. (2017), Reading Wikipedia to Answer Open-Domain Questions
    url: https://aclanthology.org/P17-1171/
    type: paper
---

## Purpose

Covers the core of ad hoc retrieval. It works through how documents get indexed, how queries get scored against them, and how ranked results get evaluated, then ends with dense retrieval, which handles the vocabulary mismatch baked into term matching. Retrieval pipelines consume [[ml/nlp/reading/tokenization|tokenized document representations]], and retrieval-augmented systems feed results into the [[ml/nlp/prompting|prompting]] workflow. Follows Jurafsky & Martin, [SLP3](https://web.stanford.edu/~jurafsky/slp3/).

Information retrieval is the process of obtaining information based on user queries, and it applies to pretty much any form of media. Search engines are the everyday example.

## Ad Hoc Retrieval

A user poses a **query** to a retrieval system, which returns an ordered set of **documents** from some **collection**. A **document** is whatever unit of text the system indexes and retrieves (a webpage, a book, a tweet). The **collection** is the set of all documents the system has indexed. A **term** is a word, phrase, or other unit of text that documents are indexed by, and a query is a set of terms.

A simple architecture for an IR system has four parts. The document collection sits in persistent storage. An indexing and preprocessing module converts documents into an inverted index. A query processing module turns user queries into query vectors. A search module takes query vectors, searches the inverted index, and returns ranked documents.

```text
persistent storage
 +-----------+++
 | Documents ||| ----> Indexing/Preprocessing ----> Inverted Index
 +-----------+++                                         |
                                                         |
                                                         v

 User Query ---> Query Processing ---(query vector)--> Search
    ^                                                    |
    |                                                    |
    +---------------(ranked docs)------------------------+
```

Usually we'll want to persist the inverted index to disk so we don't recompute it on every search, but online queries will usually be served from an in-memory index.

We can map queries and documents both to vectors based on unigram word counts, then use cosine similarity between vectors to rank documents. This is an example of the **bag-of-words** model, since words are considered independently of their positions.

### Term weighting (tf-idf)

Raw word counts aren't very effective. We instead compute a **term weight** for each document word, such as **tf-idf** or **BM25**. For tf-idf (term frequency-inverse document frequency), we compute the term frequency (tf) and inverse document frequency (idf) for each term in each document, and the tf-idf score is their product.

$$
\text{tf}_{t, d} = \begin{cases}
    1 + \log_{10} \text{count}(t, d) & \text{if count}(t, d) > 0 \\
    0 & \text{otherwise}
\end{cases}
$$

For intuition behind the $\log$, if $w_1$ appears $100$ times in a document and $w_2$ only once, that doesn't make $w_1$ a hundred times more important. Alternative definitions of tf exist, such as $\log_{10}(1 + \text{count}(t, d))$.

The **document frequency** $\text{df}_t$ is the number of documents containing term $t$. The idf is then:

$$
\text{idf}_t = \log_{10} \left( \frac{N}{\text{df}_t} \right)
$$

where $N$ is the total number of documents in the collection. A word contained in **every** document gets an idf of 0. The tf-idf score is then:

$$
\text{tf-idf}_{t, d} = \text{tf}_{t, d} \times \text{idf}_t = \begin{cases}
    (1 + \log_{10} \text{count}(t, d)) \times \log_{10} \left( \frac{N}{\text{df}_t} \right) & \text{if count}(t, d) > 0 \\
    0 & \text{otherwise}
\end{cases}
$$

### Document scoring

Score a document $d$ by the cosine of its vector $v_d$ with the query vector $v_q$:

$$
\text{score}(q, d) = \cos(v_q, v_d) = \frac{v_q \cdot v_d}{\|v_q\| \|v_d\|}
$$

Equivalently, the cosine is the dot product of the query and document unit vectors:

$$
\text{score}(q, d) = \cos(v_q, v_d) = \frac{v_q}{\|v_q\|} \cdot \frac{v_d}{\|v_d\|}
$$

Plugging in the tf-idf scores:

$$
\text{score}(q, d) = \sum_{t \in q} \frac{\text{tf-idf}_{t, q}}{\sqrt{\sum_{t' \in q} \text{tf-idf}_{t', q}^2}} \times \frac{\text{tf-idf}_{t, d}}{\sqrt{\sum_{t' \in d} \text{tf-idf}_{t', d}^2}}
$$

Many variations exist, particularly ones that drop terms to reduce computation. A notable variant is **BM25**, which introduces a parameter $k$ to adjust the balance between tf and idf, and $b$ to control the importance of document length normalization.

$$
\text{score}(q, d) = \sum_{t \in q} \log \left( \frac{N}{\text{df}_t} \right) \cdot \frac{tf_{t, d}}{k(1 - b + b \cdot \frac{|d|}{|d_{avg}|}) + tf_{t, d}}
$$

Here $|d_{avg}|$ is the average document length in the collection. When $k = 0$, BM25 ignores term frequency entirely and acts like a binary selection of query terms weighted by idf. A large $k$ approaches raw term frequency weighting (plus idf). $b$ ranges from $1$ (full scaling by document length) to $0$ (no scaling). Reasonable defaults are $k \in [1.2, 2.0]$ and $b = 0.75$.

#### Quick aside: stop words

Stop words are common words that were traditionally removed from text before indexing, since they add little information. tf-idf already downweights common words, so stop word removal matters less in modern systems, and stop words are often kept in the index to make phrase search easier.

### Inverted Index

With an inverted index, we want to find all documents $d \in C$ that contain a term $q \in Q$. The index has two parts, a **dictionary** and **postings lists**. The dictionary is a collection of terms (designed for efficient access) that maps each term to its postings list. A postings list is the list of document IDs associated with the term, and can carry extra metadata such as term frequency or positions.

This gives an efficient access pattern for computing tf-idf scores, since we can look up the postings list for each query term. Alternatives exist, especially for question answering (see [Chen et al. 2017](https://aclanthology.org/P17-1171/)).

### Evaluation

Use **precision**, the fraction of returned docs that are relevant, and **recall**, the fraction of all relevant docs that are returned.

Assume each document is either relevant or not relevant to a query. Let $U$ be the set of all relevant documents, $T$ the set of ranked documents returned, and $R$ the set of relevant documents in $T$. Then:

$$
\text{precision} = \frac{|R|}{|T|} \quad \text{recall} = \frac{|R|}{|U|}
$$

Recall never decreases as we return more documents, since returning an irrelevant document doesn't penalize it. Precision can decrease as irrelevant documents come back. Precision-recall curves show the tradeoff as the number of returned documents varies. Interpolated precision at recall level $r$ is the maximum precision at any recall level at or above $r$, which smooths out the sawtooth shape of the raw curve:

$$
\text{InterpolatedPrecision}(r) = \max_{i \ge r} \text{Precision}(i)
$$

```python
def interpolate_PR_curve(precision, recall):
    """
    plot averaged precision values at 11 fixed levels of recall (0 to 100 by 10)
    """
    recall_levels = np.linspace(0, 1, 11)
    interpolated_precision = np.zeros_like(recall_levels)
    for i, r in enumerate(recall_levels):
        interpolated_precision[i] = np.max(precision[recall >= r])
    return interpolated_precision, recall_levels
```

#### Mean Average Precision (MAP)

Let $R_r$ be the set of relevant documents at or above rank $r$ in the ranked list. The average precision is:

$$
\text{AP} = \frac{1}{|R_r|} \sum_{d \in R_r} \text{Precision}_{r}(d)
$$

where $\text{Precision}_{r}(d)$ is the precision measured at the rank where document $d$ was retrieved. For an ensemble of queries $Q$, average the AP over all queries to get the MAP:

$$
\text{MAP} = \frac{1}{|Q|} \sum_{q \in Q} \text{AP}(q)
$$

## IR with Dense Vectors

tf-idf and BM25 only give credit when query terms literally appear in the document. A query phrased with synonyms of the document's vocabulary scores poorly no matter how relevant the document is. This is the vocabulary mismatch problem. Dense vector representations let semantically related text match without shared terms, implemented today with encoders like BERT, in contrast to the sparse count-based vectors above.

One approach presents the query and document together to a single encoder, letting transformer self-attention see all tokens of both, so the representation is sensitive to the meanings of each. A linear layer on top of the [CLS] token then predicts the similarity score for the pair:

$$
z = BERT(q;[SEP];d)[CLS]
$$

$$
\text{score}(q, d) = \text{softmax}(U(z))
$$

Note: BERT was trained using `[CLS] sen A [SEP] sen B [SEP]`. `[SEP]` helps the model distinguish the two sentences, and `[CLS]` represents the whole input.

## Executable PPMI Experiment

Positive pointwise mutual information is a count-based bridge between sparse term statistics and semantic vectors. The companion notebook builds a PPMI matrix over the notes corpus and plots selected word associations. It demonstrates corpus-derived geometry rather than a production retrieval benchmark.

[Build the PPMI matrix](/ml/nlp/ppmi.ipynb)

## Related notes

- [[systems/databases/foundations/ch3-storage-and-retrieval|Storage and Retrieval Techniques for Database Systems]]

## Sources

- [Jurafsky & Martin, Speech and Language Processing (3rd ed. draft)](https://web.stanford.edu/~jurafsky/slp3/)
- [Chen et al. (2017), Reading Wikipedia to Answer Open-Domain Questions](https://aclanthology.org/P17-1171/)
