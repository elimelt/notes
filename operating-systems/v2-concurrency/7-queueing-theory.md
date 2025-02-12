---
title: Queueing Theory
category: Systems
tags: queueing theory, systems, performance analysis
description: Covers the fundamental concepts of queueing theory, including definitions, Little's Law, and analysis of response time versus utilization under different arrival patterns (uniform, bursty, exponential). Discusses how queueing theory can be applied to model and analyze the performance of systems with queuing components, such as computer networks, call centers, and manufacturing processes.
---

# Queueing Theory

Simplifying assumptions:

- **Work preserving**: The system will eventually process all requests.
- **FIFO scheduling**: Requests are processed in the order they arrive.

## Definitions

- **Server**: Anything that performas tasks, e.g. CPU, disk, network, etc.
- **Queueing delay ($W$)**: Time a task spends waiting to be scheduled. In a time slicing system (e.g. CPU), this is the sum of all the time it takes for a request to be completed.
- **Tasks queued ($Q$)**: Number of tasks in the queue.
- **Service time ($S$)**: Time it takes to complete a task, assuming no waiting.
- **Response time ($R$)**: Time it takes for a task to be completed, including queueing and service time.
    - Note that $R = W + S$, and that in order to improve overall response time, we need to reduce either queueing time or service time.
- **Arrival rate ($\lambda$)**: Number of tasks arriving per unit time.
- **Arrival process**: The distribution of the time between task arrivals.
- **Service rate ($\mu$)**: Number of tasks completed per unit time. $\mu = 1/S$.
- **Utilization ($U$)**: Fraction of time the server is busy.
    - $0 \leq U \leq 1$.
    - $U = \lambda / \mu$ if $\lambda < \mu$.
    - $U = 1$ if $\lambda \geq \mu$.
- **Throughput ($X$)**: Number of tasks completed per unit time.
    - $X = U \cdot \mu$.
    - X = $\lambda$ if $U < 1$.
    - X = $\mu$ if $U = 1$.
- **Tasks in the system (N)**: Tasks in the system, including those being serviced and those in the queue.
    - $N = Q + U$.

## Little's Law

Defines a very general relationship for any system, and is useful for understanding the relationship between throughput, response time, and the number of tasks in the system.

$$N = X \cdot R$$

*eg. If the throughput is 10 tasks per second, and the average response time is 5 seconds, then there are 50 tasks in the system.*

### Examples


Server than processes requests sequentually. The average arrival and departure rate is 100 requests/sec. The average request completes after 5 ms. What is the average utilization $U$ of the system?

$$U = X \cdot R = 100 \cdot 0.005 = 0.5$$

*Meaning the server is busy 50% of the time.*

Web service that takes an average of 100 ms to process a request, and handles 10000 queries per second. What is the average number of requests in the system?

$$N = X \cdot R = 10000 \cdot 0.1  = 1000 \text{ queries}$$

### Response Time vs. Utilization

Operating a system with high utilization increases risk of overload. If $\lambda > \mu$, the queue will grow indefinitely, and so will the response time.

Higher arrival rate $\lambda$ and burstier arrival process will tend to yield longer queue lengths.

#### Best Case: Uniform Arrival

- $\lambda < \mu$: $R = S$. Queues will shrink until they are empty and remain that way.
- $\lambda = \mu$: $R = S$. Queues will remain in a steady state.
- $\lambda > \mu$: $R = \infty$. Queues will grow indefinitely. In practice, this would lead to requests being dropped/system failure.

#### Worst Case: Bursty Arrival

When requests arrive in groups (which they often do), the queue will grow and shrink in response to the bursts. This can lead to a higher average queue length and response time. Even if the average arrival rate is less than the service rate, the queue can still grow if the arrival process is bursty.

For example, consider the following two systems:

- System 1: $\lambda = 1$ request/second, $S = 1$ second service time, uniform arrival.
- System 2: $\lambda = 1$ request/second, $S = 1$ second service time, bursty arrival w/ 10 req every 10 seconds.

System 1 processes requests as they come in, with a queue length of 0. The average response time over a 10 second period is 1 second.

$$
R = \frac{1}{10} \sum_{i=1}^{10} 1 = 1 \text{ seconds}
$$

System 2 processes requests in bursts, with a queue length that grows and shrinks. The average response time is...

$$R = \frac{1}{10} \sum_{i=1}^{10} i = 5.5 \text{ seconds}$$

Generally, for a system with arrival rate $\lambda = \frac{n}{t}$ which is a bursty arrival process of $n$ requests every $t$ seconds, and a service time of $S$ seconds, the average response time for each request in the burst is...

$$
R = \frac{1}{n} \sum_{i=1}^{n} i \cdot S
$$

#### Exponential Arrivals

An **exponential distribution** of a continuous random variable has a mean $\lambda^{-1}$, and a variance $\lambda^{-2}$. Its probability density function is...

$$
f(x) = \lambda e^{-\lambda x}
$$

It is a *memoryless* distribution, meaning that the probability of an event occurring in the next $t$ seconds is the same as the probability of an event occurring in the next $t + s$ seconds.

A memoryless distribution is useful because it allows us to model a queue as a finite state machine with states corresponding to the number of tasks in the queue, and transition probablilities $\lambda$ and $\mu$ for transitioning up a state (arrival) and down a state (departure).

Assuming $\lambda < \mu$, the system is stable and we can calculate the response time $R$ as a function of utilization $U$ and service time $S$:

$$
R = \frac{S}{1 - U}
$$

This shows the exponential relationship between response time and utilization. As utilization increases, response time increases very slowly at first, but then increases rapidly as the system approaches overload.