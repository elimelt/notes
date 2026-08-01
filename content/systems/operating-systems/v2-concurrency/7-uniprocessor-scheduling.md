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
updated: 2026-08-01
status: evergreen
description: Single-CPU scheduling policies and what each optimizes. FIFO, SJF and SRPT optimality, Round Robin and processor sharing, max-min fairness, lottery and stride scheduling, starvation and aging, and MLFQ, with a side-by-side trace comparing policies on one workload.
sources:
  - title: "Operating Systems: Principles and Practice (2nd ed.), Anderson and Dahlin, chapter 7"
    url: https://ospp.cs.washington.edu/
    type: textbook
  - title: Schrage (1968), A Proof of the Optimality of the Shortest Remaining Processing Time Discipline
    url: https://dl.acm.org/doi/10.1145/321738.321743
    type: paper
  - title: Joseph Hellerstein, CS262 scheduling lecture notes
    url: https://people.eecs.berkeley.edu/~adj/cs262/Lec_10_22.pdf
    type: lecture
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

### SRPT and Why It Is Optimal

The preemptive version, **shortest remaining processing time** (SRPT), preempts the running task whenever a new arrival has less remaining work. [Schrage (1968)](https://dl.acm.org/doi/10.1145/321738.321743) proved SRPT optimal: among *all* scheduling disciplines, preemptive or not, with or without knowledge of the future, SRPT minimizes the number of jobs in the system at every instant — and by Little's Law, minimizing time-average jobs-in-system is the same as minimizing mean response time. The exchange-argument intuition: if the schedule ever runs a job with more remaining work while one with less waits, swapping the next unit of service finishes the short one sooner without delaying the long one's completion, reducing the jobs-in-system count during the swapped interval. Repeating the swap until no such pair exists yields SRPT.

The proof's assumptions are the interesting part: one processor, jobs' remaining times known, no switching cost. Every real scheduler violates the middle assumption and must approximate remaining time from observed behavior — which is exactly what MLFQ below does, using "has this task used up its quanta" as a cheap predictor of "does it have a lot of work left."

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

### Processor Sharing: the Fluid Ideal Behind RR

As the quantum shrinks toward zero (with zero overhead), RR converges to **processor sharing** (PS): all $n$ runnable tasks progress simultaneously at rate $1/n$ each. PS is to RR what bit-by-bit round robin is to packet scheduling in [[systems/scheduling/3-network-and-packet/fair-queueing-wfq-and-drr|fair queueing]] — the continuous ideal that the discrete policy approximates one quantum at a time. PS has a clean analytical property: in the M/M/1-PS queue, a job of size $x$ has expected response time $x/(1-\rho)$, *proportional to its own size* and independent of the shapes of other jobs. Every job is slowed by the same factor $1/(1-\rho)$ — perfectly proportional pain, no starvation, no need to know job sizes. That insensitivity is why PS is the standard fairness benchmark: SRPT beats it on mean response time by favoring the short, but PS guarantees no job's slowdown depends on being lucky about the competition. Real RR sits between the ideal and FIFO, degraded by quantum granularity (a task waits up to $(n-1)q$ per round) and switch overhead.

### Silver Lining: Stream Processing

Round-robin is a natural fit when tasks are continuous streams rather than discrete jobs. A video server can send a small chunk to each client in round-robin order, serving all clients evenly with no client starved.

### Mixed Workloads Being Bad for RR

Workloads mixing I/O-bound and CPU-bound tasks give RR trouble. A text editor needs keystrokes echoed with low latency, and under RR it may have to wait out a full round of other tasks' quanta before its input handler runs. Or take a browser on a slow link downloading a large file in the background while the user browses: round-robin scheduling of network I/O degrades the interactive browsing to the benefit of the bulk download.

## Max-Min Fairness

Max-min fairness maximizes the minimum share of the processor across tasks: give every task as much as it can use, subject to no task getting more while a needier task gets less. This drives down the variance in response times.

If all tasks are compute-bound, max-min reduces to RR. I/O-bound tasks that use less than their full quantum get to run fully, and their unused allocation is split evenly among the remaining tasks, repeating until all CPU time is assigned.

A literal implementation would always schedule the task that has consumed the least processor time so far. That fails in practice because two equally short tasks endlessly alternate, each preempting the other. An approximation tracks CPU usage at quantum granularity and allows a task at most one quantum beyond its ideal max-min allocation. Even that needs a priority queue over tasks, which is more bookkeeping than commercial operating systems are willing to pay per scheduling decision.

## Weighted Fairness: Lottery and Stride

Equal shares are rarely the actual goal — an interactive session should outweigh a batch reindex. Give task $i$ a weight $w_i$ and target allocation $w_i / \sum_j w_j$. Two classic mechanisms from Waldspurger and Weihl implement weighted shares without measuring job lengths:

- **Lottery scheduling**: each task holds $w_i$ tickets; each quantum, draw a ticket uniformly and run the holder. Expected share is exactly proportional to tickets, starvation is impossible (every ticket has positive probability), and the mechanism composes — a task can subdivide its tickets among its own children, giving hierarchical shares for free. The cost is variance: over a window of $k$ quanta a task's actual allocation fluctuates like a binomial, $\sigma \propto \sqrt{k}$, so short-window fairness is poor.
- **Stride scheduling** is the deterministic version: task $i$ has stride $\propto 1/w_i$ and a pass counter; always run the task with the smallest pass, then advance its pass by its stride. Heavier weight, smaller stride, more frequent turns. Allocation error is bounded by a constant (one quantum) over any window, versus lottery's $\sqrt{k}$ drift.

Stride scheduling is the direct ancestor of Linux CFS's virtual runtime: `vruntime` advances at a rate inversely proportional to weight, and the scheduler always runs the minimum — the same pass/stride idea with different bookkeeping (details in [[systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling|multiprocessor scheduling]]). All of these are the CPU-side siblings of WFQ's virtual finish times in [[systems/scheduling/3-network-and-packet/fair-queueing-wfq-and-drr|fair queueing]].

## Starvation and Aging

Any policy that ranks tasks by a static attribute can starve the bottom rank: SJF starves long jobs while short ones keep arriving, and strict priority starves low priorities under sustained high-priority load. Two structural observations organize the fixes:

- Starvation requires *sustained* competition. Under light load every policy is benign; the failure mode appears exactly when $\rho \to 1$ and the favored class alone can keep the processor busy.
- The fix is always some form of **aging**: fold waiting time into effective priority so that neglect is self-correcting. A common form raises priority linearly with wait ($p_{\text{eff}} = p_{\text{base}} + \alpha \cdot t_{\text{wait}}$), which bounds worst-case wait by $(p_{\max} - p_{\text{base}})/\alpha$ plus the queue drain time above — a tunable starvation bound, traded directly against how sharply the scheduler favors its preferred class in the short term.

MLFQ's periodic priority boost, lottery's guaranteed ticket probability, stride's bounded pass drift, and CFS's min-vruntime pick are all aging in different costumes. The diagnostic question for any proposed policy is: what unbounded counter, if any, can a task accumulate while never being scheduled? If one exists, the policy starves.

## One Workload, Four Policies

Acceptance test for all of the above: three tasks on one CPU — A arrives at $t=0$ needing 8 units, B at $t=1$ needing 4, C at $t=2$ needing 1. RR quantum = 1. Response time = finish − arrival. (Trace generated by a small simulator in the repo venv; the simulator is the ~40 lines of Python below.)

| Policy | A finishes | B finishes | C finishes | Mean response time |
| --- | --- | --- | --- | --- |
| FIFO | 8 | 12 | 13 | 10.00 |
| SJF (non-preemptive) | 8 | 13 | 9 | 9.00 |
| SRPT | 13 | 6 | 3 | **6.33** |
| RR ($q=1$) | 13 | 9 | 4 | 7.67 |

The trace compresses the whole chapter. FIFO makes C (1 unit of work) wait 11 units behind A. Non-preemptive SJF cannot help B and C until A's 8-unit run ends — the damage is done at $t=0$. SRPT preempts A the moment B arrives and achieves the provably minimal mean, at the price of pushing A, the longest job, to last place; its response time goes from 8 to 13, the fairness cost of the optimal mean. RR lands between SRPT and FIFO on the mean, close to SRPT for the short jobs (C at 4 vs. 3) without needing to know any job lengths — which is the practical argument for time slicing: most of SRPT's benefit for short jobs, none of its clairvoyance.

```python
def rr(tasks, q=1):                       # tasks: (name, arrival, burst)
    from collections import deque
    rem = {n: b for n, a, b in tasks}
    arr = {n: a for n, a, b in tasks}
    t, run, done, added = 0.0, deque(), {}, set()
    while len(done) < len(tasks):
        for n, a, b in tasks:
            if a <= t and n not in added:
                run.append(n); added.add(n)
        if not run:
            t = min(a for n, a, b in tasks if n not in added); continue
        n = run.popleft()
        step = min(q, rem[n]); t += step; rem[n] -= step
        for m, a, b in tasks:              # arrivals during the slice
            if a <= t and m not in added:
                run.append(m); added.add(m)
        if rem[n] <= 1e-9: done[n] = t
        else: run.append(n)
    return {n: done[n] - arr[n] for n in done}

print(rr([("A", 0, 8), ("B", 1, 4), ("C", 2, 1)]))
```

Output: `{'C': 2.0, 'B': 8.0, 'A': 13.0}` — matching the RR row (response times, not finish times). Swapping the policy function reproduces the other rows.

### What Each Policy Optimizes

| Policy | Optimizes / approximates | At the cost of |
| --- | --- | --- |
| FIFO | switching overhead, simplicity; fine when jobs are uniform | mean response time under variable job sizes |
| SJF / SRPT | mean response time (SRPT provably optimal, Schrage 1968) | long-job response time and variance; needs size estimates |
| RR / PS | proportional slowdown, no starvation, no job-size knowledge | ~2x mean response time on equal-length jobs |
| Lottery / stride | weighted proportional shares | lottery: short-window variance; stride: bookkeeping |
| MLFQ | SRPT-like means without clairvoyance + responsiveness | gameable heuristics, needs aging against starvation |

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

- [[systems/scheduling/1-single-resource/fifo-sjf-srpt-rr-and-mlfq|FIFO, SJF, SRPT, RR, and MLFQ]]
- [[systems/scheduling/1-single-resource/real-time-scheduling-edf-and-rate-monotonic|real-time scheduling]]
- [[systems/operating-systems/v2-concurrency/7-queueing-theory|queueing theory]]
- [[systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling|multiprocessor scheduling]]
- [[systems/operating-systems/v2-concurrency/4-concurrency-and-threads|concurrency and threads]]
