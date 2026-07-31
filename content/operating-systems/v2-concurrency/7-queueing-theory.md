---
title: Queueing Theory
category: Systems
tags:
  - queueing theory
  - systems
  - performance analysis
date: 2024-03-07
updated: 2026-07-30
status: evergreen
description: Chapter notes on the queueing theory section of OSPP chapter 7. Definitions and notation, Little's Law with worked examples, and how response time behaves under uniform, bursty, and exponential arrival processes.
sources:
  - title: "Operating Systems: Principles and Practice (2nd ed.), Anderson and Dahlin, chapter 7"
    url: https://ospp.cs.washington.edu/
    type: textbook
---

## Purpose

Notes on the queueing theory section of chapter 7 of [Operating Systems: Principles and Practice](https://ospp.cs.washington.edu/). Queueing theory gives back-of-the-envelope answers to questions like "what happens to response time if utilization doubles" without simulating anything. The same math applies to CPUs, disks, networks, and anything else that serves requests from a queue.

Simplifying assumptions used throughout:

- **Work preserving**: the system will eventually process all requests.
- **FIFO scheduling**: requests are processed in the order they arrive.

## Definitions

- **Server**: anything that performs tasks, e.g. CPU, disk, network link.
- **Queueing delay ($W$)**: total time a task spends waiting to be scheduled. In a time-slicing system the task may wait many separate times, and $W$ is the sum of those waits.
- **Tasks queued ($Q$)**: number of tasks in the queue.
- **Service time ($S$)**: time to complete a task, assuming no waiting.
- **Response time ($R$)**: time for a task to complete, including queueing and service time.
    - $R = W + S$. Improving overall response time means reducing either the queueing time or the service time.
- **Arrival rate ($\lambda$)**: number of tasks arriving per unit time.
- **Arrival process**: the distribution of the time between task arrivals.
- **Service rate ($\mu$)**: number of tasks completed per unit time when busy. $\mu = 1/S$.
- **Utilization ($U$)**: fraction of time the server is busy.
    - $0 \leq U \leq 1$.
    - $U = \lambda / \mu$ if $\lambda < \mu$.
    - $U = 1$ if $\lambda \geq \mu$.
- **Throughput ($X$)**: number of tasks completed per unit time.
    - $X = U \cdot \mu$.
    - $X = \lambda$ if $U < 1$.
    - $X = \mu$ if $U = 1$.
- **Tasks in the system ($N$)**: tasks in the system, both in service and queued.
    - $N = Q + U$ on average, since utilization equals the average number of tasks in service at a single server.

## Little's Law

For any stable system, regardless of arrival distribution or scheduling policy:

$$N = X \cdot R$$

The average number of tasks in the system equals throughput times average response time. If throughput is 10 tasks per second and average response time is 5 seconds, there are on average 50 tasks in the system.

The law applies to any bounded subsystem, and that flexibility is what makes it useful. Applied to just the server (excluding the queue), the "tasks inside" is the average number in service, which is $U$, and the "time inside" is $S$, giving $U = X \cdot S$.

### Examples

A server processes requests sequentially. Requests arrive (and depart) at an average of 100 requests/sec, and the average request takes 5 ms of service. Applying Little's Law to the server alone:

$$U = X \cdot S = 100 \cdot 0.005 = 0.5$$

The server is busy 50% of the time.

A web service takes an average of 100 ms to complete a request and handles 10,000 queries per second. Applying Little's Law to the whole system:

$$N = X \cdot R = 10000 \cdot 0.1 = 1000 \text{ queries in the system}$$

## Response Time vs. Utilization

Operating a system at high utilization raises the risk of overload. If $\lambda > \mu$, the queue grows without bound and response time grows with it. Higher arrival rate $\lambda$ and burstier arrival processes both push queue lengths up.

### Best Case: Uniform Arrival

With perfectly evenly spaced arrivals:

- $\lambda < \mu$: $R = S$. Queues shrink until empty and stay empty.
- $\lambda = \mu$: $R = S$. Queues hold steady.
- $\lambda > \mu$: $R \to \infty$. Queues grow indefinitely. In practice requests get dropped or the system fails.

### Worst Case: Bursty Arrival

Requests often arrive in groups. The queue grows during a burst and drains between bursts, and average response time suffers even when the average arrival rate is well under the service rate. Compare:

- System 1: $\lambda = 1$ request/second, $S = 1$ second, uniform arrivals.
- System 2: $\lambda = 1$ request/second, $S = 1$ second, bursty arrivals of 10 requests every 10 seconds.

System 1 serves each request as it arrives. The queue stays empty and every request sees $R = 1$ second:

$$
R = \frac{1}{10} \sum_{i=1}^{10} 1 = 1 \text{ second}
$$

System 2 serves each burst sequentially. The $i$-th request in the burst waits for the $i - 1$ requests ahead of it, finishing at time $i$:

$$R = \frac{1}{10} \sum_{i=1}^{10} i = 5.5 \text{ seconds}$$

Same average arrival rate, 5.5x the average response time. In general, for bursts of $n$ requests with service time $S$ each, the $i$-th request in a burst finishes at $i \cdot S$, so

$$
R = \frac{1}{n} \sum_{i=1}^{n} i \cdot S = \frac{(n+1) S}{2}
$$

### Exponential Arrivals

An **exponential distribution** with rate $\lambda$ has mean $\lambda^{-1}$, variance $\lambda^{-2}$, and probability density

$$
f(x) = \lambda e^{-\lambda x}
$$

It is *memoryless*: given that you have already waited $s$ seconds, the probability of waiting at least $t$ more is the same as it was from the start, $P(X > s + t \mid X > s) = P(X > t)$.

Memorylessness is what makes the math tractable. With exponential interarrival and service times, the queue becomes a state machine whose states are the number of tasks in the system, with transition rate $\lambda$ up (an arrival) and $\mu$ down (a departure), and no other history matters.

Assuming $\lambda < \mu$, the system is stable, and solving that state machine gives response time as a function of utilization and service time:

$$
R = \frac{S}{1 - U}
$$

The shape of this curve is the practical takeaway. At low utilization, response time barely rises above $S$. As $U$ approaches 1, the denominator goes to zero and response time blows up. At $U = 0.5$ you pay 2x the service time, at $U = 0.9$ you pay 10x. This is why operators leave headroom instead of running servers near full utilization.

## Related notes

- [[operating-systems/v2-concurrency/7-uniprocessor-scheduling|uniprocessor scheduling]]
- [[operating-systems/v2-concurrency/7-multiprocessor-scheduling|multiprocessor scheduling]]
