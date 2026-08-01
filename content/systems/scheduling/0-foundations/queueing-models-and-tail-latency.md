---
title: Queueing Models and Tail Latency
category: Scheduling
tags:
  - scheduling
  - queueing
  - tail latency
  - m-m-1
  - little's law
  - service variability
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: The standard queueing models behind scheduling intuition, including M/M/1, service-time variability, and why percentiles get ugly long before average throughput looks broken.
sources:
  - title: "Queueing Theory"
    url: https://www.kea.nu/files/textbooks/ospp/
    type: textbook
  - title: "The Tail at Scale"
    url: https://research.google/pubs/the-tail-at-scale/
    type: paper
---

## Purpose

This note is the math behind "utilization near one is dangerous." The key ideas are:

- M/M/1 gives the cleanest closed form
- deterministic service is friendlier than variable service
- tails compound under fan-out

## M/M/1 in One Page

Assume:

- Poisson arrivals with rate $\lambda$
- exponential service with rate $\mu$
- one server
- FIFO

Define utilization

$$
\rho = \frac{\lambda}{\mu} = \lambda S
$$

with $S = 1/\mu$.

The stationary probability of $n$ jobs in the system is geometric:

$$
P(N = n) = (1-\rho)\rho^n, \qquad n \ge 0
$$

so

$$
E[N] = \frac{\rho}{1-\rho}
$$

Little's Law then gives

$$
E[R] = \frac{E[N]}{\lambda} = \frac{1}{\mu-\lambda} = \frac{S}{1-\rho}
$$

This is the core scheduling curve. The denominator is the whole story.

## Why the Curve Hurts

Take $S = 1$ ms.

- at $\rho = 0.5$, $E[R] = 2$ ms
- at $\rho = 0.8$, $E[R] = 5$ ms
- at $\rho = 0.9$, $E[R] = 10$ ms
- at $\rho = 0.99$, $E[R] = 100$ ms

The service time did not change. The queue did.

> [!warning] Utilization prices latency nonlinearly
> With $S = 1$ ms, moving from 50% to 90% busy quintuples response time, and 90% to 99% multiplies it by ten again — the work never changed, only the queue. Average-utilization dashboards hide this: the same 0.9 average reached smoothly or in bursts produces very different tails.

## Deterministic Service Is Kinder

M/M/1 is analytically convenient and operationally pessimistic because exponential service is highly variable. If service time is constant instead, the queue is M/D/1, and the mean waiting time is lower.

The broader lesson comes from the Pollaczek-Khinchine result for M/G/1:

$$
E[W_q] = \frac{\lambda E[S^2]}{2(1-\rho)}
$$

Since $E[S^2]$ appears, variability matters directly. Two servers with the same mean service time can have very different queueing delay if one has a long heavy tail.

That is why systems that mix tiny requests with rare giant ones often need classification, separate pools, or admission control instead of a single queue.

## Burstiness

Arrival variability hurts for the same reason. Average utilization can look fine while bursts create local overload. A queue that drains comfortably on average can still accumulate large backlogs during spikes, and those spikes show up first in high percentiles.

This is where "run at 60% average utilization" comes from. The missing 40% is not waste. It is burst budget.

## Tail Percentiles Under Fan-Out

Suppose one user request waits on $k$ parallel subrequests, and the overall completion time is the max:

$$
T_{\max} = \max(T_1, \dots, T_k)
$$

If each subrequest finishes by time $t$ with probability $F(t)$, then

$$
P(T_{\max} \le t) = F(t)^k
$$

So the service-level target for each shard must be stricter than the end-to-end target. If one backend has p99 = 100 ms and a request fans out to 100 independent backends, the probability all are below 100 ms is about

$$
0.99^{100} \approx 0.366
$$

So 100 ms is nowhere near the end-to-end p99 anymore.

This is the central tail-at-scale effect.

## Tiny Simulation

```python
import random
from collections import deque

def simulate_mm1(arrival_rate, service_rate, steps, dt=1e-4):
    q = deque()
    t = 0.0
    busy_until = 0.0
    responses = []

    for _ in range(steps):
        t += dt

        if random.random() < arrival_rate * dt:
            q.append(t)

        if t >= busy_until and q:
            arrival_t = q.popleft()
            service_t = random.expovariate(service_rate)
            busy_until = t + service_t
            responses.append(busy_until - arrival_t)

    return responses
```

This is crude, but enough to make the blow-up visible as $\rho$ approaches 1.

## How Scheduling Changes the Distribution

Queueing formulas are always conditional on a policy and service model. Changing the scheduling policy can reduce mean or tail latency by:

- prioritizing short jobs
- separating heterogeneous job classes
- preempting long work
- rejecting work before queues run away
- duplicating or speculating on stragglers

The queueing model explains why those moves help. The scheduling policy chooses which one to pay for.

## Related Notes

- [[systems/scheduling/0-foundations/littles-law-and-bottleneck-analysis|Little's Law and Bottleneck Analysis]]
- [[systems/distributed-systems/load-balancing|Load Balancing]]
- [[systems/operating-systems/v2-concurrency/7-queueing-theory|Queueing Theory]]

