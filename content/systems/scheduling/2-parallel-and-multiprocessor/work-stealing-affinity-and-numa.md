---
title: Work Stealing, Affinity, and NUMA
category: Scheduling
tags:
  - scheduling
  - work stealing
  - affinity scheduling
  - numa
  - locality
  - multiprocessor scheduling
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Scheduling dynamic parallel work on many processors, including work stealing, processor affinity, and why locality and migration cost belong in the objective.
sources:
  - title: "Scheduling Multithreaded Computations by Work Stealing"
    url: https://dl.acm.org/doi/10.1145/324133.324234
    type: paper
  - title: "The Implementation of the Cilk-5 Multithreaded Language"
    url: https://dl.acm.org/doi/10.1145/277650.277725
    type: paper
  - title: "Linux NUMA Memory Policy"
    url: https://www.kernel.org/doc/html/latest/admin-guide/mm/numa_memory_policy.html
    type: docs
---

## Purpose

Single-queue scheduling stops being adequate on multicore machines because a good placement policy has to reason about both load and locality. This note covers three pieces that fit together:

- work stealing for irregular task graphs
- processor affinity for cache reuse
- NUMA awareness for memory locality

## Work and Span

For a parallel computation DAG:

- $T_1$: total work, the time on one processor
- $T_\infty$: span, the critical-path time with infinite processors

No scheduler can beat

$$
T_P \ge \max\left(\frac{T_1}{P}, T_\infty\right)
$$

Work stealing matters because it gets close to that lower bound for well-structured computations without centralized scheduling.

## The Deque Discipline

Each worker owns a double-ended queue:

- owner pushes and pops from the bottom
- thieves steal from the top

That asymmetry is the trick.

- Bottom operations are cheap and local in the common case.
- Old work near the top tends to expose more parallel slack, so stealing there is useful.

```python
class Worker:
    def __init__(self):
        self.deque = []

    def spawn(self, task):
        self.deque.append(task)        # push bottom

    def run_local(self):
        return self.deque.pop() if self.deque else None

    def steal_from(self, victim):
        return victim.deque.pop(0) if victim.deque else None
```

Real runtimes avoid `pop(0)` because it is linear in Python lists, but the policy is the point.

## Why Work Stealing Works

The Blumofe-Leiserson result is the headline:

$$
E[T_P] = O\left(\frac{T_1}{P} + T_\infty\right)
$$

for fully strict computations under randomized stealing.

The intuition is clean:

- busy workers keep chewing through local work
- idle workers steal only when parallelism exists elsewhere
- steals are charged mostly to the critical path rather than to all work

That is why task-parallel runtimes often prefer work stealing to one global queue.

## Affinity

Even for sequential request processing, where work stealing is not the main idea, affinity matters. If a thread runs again on the same core:

- its private caches are more likely to help
- branch predictor state is warmer
- TLB entries are likelier to still matter

The scheduler objective is no longer just "which core is idle?" It becomes:

- is the work runnable?
- where is its state warm?
- what is the cost of moving it?

This is why per-core run queues are common.

## NUMA

On a NUMA machine, memory has topology. Local DRAM and remote DRAM do not cost the same. So thread placement and page placement become coupled problems.

The wrong move is to "balance" CPU load by moving a thread away from the memory it mostly touches. CPU utilization can improve while response time gets worse.

The actual cost model includes:

- migration cost of moving the runnable thread
- cache-warmup loss after migration
- remote-memory penalty if the thread stays but data moves badly

That is why real multiprocessor scheduling often accepts some load imbalance to preserve locality.

## When Work Stealing and Affinity Fight

Work stealing wants idle processors to grab tasks aggressively. Affinity wants tasks to stay near their data. These objectives line up when:

- steal only when local work is exhausted
- steal coarse enough tasks that the extra locality loss is amortized

They fight when tasks are tiny or data-heavy. Then a "balanced" schedule can become a locality disaster.

## Related Notes

- [[systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling|Multiprocessor Scheduling]]
- [[systems/operating-systems/benchmarks/bandwidth|Memory Bandwidth]]
- [[systems/operating-systems/benchmarks/false_sharing|False Sharing]]
- [[systems/operating-systems/benchmarks/mlp|Memory-Level Parallelism]]

