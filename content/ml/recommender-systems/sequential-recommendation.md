---
title: Sequential and Graph Recommenders
category: Recommender Systems
tags:
  - recommender systems
  - sequential recommendation
  - graph recommenders
  - implicit feedback
  - exposure bias
  - transformers
  - gnn
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: How recommenders exploit order and graph structure, from self-attentive sequence models to graph-based embedding propagation.
sources:
  - title: Kang and McAuley (2018), Self-Attentive Sequential Recommendation
    url: https://arxiv.org/pdf/1808.09781
    type: paper
  - title: Sun et al. (2019), BERT4Rec
    url: https://arxiv.org/abs/1904.06690
    type: paper
  - title: Ying et al. (2018), PinSage
    url: https://cs.stanford.edu/people/jure/pubs/pinsage-kdd18.pdf
    type: paper
  - title: He et al. (2020), LightGCN
    url: https://arxiv.org/abs/2002.02126
    type: paper
---

## Purpose

Plain collaborative filtering treats user history as an unordered bag. That throws away two strong signals:

- **order**: what happened recently and in what sequence
- **structure**: which users and items sit near each other in the interaction graph

This note covers both.

## Sequential Recommendation

The problem is straightforward to state. A user's next action depends on more than the multiset of items they consumed. Recency matters. Session context matters. The same item can mean different things depending on what came just before it.

If someone watched:

1. "intro to transformers"
2. "attention is all you need explained"
3. "kv cache implementation"

the next relevant item is not the same as it would be after a month of random, unrelated clicks.

## SASRec

SASRec moved sequential recommendation toward self-attention. The model treats a user's history as a sequence and predicts future items from attention over prior positions.

The paper's useful claim is not merely that transformers work. It is that self-attention adapts to dataset density:

- on dense datasets, the model can use longer-range dependencies
- on sparse datasets, it naturally leans harder on recent events

The paper also emphasizes speed. Self-attention lets the model train and serve much more in parallel than older RNN-based sequence models.

## BERT4Rec

BERT4Rec pushes the sequence idea further by using a bidirectional Transformer and a Cloze-style masked-item objective. Instead of only predicting the next item from the left context, it predicts masked items from both left and right context inside the observed sequence.

That buys a stronger sequence representation, though it changes the task. BERT4Rec is not a pure autoregressive next-item model. It is a denoising model for sequence understanding.

The practical takeaway is that sequence modeling does not have to be strictly left-to-right to be useful in recommendation. If the training objective is chosen well, bidirectional context can help.

## What Sequence Models Buy You

Sequence-aware recommenders help when:

- user intent changes quickly
- sessions have local coherence
- recency matters more than long-run taste
- item transitions themselves carry signal

They are especially useful in media, shopping, and short-session surfaces where "what came right before this" is often the strongest feature available.

## What They Do Not Solve

Sequence models still inherit the usual recommender problems:

- exposure bias in the logs
- cold start for fresh items
- weak supervision from implicit feedback
- catalog constraints that the model itself does not understand

They also add a new one: sequence boundaries are messy. Sessionization, truncation length, and negative sampling all matter.

## Graph Recommenders

The user-item log is also a graph. Users connect to items through interactions. Items connect indirectly through shared audiences. Boards, creators, or taxonomies may add more edges.

Graph-based recommenders try to exploit that structure by propagating information over neighborhoods instead of relying only on direct features or sequence order.

## PinSage

PinSage is the production landmark. It uses random walks and graph convolutions to build item embeddings at Pinterest scale. The point is not the exact aggregator. The point is that local graph neighborhoods encode meaningful context that pure ID-based factorization misses.

Graph structure is especially attractive when item content is rich and the interaction graph is huge. Pins linked through boards, images, and co-save behavior contain far more signal than a flat user-item matrix suggests.

## LightGCN

LightGCN is the cleanest corrective note in this line of work. The paper argues that when GCNs are adapted to collaborative filtering, two common neural-network ingredients are often unnecessary:

- feature transformations
- nonlinear activations

Its claim is that simple linear neighborhood aggregation is enough, and often better. The reported result is about **16% relative improvement on average** over NGCF under the same setting.

> [!quote] The ablation finding
> "We empirically find that the two most common designs in GCNs -- feature transformation and nonlinear activation -- contribute little to the performance of collaborative filtering. Even worse, including them adds to the difficulty of training and degrades recommendation performance."
> — [He et al. (2020), LightGCN](https://arxiv.org/abs/2002.02126), abstract

That is a good lesson beyond graph models. If the graph signal is already expressive, piling on extra nonlinear machinery may just make training harder.

## Sequence Versus Graph

These are not rival camps. They answer different questions.

| Signal type | Best question it answers |
| --- | --- |
| Sequential model | What is this user likely to do next, given recent behavior? |
| Graph model | Which users and items occupy nearby regions of the interaction graph? |

A platform can use both:

- sequence models for short-horizon intent
- graph models for broad structural similarity and retrieval

## Where They Fit in a System

- Retrieval can use graph-derived item embeddings.
- Ranking can use sequence encoders over recent activity.
- Feature pipelines often expose both graph and sequence summaries to later models.

Once the catalog and traffic grow, this usually matters more than arguing about one single end-to-end model.

## Related Notes

- [[ml/recommender-systems/recommender-systems|Recommender Systems]]
- [[ml/recommender-systems/two-tower-retrieval|Two-Tower Retrieval]]
- [[ml/recommender-systems/bias-and-marketplace-effects|Bias, Marketplace Effects, and Counterfactual Evaluation]]
- [[systems/research/sparsity-notes|Faster Causal Self Attention]]
- [[ml/recommender-systems/two-tower-retrieval|Two-Tower Retrieval and the MovieLens 100K experiment]]

## Sources

- [Kang and McAuley (2018), Self-Attentive Sequential Recommendation](https://arxiv.org/pdf/1808.09781)
- [Sun et al. (2019), BERT4Rec](https://arxiv.org/abs/1904.06690)
- [Ying et al. (2018), PinSage](https://cs.stanford.edu/people/jure/pubs/pinsage-kdd18.pdf)
- [He et al. (2020), LightGCN](https://arxiv.org/abs/2002.02126)
