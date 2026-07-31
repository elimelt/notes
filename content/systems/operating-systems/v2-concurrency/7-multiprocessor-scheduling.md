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
updated: 2026-07-30
status: evergreen
description: Chapter notes on the multiprocessor portion of OSPP chapter 7. Per-processor scheduling queues and affinity scheduling, the failure modes of oblivious scheduling for parallel programs, gang scheduling and scheduler activations, and a short treatment of real-time scheduling.
sources:
  - title: "Operating Systems: Principles and Practice (2nd ed.), Anderson and Dahlin, chapter 7"
    url: https://ospp.cs.washington.edu/
    type: textbook
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

- [[systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling|uniprocessor scheduling]]
- [[systems/operating-systems/v2-concurrency/7-queueing-theory|queueing theory]]
- [[systems/operating-systems/v2-concurrency/4-concurrency-and-threads|concurrency and threads]]
