---
title: Divide and Conquer Algorithms
category: Algorithms
tags: divide and conquer, master theorem, root finding, bisector algorithm, kth smallest element
description: A technical exploration of Divide and Conquer algorithms focusing on the Master Theorem, Root Finding, and kth Smallest Element problems.
---

# Divide and Conquer

## Master Theorem

Given any recurrence of the form $T(n) = a T(\frac{n}{b}) + c n^k$ for all $n > b$, we have:

- If $a > b^k$, then $T(n) = \Theta(n^{\log_b a})$
- If $a < b^k$, then $T(n) = \Theta(n^k)$
- If $a = b^k$, then $T(n) = \Theta(n^k \log n)$

## Root Finding

Given a continuous function $f$ and two points $a < b$ such that $f(a) \cdot f(b) < 0$, there exists a root of $f$ in the interval $\lbrack  a, b  \rbrack$ by the **intermediate value theorem**. Since said root may be irrational, we aim to approximate it with an arbitrary precision $\epsilon$.

- **Algorithm**: $Bisect(a, b, \epsilon)$
  - If $b - a < \epsilon$, $a$ is a suitable approximation
  - Otherwise, calculate the midpoint $m = (a + b)/2$
  - If $f(m) \le 0$ then return $Bisect(m, b, \epsilon)$
  - else return $Bisect(a, m, \epsilon)$
- **Time**: $T(n) = T(\frac{n}{2}) + O(1) = O(\log(\frac{b - a}{\epsilon}))$
- **Proof**:
  - $P(k) =$ For any $a, b$ such that $k\epsilon \le |a - b| \le (k + 1)\epsilon$, if $f(a)f(b) \le 0$, then we find an $\epsilon$ approx to a root using $\log k$ queries to $f$.
  - $P(1)$: Output $a + \epsilon$, since the whole interval is at most $epsilon$. This requires $0$ calls to $f$.
  - Suppose $P(k)$ and consider an arbitrary $a$, $b$ s.t. $2k\epsilon \le |a - b| \le (2k + 1)\epsilon$.
  - If $f(a + k\epsilon) = 0$, output $a + k\epsilon$.
  - If $f(a)f(a + k\epsilon) < 0$, solve on the interval $\lbrack  a, a + k\epsilon  \rbrack$. By I.H. this takes at most $\log(k)$ queries of $f$.
  - Otherwise, we have $f(b)f(a + k\epsilon) < 0$, since $f(a)f(b) < 0$ and $f(a)f(a + k\epsilon) \ge 0$. Solve the interval $\lbrack  a + k\epsilon, b  \rbrack$.
  - In any case, we used at most $\log(k) + 1 = $\log(2k)$ queries to $f$.


## kth Smallest Element

- **Algorithm**: $f(S \in \mathbb{R}^n, k \in \mathbb{R})$
  - Select an approximate median element $w$ using median of $\frac{n}{5} medians with subarrays of size $5$
  - Partition each element into three sets, $S_{>}, S_{<}, S_{=}$
  - If $k \le |S_{<}|$, recurse on $f(S_{<}, k)$
  - Else, if $k \le |S_{<}| + |S_{=}|$, return $w$
  - Else, recurse on $f(S_{>}, k - |S_{<}| - |S_{=}|)$