---
title: Approximation Algorithms
category: algorithms
tags: approximation, algorithms, vertex cover, set cover
description: A survey of approximation algorithms, including the 2-approximation for vertex cover and the log(n) approximation for set cover.
---

# Approximation Algorithms

When faced with a problem that can be reduced to some NP-Complete problem, you (most probably) cannot generally solve it in polynomial time. For example:

- Set Cover
- Graph Coloring
- Traveling Salesman/Eulerian Tour
- Maximal independent Set
- Vertex Cover
- Boolean Satisfiability

Instead of finding an optimal solution in polynomial time, we have two approaches:

- Find the optimal solution to some specially structured input
- Find as close to optimal solution as possible, with upper/lower bounds even on the worst case

## Approximation Ratio

$$
\alpha = \frac{\text{computed solution}}{\text{optimum solution}}
$$

If we can prove some upper or lower bound on $\alpha$, then we might be able to use and reason about a given approximation algorithm. Finding better approximations is an open problem.

## A Survey of Approximation Algorithms

The following two examples are the best known general approximation algorithms for their respective problems.

### 2-Approximation for Vertex Cover

**Problem**: find the minimal subset $S$ of vertices in a graph such that every edge is connected to some vertex in $S$.
**Algorithm**: For every edge $(u, v)$, add $u$ and $v$ to $S$

By a 2-approximation, it means that $\alpha = 2$. Since we are minimizing the set, we have that that for any graph $G$, it must be the case that $OPT(G) \le ALG(G) \le 2 \cdot OPT(G)$

### log(n) approximation for Set Cover

**Problem**: Given some number of sets $S_1, S_2, \ldots, S_n$ with $S_i \subseteq U$, choose the minimum number of sets that cover all elements of $U$
**Algorithm**: While there are remaining elements, choose the set that maximizes the number of new elements covered.

If the optimal solution has $k$ sets, this algorithm always selects at most $k log(n)$ sets. This is because there is at least a set that covers $\frac{1}{k}$ of the remaining elements, so after $t$ steps we have $ \le n(1 - \frac{1}{k})^t \le n \cdot e^{-\frac{t}{k}}$ remaining elements. Therefore, after $t = k\ln(n)$ steps, we have $< 1$ uncovered element remaining.