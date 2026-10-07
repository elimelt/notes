---
title: Why Earliest Finish Time Is Optimal for Interval Scheduling
category: Algorithms
tags:
  - algorithms
  - interval
  - scheduling
  - partitioning
  - greedy
date: 2024-04-19
updated: 2026-10-06
status: evergreen
description: A greedy-stays-ahead proof that earliest finish time is optimal for interval scheduling, plus why interval partitioning uses earliest start time instead.
authors:
  - elimelt
  - gpt-5.6-sol
sources:
  - title: Kleinberg and Tardos, Algorithm Design course materials
    url: https://www.cs.princeton.edu/~wayne/kleinberg-tardos/
    type: course-materials
---

## Purpose

A greedy algorithm makes the most attractive choice at each step. The choice needs a proof. For **interval scheduling**, choosing the compatible interval with the earliest finish time is optimal because it leaves at least as much room for every later choice as any optimal solution. For **interval partitioning**, the goal changes from selecting intervals to assigning all of them, and the correct processing order is earliest start time.

Assume every interval is half-open, $[s(j), f(j))$, so one job may start exactly when another finishes.

| Problem | Goal | Greedy order | Proof idea |
| --- | --- | --- | --- |
| Interval scheduling | Select the largest compatible subset | Earliest finish time | Greedy stays ahead: its $r$th selected job finishes no later than the $r$th job in an optimum |
| Interval partitioning | Use the fewest classrooms for all intervals | Earliest start time | A newly opened room witnesses that many intervals overlapping at the new interval's start |

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
    last = float("-inf")
    selected = []
    for job in jobs:
        if job[0] >= last:
            selected.append(job)
            last = job[1]
    return selected
```

<a id="greedy-stays-ahead-proof"></a>

### Why earliest finish time is optimal: greedy stays ahead

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
    I.sort(key=lambda x: x[0])
    partitions = []
    for interval in I:
        for partition in partitions:
            if interval[0] >= partition[-1][1]:
                partition.append(interval)
                break
        else:
            partitions.append([interval])
    return partitions
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

**Proof**: let $d$ be the number of classrooms the algorithm uses. Classroom $d$ was allocated because some job $j$ was incompatible with all $d - 1$ previously allocated classrooms. Since we sorted by start time, the last job in each of those classrooms starts no later than $s(j)$ and finishes after $s(j)$. Under the half-open interval convention, those $d - 1$ jobs and $j$ all contain time $s(j)$. The input depth is therefore at least $d$. Every valid solution needs at least one classroom per interval at that time, while greedy uses $d$, so greedy is optimal. $\blacksquare$

## Sources

- [Kleinberg and Tardos, Algorithm Design course materials](https://www.cs.princeton.edu/~wayne/kleinberg-tardos/)

## Related notes

- [[algorithms/practice/4|problem set 4]]
- [[algorithms/dynamic-programming|dynamic programming]]
- [[algorithms/approximation-algorithms|approximation algorithms]]
- [[algorithms/stable-matching|stable matching]]
