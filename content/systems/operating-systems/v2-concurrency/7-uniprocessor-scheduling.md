---
title: Uniprocessor Scheduling
aliases:
  - operating-systems/v2-concurrency/7-uniprocessor-scheduling
category: Operating Systems
tags:
  - uniprocessor scheduling
  - operating systems
  - performance metrics
date: 2024-03-04
updated: 2026-07-30
status: evergreen
description: Chapter notes on the uniprocessor portion of OSPP chapter 7. FIFO, SJF, Round Robin, max-min fairness, and multi-level feedback queues, with the tradeoffs each makes between response time, throughput, and fairness, and a derivation comparing RR to SJF/FIFO response times.
sources:
  - title: "Operating Systems: Principles and Practice (2nd ed.), Anderson and Dahlin, chapter 7"
    url: https://ospp.cs.washington.edu/
    type: textbook
---

## Purpose

Notes on the uniprocessor scheduling part of chapter 7 of [Operating Systems: Principles and Practice](https://ospp.cs.washington.edu/). The question a scheduler answers is which task gets the processor next. Each policy here answers it differently, and each one trades response time, throughput, and fairness against the others. The multiprocessor case builds on these in [[systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling|multiprocessor scheduling]].

## Performance Terminology

| Key Word | Description |
| - | - |
| **Task/Job** | A unit of work that can be scheduled. |
| **Response time/delay** | The user-perceived time to do some task. |
| **Throughput** | The number of tasks completed per unit time. |
| **Predictability** | Inversely related to variance in response time for repeated tasks. |
| **Scheduling Overhead** | The time to switch between tasks. |
| **Fairness** | Equality in the number and timeliness of resource allocations. |
| **Starvation** | Lack of progress for one task due to resources being allocated to higher-priority tasks. |
| **Workload** | The set of tasks to be scheduled. |

## First in, First Out (FIFO)

Complete tasks in arrival order, finishing one before starting the next. On a uniprocessor with a fully CPU-bound workload, FIFO is hard to beat on throughput because scheduling overhead is minimal. It is bad for interactive systems, since short tasks get stuck behind long ones, and its average response time is in many cases much worse than the alternatives below.

FIFO works when requests are of roughly equal length. Memcached-style cache servers are the standard example: every request is an in-memory lookup of about the same cost, so nothing gets stuck behind a long job, and FIFO's simplicity supports very high throughput.

## Shortest Job First (SJF)

Run the task with the shortest remaining time first. For a given set of tasks this minimizes average response time, and it is also unimplementable as stated, since run times are not known in advance. Its value is as a bound to compare real policies against.

### Bias Towards Short Tasks

SJF's bias toward short tasks can starve long ones, and there is a real tradeoff between average response time and the variance of response times. In interactive systems the long tasks are often the ones users care about. The bias is also exploitable: a user can split a long task into many short tasks to jump the queue, which turns into a denial-of-service vector against other users.

### Sample Bias

When measuring SJF against other policies, watch for sample bias. If short tasks keep arriving, long tasks starve, and a measurement that only samples completed tasks never sees the starving ones. The average looks great because the victims are missing from the data.

### Bandwidth Constrained Web Services

SJF fits a web service limited by network egress bandwidth. The shortest jobs are the responses that leave fastest, and large responses are limited by the network anyway, so favoring short jobs improves how quickly the system as a whole gets bytes out the door. An overloaded server can drop the largest requests, a natural form of load shedding, at the cost of extra logic to handle what was dropped.

## Round Robin (RR)

Each task in the queue runs for a fixed **time quantum**. A task that does not finish gets preempted by a timer interrupt and moved to the back of the queue, so no task can starve indefinitely. The quantum has to be long enough to keep context switch overhead small and short enough to keep response time good.

### Overhead of RR Context Switching

Much of the context switch cost is cache damage. Each switch lets a new task evict the previous task's cache entries, so a very short quantum means every task runs cold. Lengthening the quantum does not make a single switch cheaper. It makes switches rarer, which is what recovers the cache hit rate.

RR sits between FIFO and SJF. With an infinite quantum, RR is FIFO. With a quantum of a single instruction and zero overhead, tasks complete in order of length, the same completion order SJF would give, though every task's response time stretches because everyone shares the processor along the way.

**Simultaneous Multithreading (SMT)** lets multiple threads issue instructions to a superscalar processor in the same cycle, which amounts to hardware-level round-robin without context switch overhead.

### Deriving RR's Response Time on a Worst-Case Workload

Take a workload of $n$ tasks, each needing $t$ quanta of length $q$ (so each task takes $t \cdot q$ seconds of CPU). Assume no scheduling overhead. All three policies finish all $n$ tasks at time $n \cdot t \cdot q$, so throughput is identical. Response time is where they split.

Under RR, every task limps along at the same pace and they all finish during the final round of scheduling. Each round takes $nq$ seconds and there are $t$ rounds, so the last round starts at $nq(t-1)$, and the $i$-th task in the round order finishes at $nq(t-1) + iq$:

$$
T_{\text{RR}} = \frac{1}{n} \sum_{i=1}^{n} \left( nq(t - 1) + iq \right) = nq(t-1) + q\,\frac{n + 1}{2}
$$

SJF and FIFO behave identically on this workload (all tasks are equal length and already queued): task $i$ finishes at $iqt$, so

$$
T_{\text{SJF}} = T_{\text{FIFO}} = \frac{1}{n} \sum_{i=1}^{n} iqt = qt\,\frac{n + 1}{2}
$$

The difference is $T_{\text{RR}} - T_{\text{FIFO}} = q(t-1)\frac{n-1}{2} \geq 0$, and for large $n$ and $t$ the averages approach $nqt$ versus $nqt/2$: RR roughly doubles the average response time on equal-length tasks while delivering the same throughput. Equal-length tasks are RR's worst case, since time slicing helps only when task lengths vary. If response time is the metric you care most about, round-robin is a poor choice.

### Silver Lining: Stream Processing

Round-robin is a natural fit when tasks are continuous streams rather than discrete jobs. A video server can send a small chunk to each client in round-robin order, serving all clients evenly with no client starved.

### Mixed Workloads Being Bad for RR

Workloads mixing I/O-bound and CPU-bound tasks give RR trouble. A text editor needs keystrokes echoed with low latency, and under RR it may have to wait out a full round of other tasks' quanta before its input handler runs. Or take a browser on a slow link downloading a large file in the background while the user browses: round-robin scheduling of network I/O degrades the interactive browsing to the benefit of the bulk download.

## Max-Min Fairness

Max-min fairness maximizes the minimum share of the processor across tasks: give every task as much as it can use, subject to no task getting more while a needier task gets less. This drives down the variance in response times.

If all tasks are compute-bound, max-min reduces to RR. I/O-bound tasks that use less than their full quantum get to run fully, and their unused allocation is split evenly among the remaining tasks, repeating until all CPU time is assigned.

A literal implementation would always schedule the task that has consumed the least processor time so far. That fails in practice because two equally short tasks endlessly alternate, each preempting the other. An approximation tracks CPU usage at quantum granularity and allows a task at most one quantum beyond its ideal max-min allocation. Even that needs a priority queue over tasks, which is more bookkeeping than commercial operating systems are willing to pay per scheduling decision.

## Multi-level Feedback Queue (MLFQ)

Think grocery store express lanes, with multiple priority tiers. MLFQ is the compromise policy that most general-purpose kernels build on, balancing:

| Goal | Description |
| - | - |
| **Responsiveness** | Short tasks should be completed quickly. |
| **Low Overhead** | Minimize the number of preemptions, as well as the time spent scheduling. |
| **Starvation Avoidance** | All tasks should be able to make progress. |
| **Background Tasks** | Deferrable tasks like system maintenance should not interfere with foreground tasks. |
| **Fairness** | Assign non-background tasks an approximately max-min fair share of the CPU. |

### MLFQ Algorithm

Maintain multiple RR queues, each with its own priority and time quantum. Higher priority queues get smaller quanta and preempt lower priority queues. Tasks at the same level run round-robin.

A new task enters the highest priority queue. A task that uses its entire quantum gets demoted a level; a task that yields before its quantum expires stays put or gets promoted. The effect approximates SJF: short interactive tasks stay at high priority while long CPU-bound tasks sink.

To avoid starvation and approximate max-min fairness, the scheduler also monitors per-process CPU time and schedules the processes that have yet to receive their fair share, demoting processes that already got theirs and promoting processes that fell behind.

## Related notes

- [[systems/operating-systems/v2-concurrency/7-queueing-theory|queueing theory]]
- [[systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling|multiprocessor scheduling]]
- [[systems/operating-systems/v2-concurrency/4-concurrency-and-threads|concurrency and threads]]
