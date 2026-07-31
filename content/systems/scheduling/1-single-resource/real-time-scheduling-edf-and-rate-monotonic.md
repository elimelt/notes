---
title: Real-Time Scheduling with EDF and Rate Monotonic
category: Scheduling
tags:
  - scheduling
  - real-time scheduling
  - edf
  - rate monotonic
  - deadlines
  - schedulability
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Deadline-driven single-resource scheduling, with the classic EDF and rate-monotonic results, schedulability tests, and small worked examples.
sources:
  - title: "Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment"
    url: https://dl.acm.org/doi/10.1145/321738.321743
    type: paper
---

## Purpose

Most scheduling notes optimize averages. Real-time scheduling changes the question:

- does every job finish before its deadline?

That is a feasibility question before it is a performance question.

## Task Model

For periodic task $\tau_i$:

- computation time $C_i$
- period $T_i$
- relative deadline $D_i$

The simplest classical setting uses implicit deadlines:

$$
D_i = T_i
$$

Utilization is

$$
U = \sum_i \frac{C_i}{T_i}
$$

## Earliest Deadline First

EDF is dynamic priority scheduling:

- among runnable jobs, run the one whose absolute deadline is soonest

In the implicit-deadline uniprocessor model, EDF is optimal. If any policy can schedule the task set feasibly, EDF can.

A necessary feasibility condition is

$$
U \le 1
$$

and for implicit deadlines on one processor this is also sufficient for EDF.

That is a remarkably clean result.

## Rate Monotonic

Rate monotonic (RM) is fixed priority:

- shorter period means higher priority

It is easier to implement than EDF because priorities are static. The classic utilization bound is

$$
U \le n(2^{1/n} - 1)
$$

for $n$ tasks.

As $n \to \infty$, this approaches

$$
\ln 2 \approx 0.693
$$

So RM has a safe utilization bound around 69.3% in the worst case, even though many concrete task sets above that are still schedulable.

## Small Example

Take two periodic tasks:

- $\tau_1: C_1 = 1, T_1 = 4$
- $\tau_2: C_2 = 2, T_2 = 5$

Then

$$
U = \frac{1}{4} + \frac{2}{5} = 0.65
$$

EDF says feasible because $U < 1$.

RM bound for $n=2$ is

$$
2(\sqrt{2}-1) \approx 0.828
$$

So RM's sufficient bound also passes. Both are safe here.

## Why EDF Wins Theoretically and RM Persists Practically

EDF uses dynamic priorities and fully exploits available utilization in the classical model. RM gives up capacity in exchange for simpler implementation and analyzability under many embedded-system assumptions.

The real system tradeoff is often:

- EDF: more flexible, tighter capacity use
- RM: simpler fixed-priority machinery, easier certification story

## Tiny Schedulability Helper

```python
import math

def rm_bound(n: int) -> float:
    return n * (2 ** (1 / n) - 1)

def utilization(tasks):
    return sum(c / t for c, t in tasks)

tasks = [(1, 4), (2, 5)]
u = utilization(tasks)
print("U =", u)
print("EDF feasible?", u <= 1.0)
print("RM sufficient test?", u <= rm_bound(len(tasks)))
```

## Caveats

The clean theorems above assume a lot:

- one processor
- independent tasks
- no shared-resource blocking
- known worst-case execution times
- periodic or sporadic release models

Once locks, I/O, multicore interference, or cache effects show up, schedulability analysis gets much messier.

## Related Notes

- [[systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling|Multiprocessor Scheduling]]
- [[systems/scheduling/1-single-resource/fifo-sjf-srpt-rr-and-mlfq|FIFO, SJF, SRPT, RR, and MLFQ]]
- [[systems/scheduling/0-foundations/queueing-models-and-tail-latency|Queueing Models and Tail Latency]]

