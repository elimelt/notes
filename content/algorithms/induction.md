---
title: Mathematical Induction and Pigeonhole Principle Proofs
category: Algorithms
tags:
  - induction
  - pigeonhole principle
  - proof techniques
date: 2024-03-29
updated: 2026-07-30
status: evergreen
description: Two worked induction proofs, the closed form for the sum of the first n natural numbers and the pigeonhole principle, as templates for the base case, hypothesis, step structure.
---

## Purpose

Induction is the main proof technique behind recursive algorithms, so it pays to have the mechanics down cold. This note works two small proofs in full: the closed form for $\sum_{i=1}^{n} i$, and the pigeonhole principle. Both follow the same skeleton of base case, inductive hypothesis, and inductive step.

> [!abstract] Proof skeleton
>
> 1. Define the predicate $P(n)$ so the claim is exactly $\forall n \ge n_0,\ P(n)$.
> 2. **Base case**: prove $P(n_0)$ directly.
> 3. **Inductive hypothesis**: assume $P(n - 1)$ for an arbitrary $n > n_0$.
> 4. **Inductive step**: derive $P(n)$ from the hypothesis.

## Sum of the First n Naturals

**Claim**:

$$
\forall n \in \mathbb{N}, \sum^{n}_{i = 1} i = \frac{n(n + 1)}{2}
$$

Let $P(n)$ denote the statement $\sum^{n}_{i = 1} i = \frac{n(n + 1)}{2}$.

**Base case** $P(1)$:

$$
1 = \frac{1(1 + 1)}{2}
$$

**Inductive hypothesis**: assume $P(n - 1)$ for some $n \ge 2$.

**Inductive step**: applying $P(n - 1)$ to the first $n - 1$ terms,

$$
1 + \ldots + (n - 1) + n = \frac{(n - 1)n}{2} + n = \frac{n(n + 1)}{2}
$$

so $P(n)$ holds. $\blacksquare$

## Pigeonhole Principle

**Claim**: put $n + 1$ balls into $n$ bins, and some bin holds at least 2 balls.

$P(n) :=$ *for any way to put $n + 1$ balls into $n$ bins, there exists a bin with $\ge 2$ balls.*

**Base case** $P(1)$: both balls land in the single bin, which then holds 2 balls.

**Inductive hypothesis**: assume $P(n - 1)$ holds for some $n \ge 2$.

**Inductive step**: suppose $n + 1$ balls are placed arbitrarily into bins $b_1, \ldots, b_n$. Consider $b_1$.

- If $b_1$ holds 2 or more balls, we are done.
- If $b_1$ holds exactly 1 ball, discard $b_1$ and its ball. That leaves $n$ balls in the $n - 1$ bins $b_2, \ldots, b_n$, so $P(n - 1)$ gives a bin with $\ge 2$ balls.
- If $b_1$ is empty, discard $b_1$ and one arbitrary ball. Again $n$ balls sit in $n - 1$ bins, and $P(n - 1)$ applies. $\blacksquare$

> [!warning] The build-up error
> The inductive step must start from an arbitrary instance of size $n$ and shrink it. The pigeonhole proof takes any placement of $n + 1$ balls and discards a bin. Arguing in the other direction, by extending a size $n - 1$ instance, only covers the instances you can reach that way, and the proof silently skips the rest.

## The General Pattern

Both proofs reduce $P(n)$ to $P(n - 1)$ by peeling one element off the instance. When designing recursive algorithms the same move appears as solving a problem of size $n$ using a solution of size $n - 1$. [[algorithms/divide-and-conquer|Divide and conquer]] changes only the reduction: instead of shrinking by one, you shrink to a constant fraction of the input.

## Related notes

- [[algorithms/problems/graphs-and-trees|graphs and trees problems]]
- [[reference/cheatsheets/algorithms/divide-and-conquer|divide and conquer cheatsheet]]
- [[algorithms/divide-and-conquer|divide and conquer]]
- [[algorithms/tree-intro|trees]]
- [[algorithms/dynamic-programming|dynamic programming]]
