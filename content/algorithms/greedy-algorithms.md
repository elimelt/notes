---
title: Greedy Algorithms for Interval Scheduling and Partitioning
category: Algorithms
tags:
  - algorithms
  - interval
  - scheduling
  - partitioning
  - greedy
date: 2024-04-19
updated: 2026-07-30
status: evergreen
description: Greedy algorithms for interval scheduling and interval partitioning, with correctness proofs by greedy-stays-ahead, exchange argument, and a structural depth bound.
sources:
  - https://www.cs.princeton.edu/~wayne/kleinberg-tardos/
---

## Purpose

A greedy algorithm makes the most attractive choice at each step and hopes this leads to an optimal solution. Most greedy strategies are wrong, so the proof of correctness carries the weight. This note works through interval scheduling and interval partitioning, which between them show the three standard proof techniques: greedy stays ahead, exchange arguments, and structural bounds.

> [!abstract] The three proof techniques
> **Greedy stays ahead**: define a progress measure, then show by induction that after every step greedy is at least as far along as any optimal solution. Used for interval scheduling via the lemma $f(i_r) \le f(j_r)$.
> **Exchange argument**: transform an optimal solution into the greedy one through swaps that never hurt its value, so greedy's value equals the optimum. Used as the alternate interval scheduling proof.
> **Structural bound**: exhibit a quantity that lower-bounds every solution, then show greedy meets it exactly. Used for interval partitioning, where the bound is the depth of the input.

## Interval Scheduling

Job $j$ starts at $s(j)$ and finishes at $f(j)$. Two jobs are compatible if they don't overlap. The goal is to schedule as many jobs as possible without overlap. This is one of the classic [[reference/cheatsheets/algorithms/intervals|interval scheduling]] problems.

Sort the jobs by $f(j)$, iterate in order, and take every job that is compatible with the last one taken.

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

Suppose greedy chose jobs with finish times $f(i_1) \le f(i_2) \le \ldots \le f(i_k)$, and some optimal solution chose $f(j_1) \le f(j_2) \le \ldots \le f(j_m)$.

*Goal*: $m \le k$.

*Lemma*: $\forall r$, $f(i_r) \le f(j_r)$.

*Proof*: induction on $r$ with $P(r) := f(i_r) \le f(j_r)$.

*Base case* $P(1)$: greedy picks $i_1$ with the smallest finish time overall.

*Inductive hypothesis*: assume $P(r - 1)$.

*Inductive step*: applying $P(r - 1)$, and using the fact that both solutions are internally non-overlapping,

$$
f(i_{r - 1}) \le f(j_{r - 1}) \le s(j_r)
$$

So $j_r$ was a candidate when greedy picked $i_r$. Greedy picks the candidate with the earliest finish time, which implies $f(i_r) \le f(j_r)$. $\blacksquare$

Now suppose for contradiction that $m > k$. The lemma gives $f(i_k) \le f(j_k) \le s(j_{k + 1})$, so $j_{k + 1}$ is compatible with $i_k$ and greedy would have taken another job after $i_k$. That contradicts greedy stopping at $k$ jobs, so $m \le k$.

### Exchange Argument

Transform the optimal solution into the greedy solution without changing its value. Remove $j_1$ from the optimal solution and add $i_1$ instead; $f(i_1) \le f(j_1)$ means $i_1$ is compatible with the rest, so the modified solution has the same number of jobs, is still optimal, and now agrees with greedy on its first choice. Repeat: if the first $r$ jobs agree, the lemma above lets us swap $j_{r+1}$ for $i_{r+1}$. Continuing until the solutions agree everywhere shows the greedy solution has optimal size.

## Interval Partitioning

Given a set of intervals $I$, partition them into the minimum number of sets $S_1, S_2, \ldots, S_k$ such that each $S_i$ contains no overlapping intervals. The usual framing is scheduling lectures into the minimum number of classrooms. This is the second classic [[reference/cheatsheets/algorithms/intervals|interval partitioning]] problem.

Sort by start time and place each interval into any existing classroom that fits, opening a new classroom only when none fits.

```python
def partition_intervals(I: list[tuple[int, int]]):
  # sort by start time
  I.sort(key=lambda x: x[0])
  S = []
  for itvl in I:
    # if some existing partition works, add itvl to it
    for S_i in S:
      if itvl[0] >= S_i[-1][1]:
        S_i.append(itvl)
        break
    # otherwise, allocate a new partition holding itvl
    else:
      S.append([itvl])
  return S
```

### Why the sort order matters

Sorting by finish time works for [[algorithms/greedy-algorithms#Interval Scheduling|interval scheduling]], but it is the wrong rule for interval partitioning. A small counterexample is

$$
[(0, 1), (0, 3), (4, 5), (2, 5)].
$$

If these intervals are processed in finish-time order, the algorithm opens three classrooms:

- $(0, 1)$ goes in $C_0$
- $(0, 3)$ is incompatible with $C_0$, so it opens $C_1$
- $(4, 5)$ fits in both $C_0$ and $C_1$, say $C_0$
- $(2, 5)$ now conflicts with the last interval in both rooms, so it opens $C_2$

That is not optimal. The input has depth $2$, since no point is covered by more than two intervals, so two classrooms suffice. The fix is to sort by **start** time. Then, when a new classroom is opened, every existing classroom already contains an interval that overlaps the new one, which is exactly the fact the correctness proof needs.

> [!warning] A plausible choice rule is not a correct one
> Earliest finish time is optimal for interval scheduling and suboptimal for interval partitioning, even though the problems look nearly identical. The failure shows up in the proof before it shows up in testing: with finish-time order, nothing guarantees that the intervals blocking a new classroom all overlap at one point, so the depth argument falls apart. If the choice rule does not hand the proof a usable invariant, treat the greedy algorithm as unproven.

### Proof of Correctness

Define the **depth** of the input as the maximum number of intervals that overlap at any single point in time. Any valid partition needs at least depth many classrooms, since the intervals overlapping at one point must all sit in different classrooms.

**Observation**: the algorithm never schedules two incompatible lectures in the same classroom, since it only places an interval where it fits.

**Lemma**: the algorithm uses exactly depth many classrooms, and is therefore optimal.

**Proof**: let $d$ be the number of classrooms the algorithm uses. Classroom $d$ was allocated because some job $j$ was incompatible with all $d - 1$ previously allocated classrooms. Since we sorted by start time, each of those incompatible jobs started before $s(j)$ and ends after $s(j)$, so $d$ lectures overlap at time $s(j) + \epsilon$. The depth is therefore at least $d$, and since every solution uses at least depth classrooms, greedy is optimal. $\blacksquare$

## Related notes

- [[algorithms/practice/4|problem set 4]]
- [[algorithms/dynamic-programming|dynamic programming]]
- [[algorithms/approximation-algorithms|approximation algorithms]]
- [[algorithms/stable-matching|stable matching]]
