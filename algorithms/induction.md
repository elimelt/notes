---
title: Mathematical Induction and Pigeonhole Principle Proofs
category: Mathematics
tags:
  - Induction
  - Pigeonhole Principle
  - Proof Techniques
  - Number Theory
  - Combinatorics
description: This document presents detailed proofs using mathematical induction and the pigeonhole principle. It demonstrates the inductive proof for the sum of natural numbers and provides a step-by-step proof of the pigeonhole principle, emphasizing the general approach to inductive reasoning in mathematics.
---


# Induction

Prove...

$$
\forall n \in \mathbb{N}, \sum^{n}_{i = 1} i = \frac{n(n + 1)}{2}
$$

$$
P(n) = \sum^{n}_{i = 1} i = \frac{n(n + 1)}{2}
$$

### Base Case

$$
P(1) = 1 = \frac{1(1 + 2)}{2}
$$

### IH

Assume $P(n)$ for some $n \ge 2$

### IS

$$
1 + \ldots + n - 1 + n = \frac{(n - 1)(n)}{2} + n = \frac{n(n + 1)}{2}
$$

# Pigeon Hole Principle

Suppose that we put $n + 1$ balls into $n$ bins. Prove that there is a bin with at least $2$ balls.

$P(n) :=$ _For any possible way to put $n + 1$ balls into $n$ bins, there exists a bin with $\ge 2$ balls._

## Base Case

duh...

## IH

Assume $P(n - 1)$ holds for some $n \ge 2$

## IS

Suppose we are given $n + 1$ balls _arbitrarily_ placed into $n$ bins, labeled $b_1, \ldots, b_{n}$.

Consider $b_1$. If $b_1$ has 2 balls in it, we are done. If it has 1 ball, then throw away $b_1$ and call $P(n - 1)$ for $b_2, \ldots, b_{n}, so we are done.

Finally, if $b_1$ has no balls, throw away an arbitrary ball and call $P(n - 1)$ on $b_2, \ldots, b_n$

### Generally

With this type of induction, start with $P(n)$, and reduce to $P(n - 1)$.
