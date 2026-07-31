---
title: Measuring Algorithm Efficiency with Asymptotic Notation
category: Algorithms
tags:
  - time complexity
  - asymptotic notation
  - efficiency
date: 2024-03-29
updated: 2026-07-30
status: evergreen
description: Definitions of O, Omega, and Theta notation, growth-rate facts for common function families, and why polynomial time is the standard bar for an efficient algorithm.
sources:
  - https://www.cs.princeton.edu/~wayne/kleinberg-tardos/
---

## Purpose

Running time is roughly proportional to the number of simple operations performed, so counting operations as a function of input size is how we compare algorithms without benchmarking them. This note pins down the three asymptotic notations and the growth-rate facts worth memorizing.

## O-Notation

Given two functions $f(n)$ and $g(n)$, we say that $f(n)$ is $O(g(n))$ if there exist constants $c$ and $n_0$ such that $0 \leq f(n) \leq c \cdot g(n)$ for all $n \geq n_0$.

## Omega-Notation

Given two functions $f(n)$ and $g(n)$, we say that $f(n)$ is $\Omega(g(n))$ if there exist constants $c$ and $n_0$ such that $0 \leq c \cdot g(n) \leq f(n)$ for all $n \geq n_0$.

## Theta-Notation

Given two functions $f(n)$ and $g(n)$, we say that $f(n)$ is $\Theta(g(n))$ if there exist constants $c_1$, $c_2$, and $n_0$ such that $0 \leq c_1 \cdot g(n) \leq f(n) \leq c_2 \cdot g(n)$ for all $n \geq n_0$.

## Common Bounds

Logarithms grow slower than every polynomial $n^\epsilon$ with $\epsilon > 0$, and every polynomial grows slower than every exponential $b^n$ with $b > 1$.

### Polynomial

$$
a_0 + a_1n + a_2n^2 + \ldots + a_kn^k \in O(n^k)
$$

### Logarithmic

$$
\log_a n \in O(\log_b n) \text{ for all } a, b > 1
$$

Base changes only shift a logarithm by a constant factor, since $\log_a n = \frac{\log_b n}{\log_b a}$.

### Exponential

$$
a^n \in O(b^n) \text{ for all } 1 < a \le b
$$

### Factorial

$$
n! \in O(n^n)
$$

## "Efficient" Algorithms

A single CPU core executes on the order of $10^9$ simple operations per second. That budget makes exponential algorithms useless beyond tiny inputs: $2^{60}$ operations is decades of compute, and $n!$ blows past that at $n = 20$.

Polynomial time is the standard bar for an efficient algorithm, and it has a useful scaling property: if the input size grows by a constant factor, the running time of a polynomial time algorithm also grows by a constant factor.

## Related notes

- [[algorithms/divide-and-conquer|divide and conquer]]
- [[algorithms/dynamic-programming|dynamic programming]]
