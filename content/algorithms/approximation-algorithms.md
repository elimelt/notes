---
title: Approximation Algorithms
category: Algorithms
tags:
  - approximation
  - algorithms
  - vertex cover
  - set cover
date: 2024-05-10
updated: 2026-07-30
status: evergreen
description: Defines the approximation ratio and derives the bounds for two standard examples, the 2-approximation for vertex cover and the greedy ln(n) approximation for set cover.
---

## Purpose

When a problem is NP-complete, you give up on computing an exact optimum in polynomial time. This note defines the approximation ratio and derives the guarantees for two standard approximation algorithms: the 2-approximation for vertex cover and the greedy $\ln(n)$ approximation for set cover.

Problems where this comes up include set cover, graph coloring, traveling salesman, maximum independent set, vertex cover, and boolean satisfiability. When your problem reduces to one of these, you have two practical options. Solve the problem exactly on specially structured inputs, or compute a solution with a provable bound on how far it can be from optimal, even in the worst case.

## Approximation Ratio

$$
\alpha = \frac{\text{computed solution}}{\text{optimum solution}}
$$

An upper or lower bound on $\alpha$ turns a heuristic into an algorithm you can reason about. For a minimization problem, an $\alpha$-approximation guarantees $OPT \le ALG \le \alpha \cdot OPT$.

## 2-Approximation for Vertex Cover

**Problem**: find a minimal subset $S$ of vertices in a graph such that every edge has at least one endpoint in $S$.

**Algorithm**: while some edge $(u, v)$ has neither endpoint in $S$, add both $u$ and $v$ to $S$.

The edges the algorithm picks share no endpoints, so they form a matching $M$. Any vertex cover must contain at least one endpoint of every edge in $M$, and those endpoints are distinct across edges of $M$, so $OPT \ge |M|$. The algorithm outputs $|S| = 2|M|$ vertices, which gives

$$
OPT(G) \le ALG(G) \le 2 \cdot OPT(G)
$$

so $\alpha = 2$.

## ln(n) Approximation for Set Cover

**Problem**: given sets $S_1, S_2, \ldots, S_m$ with $S_i \subseteq U$ and $|U| = n$, choose the minimum number of sets that cover all elements of $U$.

**Algorithm**: while elements remain uncovered, choose the set that covers the most new elements.

Suppose the optimal solution uses $k$ sets. Those $k$ sets cover every remaining element at any point during the run, so some set always covers at least $\frac{1}{k}$ of the remaining elements. The greedy choice covers at least that many. After $t$ steps the number of uncovered elements is at most

$$
n\left(1 - \frac{1}{k}\right)^t \le n \cdot e^{-t/k}
$$

Setting $t = k \ln(n)$ drives this below $1$, so greedy selects at most $k \ln(n)$ sets.

## Related notes

- [[algorithms/greedy-algorithms|greedy algorithms]]
- [[algorithms/linear-programming|linear programming]]
- [[reference/cheatsheets/algorithms/intervals|interval scheduling and partitioning]]
