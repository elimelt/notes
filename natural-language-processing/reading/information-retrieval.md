---
title: **Indexing and Retrieval in Information Retrieval (IR)**
category: Other
tags: tf-idf, inverted index, precision, recall, interpolated_precision_curve, mean_average_precision, dense_vectors, bert
description: Covers indexing and retrieval techniques in Information Retrieval (IR), including term weighting with tf-idf, inverted index construction, evaluation metrics such as MAP, and dense vector-based approaches using BERT. It also touches on ad hoc retrieval, stop words, and precision/recall trade-offs. The focus is on the technical implementation of IR algorithms.
---

# Information Retrieval

IR in general is the process of obtaining information based on user queries, and can be applied to pretty much any form of media. Probably the most prevalent form of IR that we use every day is through **search engines**.

## Ad Hoc Retrieval

A user poses a **query** to a retrieval system, which then returns an ordered set of **documents** from some **collection**. A **document** refers to whatever unit of text the system indexes and retrieves (e.g. a webpage, a book, a tweet, etc.). The **collection** is the set of all documents that the system has indexed. A **term** can correspond to either a word, phrase, or some other unit of text which documents are indexed by. A query is therefore a set of terms.

A simple architecture for an IR system is as follows:

- Document collection in persistent storage
- Indexing/Preprocessing module to convert documents into an inverted index
- Query processing module to process user queries into query vectors
- Search module to take in query vectors, which then searches the inverted index, returning a set of ranked documents

```txt
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

Usually, we'll want to also persist the inverted index to disk, so that we don't have to recompute it every time we want to search, but online queries will at least usually be served by using an in-memory index.

We can map queries and documents both to vectors based on unigram word counts, and then use cosine similarity between vectors to rank documents. This is an example of the **bag-of-words** model, since words are considered independently of their positions.

### Term weighting (tf-idf)

Using raw word counts isn't very effective. We instead compute a **term weight** for each document word (e.g. **tf-idf** or **BM25**). For tf-idf (term frequency-inverse document frequency), we compute the term frequency (tf) and inverse document frequency (idf) for each term in each document. The tf is the number of times a term appears in a document, and the idf is the log of the total number of documents divided by the number of documents containing the term. The tf-idf score is then the product of these two values.

$$
\text{tf}_{t, d} = \begin{cases}
    1 + \log_{10} \text{count}(t, d) & \text{if count}(t, d) > 0 \\
    0 & \text{otherwise}
\end{cases}
$$

For intuition behind using $log$, if $w_1$ appears $100$ times in a document, and $w_2$ only once, it doesn't mean that $w_1$ is $100$ times more important. Note that alternative definitions of tf exist, e.g. $\log_{10}(1 + \text{count}(t, d))$.

On the other hand, the **document frequency** is the number of documents containing a term. The idf is then defined as:

$$
\text{idf}_t = \log_{10} \left( \frac{N}{\text{df}_t} \right)
$$

where $N$ is the total number of documents in the collection. Therefore, for a word that is contained in **every** document, we'd have an $idf$ of 0. The tf-idf score is then:

$$
\text{tf-idf}_{t, d} = \text{tf}_{t, d} \times \text{idf}_t = \begin{cases}
    (1 + \log_{10} \text{count}(t, d)) \times \log_{10} \left( \frac{N}{\text{df}_t} \right) & \text{if count}(t, d) > 0 \\
    0 & \text{otherwise}
\end{cases}
$$

### Document scoring

We can then score a document $d$ by the cosine of its vector $v_d$ with the query vector $v_q$:

$$
\text{score}(q, d) = cos(v_q, v_d) = \frac{v_q \cdot v_d}{\|v_q\| \|v_d\|}
$$

Alternatively, you can think of the cosine as the dot product of the document and query unit vectors, e.g.:

$$
\text{score}(q, d) = cos(v_q, v_d) = \frac{v_t}{\|v_q\|} \cdot \frac{v_d}{\|v_d\|}
$$

Then, plugging in the tf-idf scores:

$$
\text{score}(q, d) = \sum_{t \in q} \frac{\text{tf-idf}_{t, q}}{\sqrt{\sum_{q_i \in q} \text{tf-idf}^2(q_i, q)}} \times \frac{\text{tf-idf}_{t, d}}{\sqrt{\sum_{d_i \in d} \text{tf-idf}^2(d_i, d)}}
$$

Many variations exist, particularly ones that drop terms in order to reduce computation required. A notable variant is **BM25**, which introduces parameters $k$ to adjust balance between $tf$ and $idf$, and $b$ which controls the importance of document length normalization.

$$
\text{score}(q, d) = \sum_{t \in q} \log \left( \frac{N}{\text{df}_t} \right) \cdot \frac{tf_{t, d}}{k(1 - b + b \cdot \frac{|d|}{|d_{avg}|}) + tf_{t, d}}
$$

Where $d_{avg}$ is the average document length in the collection. When $k = 0$, BM25 reverts to no use of term frequency, just like a binary selection of terms in the query (plus idf). A large $k$ results in raw term frequency (plus idf). $b$ ranges from $1$ (scaling by document length) to $0$ (no scaling). Reasonable defaults for these parameters are $k = [1.2, 2.0]$ and $b = 0.75$.

#### Quick aside: stop words

Stop words are common words that would traditionally be removed from the text before indexing, since they don't add much information. However, tf-idf already does a good job of downweighting common words, so stop words are less important in modern systems, an are often included in the index to make search for phrases easier.

### Inverted Index

Using an inverted index, want to be able to find all documents $d \in C$ that contain a term $q \in Q$. The index is composed of two parts: a **dictionary** and a **postings list**. The dictionary is a collection of terms (designed to be efficiently accessed) which map to a postings list for the term. A posting list is the list of document IDs associated with each term, which can also contain additional metadata (e.g. term frequency, positions, etc.).

This gives us an efficient access pattern for computing tf-idf scores for documents, since we can look up the postings list for each term in the query. However, alternatives, especially for question answering, exist (e.g. [Chen et al. 2017](https://aclanthology.org/P17-1171/)).

### Evaluation

Use **precision**, the fraction of returned docs that are relevant, and **recall**, the fraction of all relevant docs that are returned.

Assume that each document in our IR system is either relevant or not relevant to a query. Further, let $U$ be the set of all relevant documents, $T$ be the set of ranked documents returned, and $R$ be the set of relevant documents in $T$. Then, we can define precision and recall as:

$$
\text{precision} = \frac{|R|}{|T|} \quad \text{recall} = \frac{|R|}{|U|}
$$

Note that recall always increases, e.g. it isn't penalized by returning an irrelevant document. Precision, on the other hand, can decrease if we return irrelevant documents. It is useful to plot precision-recall curves, which show the tradeoff between precision and recall as we vary the number of documents returned.

$$
\text{InterpolatedPrecision} = \text{maxPrecision}(i) \text{ for } i \ge r
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

Assume $R_r$ is the set of relevant documents at or above $r$ in the ranked list. Then, the average precision at $r$ is:

$$
\text{AP} = \frac{1}{|R_r|} \sum_{d \in R_r} \text{Precision}_{r}(d)
$$

Where $\text{Precision}_{r}(d)$ is the precision measured at the rank $r$ where document $d$ was retrieved. For an ensemble of queries $Q$, we average the AP over all queries to get the MAP:

$$
\text{MAP} = \frac{1}{|Q|} \sum_{q \in Q} \text{AP}(q)
$$

## IR with Dense Vectors

tf-idf and BM25 both kind of suck in a way (read vocabulary mismatch problem). Instead, we need to handle synonyms by using dense vectors (as opposed to sparse ones like word counts). This is implemented today via encoders like BERT.

The general approach is to present both the query and the document to a single encoder, allowing the transformer self-attention to see all tokens of both the query and the document, thus also building a representation that is sensitive to the meanings in both. Then, a linear layer can be put on top of the [CLS] token to predict the similarity score for the query and document.

$$
z = BERT(q;[SEP];d)[CLS]
$$

$$
\text{score}(q, d) = \text{softmax}(U(z))
$$

Note: BERT was trained using `[CLS] sen A [SEP] sen B [SEP]`. `[SEP]` is used to help the model distinguish between the two sentences. `[CLS]` is used to represent the entire sentence.

