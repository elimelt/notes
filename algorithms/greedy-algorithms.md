---
title: Greedy Algorithms for Interval Scheduling and Partitioning
category: Algorithm Analysis
tags: algorithms, interval, scheduling, partitioning, greedy-algorithms
description: This document explores greedy algorithms for interval scheduling and partitioning problems. It provides detailed explanations of the algorithms, including Python implementations, and presents rigorous proofs of correctness using techniques such as "Greedy Stays Ahead" and exchange arguments.
---

# Greedy Algorithms

Choose the most attractive choice at each step, and hope that this will lead to the optimal solution. Proofs of correctness are particularly important for greedy algorithms.

## Interval Scheduling

Job $j$ starts at $s(j)$ and finishes at $f(j)$. Two jobs are compatible if they don't overlap. The goal is to schedule as many jobs as possible without overlapping.

Start by sorting the jobs with $f(j)$, and iterate over the jobs in order and choose as many jobs as you can.

```python
def interval_scheduling(jobs):
  jobs.sort(key=lambda x: x[1])
  last = 0
  S = []
  for job in jobs:
    if job[0] >= last:
      S.append(job)
      last = job[1]
  return S
```

### Greedy Stays Ahead Proof

Suppose the above algorithm has chosen jobs $f(i_1) \le f(i_2) \le \ldots \le f(i_k)$, and suppose $f(j_1) \le f(j_2) \le \ldots \le f(j_m)$.

_Goal:_ $m \le k$

_Lemma_: $\forall r$, $f(i_r) \le f(j_r)$

_Proof_: Induction, $P(r) := f(i_r) \le f(j_r)$

_Base Case_: $P(1)$. $i_1$ has the smallest finishing time.

_IH_: Assume $P(r - 1)$

_IS_: Goal $P(r)$

Applying $P(r - 1)$, and using the fact that both sets of jobs chosen are non-overlapping within themselves, we have...

$$
f(i_{r - 1}) \le f(j_{r - 1}) \le s(j_r)
$$

So $j_r$ is a candidate for $i_r$. However, greedy chose $i_r$, which implies $f(i_r) \le $f(j_r)$. (induction over)

Now, we want to show that $m \le k$. Suppose for contradiction that $m > k$.

We know $f(i_k) \le f(j_k) \le s(j_{k + 1})$, so greedy could have executed $j_{k + 1}$ after $i_k$, which is a contradiction.

### Exchange Argument

Make the optimal solution similar to greedy without changing its value.

This would look like removing $j_1$ from the optimal solution, adding $i_1$ instead. Then this optimal solution still has the same number of jobs, and is thus still optimal, but also shares $i_1$ in common with the greedy solution. Continue this into the general case where the first $k$ jobs are in common, and we can use the previous lemma to show that we can continue this exchange, until the greedy solution becomes the optimal.

## Interval Partitioning

Given a set of intervals $I$, partition them into the minimum number of sets $S_1, S_2, \ldots, S_k$ such that each $S_i$ contains no overlapping intervals.

```python
def partition_intervals(I: list[tuple[int, int]]):
  # sort by start time
  I.sort(key=lambda x: x[0])
  d = 0
  S = []
  for itvl in I:
    # if some partition works, add itvl to it
    for i, S_i in enumerate(S):
      if itvl[0] >= S_i[-1][1]:
        S[i].append(itvl)
        break
    # otherwise, allocate new partition with itvl
    else:
      S[d] = [itvl]
      d += 1
  return S
```

### Proof of Correctness

**Observation**: The algorithm never schedules two incompatible lectures in the same classroom.

**Lemma**: The algorithm is optimal.

**Proof**: using structural property

Let $d$ be the number of classrooms the greedy algorithm uses. Classroom $d$ is then allocated because we needed to schedule a job, $j$, that is incompatible with all $d - 1$ previously allocated classrooms.

Since we sorted by start time, all these incompatible jobs must have started before $s(j)$, and thus we have $d$ lectures overlapping at time $s(j) + \epsilon$, so our maximum depth is $\ge d$.

Since we have that the optimal solution must schedule at least depth number of classrooms, we have that the greedy algorithm is optimal.
