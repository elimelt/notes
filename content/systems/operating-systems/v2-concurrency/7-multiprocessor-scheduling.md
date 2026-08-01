---
title: Multiprocessor Scheduling
aliases:
  - operating-systems/v2-concurrency/7-multiprocessor-scheduling
category: Operating Systems
tags:
  - multiprocessor scheduling
  - operating systems
  - cache coherence
  - affinity scheduling
date: 2024-03-04
updated: 2026-08-01
status: evergreen
description: The main CPU-parallel scheduling reference. Per-processor queues and affinity, work stealing mechanics, NUMA and migration cost accounting, Linux CFS and EEVDF as real-system reference points, failure modes of oblivious scheduling, gang scheduling and scheduler activations, and real-time basics.
sources:
  - title: "Operating Systems: Principles and Practice (2nd ed.), Anderson and Dahlin, chapter 7"
    url: https://ospp.cs.washington.edu/
    type: textbook
  - title: Blumofe and Leiserson (1999), Scheduling Multithreaded Computations by Work Stealing
    url: https://dl.acm.org/doi/10.1145/324133.324234
    type: paper
  - title: Linux kernel docs, CFS Scheduler Design
    url: https://www.kernel.org/doc/html/latest/scheduler/sched-design-CFS.html
    type: docs
---

## Purpose

Notes on the multiprocessor scheduling part of chapter 7 of [Operating Systems: Principles and Practice](https://ospp.cs.washington.edu/). The uniprocessor policies in [[systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling|uniprocessor scheduling]] assume one processor pulling from one queue. This note covers what breaks when there are many processors, and what schedulers do about it.

Modern systems have multiple processors, each with multiple cores, often with hyperthreading on top. A scheduler has to exploit that parallelism without drowning in coordination costs.

## Scheduling Sequential Applications on Multiprocessors

Consider a server processing a large number of requests. The simple design is one shared multi-level feedback queue (MLFQ, covered in the uniprocessor note) protected by a lock, with every processor pulling work from it. When a request blocks on I/O, it re-enters the queue and another request runs. Three things go wrong:

- **Contention for the MLFQ lock**: more processors means more contention, and processors end up waiting on the lock instead of running work.
- **Cache coherence overhead**: each scheduling decision writes the shared queue, invalidating the copies cached by other processors. Every processor then fetches queue state from memory or a remote cache, which takes orders of magnitude longer than a local cache hit, and this happens while the lock is held, lengthening the critical section.
- **Limited cache reuse**: a thread gets picked up by whatever processor is free, so it usually lands on a processor whose cache holds someone else's data.

For these reasons, common practice is a separate MLFQ per processor. Each processor uses **affinity scheduling**: once a thread is scheduled on a processor, it keeps getting scheduled there, so its cache state stays useful. Load gets rebalanced by occasionally migrating threads between per-processor queues.

## Migration Cost and NUMA

Per-processor queues force the question affinity answers implicitly: what does moving a thread actually cost? Three components, in increasing severity:

- **Cache refill.** A migrated thread restarts with cold L1/L2 (and, cross-socket, cold L3). A working set of a few MB refills at the rate the memory hierarchy allows; with misses costing on the order of 100 ns, refilling even 1 MB of dirty working set is tens of microseconds of degraded execution, not a one-time fixed fee. The [[systems/operating-systems/benchmarks/mlp|MLP benchmark]] measures exactly how much of this latency can be hidden by overlapping misses.
- **Coherence traffic.** Data the thread wrote on the old core must be invalidated or transferred as it touches it from the new one; the [[systems/operating-systems/benchmarks/false_sharing|false sharing benchmark]] shows the per-line cost of exactly this ping-pong.
- **Remote memory on NUMA.** Cross-socket migration changes the *distance to the thread's own pages*: its memory stays on the old node, and every miss now crosses the interconnect. Remote DRAM access costs roughly 1.5-2x local latency on typical two-socket machines, and remote bandwidth is similarly reduced — measured local-versus-remote curves are in the [[systems/operating-systems/benchmarks/bandwidth|bandwidth benchmark]]. Unlike the cache costs, this one does not decay with time: it persists until the pages migrate too (Linux's NUMA balancing moves pages toward their accessors, slowly and heuristically).

The resulting rule of thumb: migration within a core's SMT siblings is nearly free, within an L3 domain cheap, across L3 domains noticeable, across sockets expensive and *persistently* so. That hierarchy is precisely how Linux structures load balancing (below): rebalance eagerly at small distances, reluctantly at large ones.

**When affinity hurts.** Affinity is a bet that cached state is worth more than a better load distribution, and the bet loses in two common cases: (1) load imbalance — a pinned thread waits on a busy core while another core idles, and the waiting exceeds the refill cost it avoided; (2) stale footprint — a thread whose phase changed (finished one file, started another) carries no reusable state, so affinity preserves nothing. Work stealing handles both automatically, because idle-core stealing overrides affinity exactly when imbalance exists, and steals are rare when load is balanced.

## Work Stealing

For parallel programs that generate tasks dynamically (fork-join, divide-and-conquer), the standard scheduler inside a process is **work stealing**. Mechanism first:

- Each worker thread owns a **deque** of ready tasks.
- The owner treats its deque as a stack: it **pushes and pops at the bottom** (LIFO). Newly spawned subtasks are executed next, depth-first — the order a sequential run would use, and the order that keeps the cache hot, since a just-spawned task's inputs were just written.
- An idle worker becomes a **thief**: it picks a victim **uniformly at random** and **steals from the top** of the victim's deque (FIFO) — the *oldest* task, which in divide-and-conquer is the largest unexplored subtree, so one steal buys the thief a long stretch of independent work.
- Owner and thief operate on opposite ends, so synchronization is nearly free in the common case; the standard lock-free implementation (the Chase-Lev deque) needs a compare-and-swap only when they collide on a nearly-empty deque.

The theory says this greedy, uncoordinated scheme is near-optimal. Model the program as a DAG with total work $T_1$ (time on one processor) and span $T_\infty$ (critical path). Any scheduler obeys the work law $T_P \ge T_1/P$ and span law $T_P \ge T_\infty$. [Blumofe and Leiserson](https://dl.acm.org/doi/10.1145/324133.324234) proved randomized work stealing achieves

$$
\mathbb{E}[T_P] \le \frac{T_1}{P} + O(T_\infty),
$$

with space at most $P \cdot S_1$. When parallelism $T_1/T_\infty \gg P$, the first term dominates: near-linear speedup with steals rare enough not to matter. Random victim selection needs no coordination and provably balances load; steal cost stays off the critical path because thieves are, by definition, workers with nothing better to do. This is the runtime under Cilk, Intel TBB, Java's ForkJoinPool, Rust's rayon, and Go's goroutine scheduler. Its limits mirror its assumptions: it optimizes throughput of one job's DAG, not priorities or deadlines across jobs; very fine tasks make steal overhead visible; and stealing ignores NUMA placement — a stolen task runs far from its data, which is the affinity bet made in the opposite direction. The scheduling-section treatment with a task-DAG trace is in [[systems/scheduling/2-parallel-and-multiprocessor/work-stealing-affinity-and-numa|work stealing, affinity, and NUMA]].

## A Real System: Linux CFS and EEVDF

Linux's CFS (Completely Fair Scheduler, 2007-2023) is the weighted-fairness thread scheduler of the [[systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling|uniprocessor note]] deployed per-core. Each task accumulates **virtual runtime** — actual runtime scaled by the inverse of its weight, where each `nice` level changes weight by ~1.25x — and the [scheduler](https://www.kernel.org/doc/html/latest/scheduler/sched-design-CFS.html) always runs the task with minimum `vruntime`, kept at the leftmost node of a red-black tree for $O(\log n)$ maintenance. This is stride scheduling with kernel bookkeeping: falling behind means a smaller vruntime, which is an automatic aging mechanism, and weighted shares emerge without measuring job lengths.

The multiprocessor layer is where this note's concerns appear. Each CPU runs its own CFS instance, and **scheduling domains** mirror the hardware hierarchy: SMT siblings, cores sharing L3, sockets. The load balancer runs far more frequently (and moves tasks more willingly) at inner domains than outer ones — the migration-cost hierarchy above, encoded as policy. **Wake affinity** places a woken task on its previous CPU if idle, or near its waker (whose cache holds the data just produced for it), which is the producer-consumer pattern handled at wake time.

In kernel 6.6 (2023), CFS's pick policy was replaced by **EEVDF** (earliest eligible virtual deadline first): among tasks that are *eligible* (not ahead of their fair share), run the one with the earliest virtual deadline, computed from its slice length over its weight. Same fairness accounting, plus a latency dimension — a task with a short slice gets an earlier deadline and preempts sooner, which lets interactive tasks be prompt without extra weight. The eligibility test is the starvation guard. The change is a useful design lesson: pure proportional fairness has no vocabulary for "small and urgent"; deadlines add it without abandoning the fair-share substrate.

## Scheduling Parallel Applications on Multiprocessors

A parallel program usually has some logical mapping between work and processors, but the mapping cannot be fixed at compile time. The number of runnable threads and available processors changes at runtime, and work rarely divides evenly.

**Oblivious scheduling** is when the scheduler operates without knowledge of the program's intent, scheduling each thread independently. It is simple and efficient for the scheduler, and it fails in recognizable ways:

- **Bulk synchronous delay**: in staged parallel computation (MapReduce is the canonical shape), every stage waits for the slowest thread, so one preempted thread stalls the whole stage.
- **Producer-consumer delay**: in a chain of producer and consumer threads (a shell pipeline), the slowest link sets the pace of the chain.
- **Critical path delay**: in a DAG of parallel work (fork-join programs), preempting a thread on the critical path delays the entire program.
- **Preemption of lock holder**: preempting a thread that holds a lock stretches the critical section across its time off the processor, delaying every waiter.
- **I/O**: a thread that blocks in the kernel on a read or write gives up its processor. Keeping the processor busy requires more threads than processors, which feeds all the problems above.

### Gang Scheduling

The application decomposes its work into a set of threads, and those threads run together or not at all. This suits specialized servers that need fine-grained control over their threads, a DBMS for example. Windows, Linux, and MacOS all provide mechanisms for it.

Time-slicing two gang-scheduled programs across all processors is usually worse than giving each program half the processors outright. Dedicating processors to tasks is called **space sharing**, and it minimizes context switches and cache invalidations. Space sharing is straightforward when tasks start and stop together; with processors coming and going dynamically, it takes more machinery, which is what scheduler activations provide.

### Scheduler Activations

The application gets an *execution context*, a **scheduler activation**, on each processor assigned to it. The kernel informs the application via upcalls whenever its processor allocation changes, and a thread blocking on I/O also triggers an upcall so the application can put that processor to other use. Scheduler activations define only the mechanism for telling an application about its processors. The scheduling policy stays with the application. The mechanism is covered in more depth in [[systems/operating-systems/v2-concurrency/4-concurrency-and-threads|concurrency and threads]].

## Real Time Scheduling

When responsiveness matters more than throughput, for instance in control systems or user interfaces, the goal becomes finishing tasks by a **deadline**. Some tools:

- **Over-provisioning**: schedule only a fraction of the system's capacity, leaving headroom so deadlines survive bursts. Like not signing up for too many classes.
- **Earliest Deadline First (EDF)**: run the task with the earliest deadline next. For CPU-bound tasks this is optimal for minimizing missed deadlines. Mixed workloads complicate it, since it can pay to start a later-deadline task's I/O early and then run the earlier-deadline task while the I/O is in flight.
- **Priority donation**: *priority inversion* happens when a high priority task waits on a lock held by a low priority task that never gets scheduled. With priority donation, the waiting high priority task donates its priority to the lock holder, which then gets scheduled, finishes the critical section, releases the lock, and drops back to its original priority.

## Related notes

- [[systems/scheduling/2-parallel-and-multiprocessor/work-stealing-affinity-and-numa|work stealing, affinity, and NUMA]]
- [[systems/scheduling/1-single-resource/real-time-scheduling-edf-and-rate-monotonic|real-time scheduling]]
- [[systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling|uniprocessor scheduling]]
- [[systems/operating-systems/v2-concurrency/7-queueing-theory|queueing theory]]
- [[systems/operating-systems/v2-concurrency/4-concurrency-and-threads|concurrency and threads]]
