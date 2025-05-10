---
title: Recommender Systems
category: Machine Learning Systems
tags: recommender systems, collaborative filtering, matrix factorization, matrix completion, personalization, cold-start problem
description: A brief overview of recommender systems, including their challenges, approaches, and applications.
---

## Recommender Systems

**Personalization and Data Sparsity**
- Personalization leverages user data (preferences, activities) to recommend items users might like.
- Challenge: User-item interaction data is sparse-most users rate only a few items.
- Collaborative filtering: Users are likely to enjoy items liked by similar users.

**Types of Feedback**
- Explicit feedback: Ratings, purchase history, rankings.
- Implicit feedback: Browsing history, time spent, clicks-requires preprocessing.

**Major Challenges**
- Sparsity of data.
- Cold-start problem: Hard to recommend for new users/items with no history.
- Changing interests: User preferences and item popularity shift over time.
- Scalability: Need algorithms that efficiently handle millions of users/items.

---

## Approaches to Recommendation

**Popularity-Based**
- Recommend most popular items (no personalization).

**Classifier-Based**
- Treat as a classification problem:  
  Input: $ x =$ (user features, item features), Output: $ y = +1$ (like) or $ -1$ (dislike).
- Pros: Personalized, can include extra features.
- Cons: Feature engineering is hard, often underperforms collaborative filtering.

**Co-Occurrence-Based**
- Use normalized co-occurrence matrix $ C$:
  $$
  C_{ij} = \frac{\text{users who bought both } i \text{ and } j}{\text{users who bought } i \text{ or } j}
  $$
- For a user who bought items $ A$ and $ B$, score for item $ X$:
  $$
  \text{Score}(X) = \frac{C_{XA} + C_{XB}}{2}
  $$

---

## Matrix Factorization and Completion

**Matrix Factorization Model**
- Represent user $ u$ and item $ v$ with feature vectors $ L_u$ and $ R_v$.
- Predicted rating:
  $$
  \text{Rating}(u, v) = L_u^T R_v
  $$
- The ratings matrix $ M$ is approximated by $ M \approx L R^T$.

**Matrix Completion Problem**
- Given observed ratings, estimate missing entries by finding $ L$ and $ R$ that minimize:
  $$
  \min_{L, R} \sum_{(u,v): r_{uv} \text{ observed}} (L_u^T R_v - r_{uv})^2
  $$

**Degrees of Freedom**
- For $ m$ movies, $ n$ users, and $ k$ topics:
  $$
  \text{Degrees of freedom} = k(m + n)
  $$

**Coordinate Descent Algorithm**
- Alternately fix $ R$ and optimize $ L$, then fix $ L$ and optimize $ R$.
- Each step reduces to multiple independent linear regression problems.

**Regularization to Prevent Overfitting**
- Add $ \ell_2$ regularization:
  $$
  \min_{L, R} \sum_{(u,v): r_{uv} \text{ observed}} (L_u^T R_v - r_{uv})^2 + \lambda (\|L_u\|^2 + \|R_v\|^2)
  $$

---

## Extensions & Cold-Start Solutions

**Feature-Based Linear Models**
- Represent items by feature vector $ \phi(v)$, learn global weights $ w$:
  $$
  r_{uv} \approx w \cdot \phi(v)
  $$
- Minimize:
  $$
  \min_w \sum_{(u,v): r_{uv} \text{ observed}} (w \cdot \phi(v) - r_{uv})^2 + \lambda \|w\|^2
  $$

**Personalization via User-Specific Deviations**
- Add user-specific weights $ w_u$:
  $$
  r_{uv} \approx (w + w_u) \cdot \phi(v)
  $$
- For new users, $ w_u = 0$ (use global weights); as more data accumulates, $ w_u$ adapts.

**Featurized Matrix Factorization (Unified Model)**
- Combine matrix factorization and feature-based approaches:
  $$
  r_{uv} \approx L_u \cdot R_v + (w + w_u) \cdot \phi(u, v)
  $$
- Can be optimized with coordinate descent or gradient descent.

---

## Applications

- **Localization**: Matrix completion can infer missing entries in distance matrices, exploiting low-rank structure due to spatial constraints.
- **Text Data**: Matrix factorization can uncover latent topics in document-word matrices, similar to topic modeling.

---

## Summary Table: Approaches Comparison

| Approach                | Personalization | Handles Cold-Start | Uses Features | Handles Sparsity | Scalability |
|-------------------------|----------------|--------------------|---------------|------------------|-------------|
| Popularity              | No             | Yes                | No            | Yes              | High        |
| Classifier              | Yes            | Yes                | Yes           | Limited          | Moderate    |
| Co-Occurrence           | Limited        | No                 | No            | Yes              | High        |
| Matrix Factorization    | Yes            | No                 | No            | Yes              | High        |
| Feature-Based Linear    | Yes            | Yes                | Yes           | Yes              | High        |
| Featurized Matrix Fact. | Yes            | Yes                | Yes           | Yes              | Moderate    |

---

**Best Practices**
- Use collaborative filtering (matrix factorization) for personalization when sufficient data exists.
- Use feature-based models to address cold-start and incorporate context.
- Combine both for robust, scalable, and adaptive recommender systems.


