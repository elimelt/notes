---
title: Interval Scheduling/Partitioning
category: algorithms
tags: greedy algorithms, interval partitioning, scheduling, time complexity
description: A technical exploration of Interval Scheduling and Partitioning focusing on their greedy algorithm properties and structural analysis.
---

# Interval Scheduling/Partitioning

## Scheduling the max number of intervals

- **Algorithm:** sort by finish time and select the next compatible interval
- **Proof**: Greedy stays ahead, by induction
  - *Claim*: Greedy algorithm is optimal
  - **Lemma**
    - $P(r)$: For greedy choices $g_1, \ldots, g_n$ and optimal choices $k_1, \ldots, k_m$, $f(g_r) \le f(k_r)$
    - $P(1)$: $g_1$ is chosen to have the minimum finish time, so $f(g_1) \le f(k_1)$
    - Suppose $P(r)$. Since $f(g_r) \le f(k_r) \le s(k_{r + 1})$, $k_{r + 1}$ is among the candidates considered for $g_{r + 1}$. Of those candidates, it picks the minimum finish time, so $f(g_{r + 1}) \le f(k_{r + 1})$.
  - By this lemma, we must have $n \ge m$, since since otherwise $k_{n + 1}$ is in the set of candidates for $g_{n + 1}$.

## Partitioning intervals into the minimum number of sets

- **Algorithm**: sort intervals by start time, adding them to **any** compatible set. If no set is compatible, create a new one
- **Proof**: exploit structural property
  - *Claim*: greedy algorithm is optimal
  - Let $d$ be the number of sets the greedy algorithm allocates. The $d$th set, $S_d$ is allocated because we had to assign some interval, $I_i$, that was not compatible with any of the $d - 1$ previous sets.
  - Since we sorted by start time, all intervals $I_j \in S_1 \cup \ldots \cup S_{d - 1}$ have $s(I_i) \ge s(I_j)$. Thus, we have at least depth $d$ intervals, and so all valid partitions must have $\ge d$ sets.
