---
title: Latency, Throughput, and Utilization
category: Performance Engineering
tags:
  - performance engineering
  - latency
  - throughput
  - utilization
  - queueing
date: 2026-07-31
updated: 2026-08-01
status: evergreen
description: A compact model for reasoning about service time, arrival rate, queueing, and the bottlenecks they create, with Little's Law, the bottleneck law, saturation behavior, and percentile-aware caveats.
sources:
  - title: Millsap (2010), Thinking Clearly about Performance
    url: https://queue.acm.org/detail.cfm?id=1854041
    type: paper
  - title: Brewer, CS262 queueing theory notes
    url: https://people.eecs.berkeley.edu/~brewer/cs262/queueing.pdf
    type: lecture
---

## Purpose

This note records the small set of quantities I keep reaching for when a system feels slow. It is the entry point for the performance section: the laws here are assumption-light and reusable, the heavier queueing math lives in [[systems/operating-systems/v2-concurrency/7-queueing-theory|Queueing Theory]], and the tail-focused view lives in [[systems/performance/tail-latency-percentiles|Tail Latency and Percentiles]].

## The four numbers

Take one service stage.

- arrival rate: $\lambda$ requests per second
- service time: $S$ seconds of work per request
- throughput: $X$ completed requests per second
- response time: $R$ seconds from arrival to completion

If the stage is stable, then $X \approx \lambda$. If requests arrive faster than the stage can serve them, a queue grows until something upstream throttles, times out, or drops work.

## Utilization

Utilization is the fraction of time the stage is busy. For a single server,

$\rho = \lambda S$

and the stage can stay stable only when $\rho < 1$.

This is the reason high average utilization is dangerous. As $\rho$ approaches 1, even small bursts stop fitting into the slack between requests, so queueing delay starts dominating service time.

## Response time

Response time splits into

$R = W_q + S$

where $W_q$ is time spent waiting in the queue and $S$ is time spent being served.

This decomposition is usually enough to narrow the problem. If $S$ is large, speed up the work. If $W_q$ is large, reduce load, smooth bursts, add capacity, or shorten the critical section that serializes requests.

## Little's Law

The one law that needs almost no assumptions: for any stable system observed over a long window,

$$
N = X \cdot R
$$

— average number of requests in the system equals throughput times average time each spends inside. The intuitive proof is an accounting identity: over a long interval $T$, each of the $XT$ completed requests contributes its residence time to the total request-seconds observed, and dividing total request-seconds by $T$ is exactly the time-average occupancy $N$. No distributional or scheduling assumptions enter, which is why the law can be applied to any boundary you can draw: a whole service, one queue, a thread pool, a connection pool.

Its everyday use is solving for the third quantity from the two you can measure. A service doing $X = 2{,}000$ req/s with $N = 300$ requests in flight has $R = N/X = 150$ ms whether or not anyone instrumented latency. Run the other way, it sizes concurrency: sustaining 2,000 req/s at 150 ms requires 300 concurrent requests' worth of capacity — threads, connections, whatever the unit of in-flight work is — and a pool capped at 100 will cap throughput at $100/0.15 \approx 667$ req/s no matter how fast the backend is.

## Bottlenecks

A bottleneck is the stage with the highest demand relative to its capacity. If stage $i$ needs $S_i$ seconds of a resource per request, then its maximum throughput is roughly

$X_i^{max} \approx 1 / S_i$

for one server, or $m_i / S_i$ for $m_i$ identical servers. The **bottleneck law** for a pipeline follows immediately: system throughput is capped by the slowest stage,

$$
X \le \min_i \frac{m_i}{S_i},
$$

and at that ceiling the bottleneck runs at $\rho = 1$ while every other stage idles in proportion. Two corollaries do most of the diagnostic work. Optimizing a non-bottleneck changes nothing measurable — the phrasing in [Millsap](https://queue.acm.org/detail.cfm?id=1854041) is that work on anything but the constraint is an illusion of progress. And the bottleneck moves after you fix it: relieving the constraint promotes the runner-up, so capacity planning is an iterative loop, not one calculation.

## The saturation curve

The queueing model sharpens "high utilization is dangerous" into a shape. For exponential arrivals and service (M/M/1; derivation in [[systems/operating-systems/v2-concurrency/7-queueing-theory|Queueing Theory]]):

$$
R = \frac{S}{1 - \rho}
$$

| $\rho$ | 0.5 | 0.8 | 0.9 | 0.95 | 0.99 |
| --- | --- | --- | --- | --- | --- |
| $R/S$ | 2 | 5 | 10 | 20 | 100 |

The pole at $\rho = 1$ separates two regimes worth naming precisely. **Stable** ($\lambda < \mu$): queues form and drain, response time is finite, and the table above prices the headroom. **Unstable** ($\lambda \ge \mu$): the queue grows without bound, $R$ is no longer a function of load but of *time* — every second of overload adds to a backlog that must be repaid — and throughput pins at $\mu$ while arrivals keep accumulating. A system past saturation does not degrade gracefully; it falls behind linearly. Simulation confirming the table, plus the variance and burstiness effects the M/M/1 model hides, are in the queueing note.

The curve also explains the knee heuristic: below $\rho \approx 0.7$-0.8, added load costs little latency; above it, each point of utilization costs more than the last. Operators leave headroom not from superstition but because the marginal price of utilization is convex.

## Finite buffers and dropped work

Real queues are bounded. A finite buffer converts unbounded delay into loss: when the queue is full, arrivals are dropped (or rejected, or timed out upstream). This is a genuine trade, not a defect — a bounded queue caps the worst-case $W_q$ a request can experience at (buffer length) x $S$, at the price of serving less than the offered load. Under sustained overload, a bounded queue is strictly better than an unbounded one, because an unbounded queue eventually holds only requests whose clients have already timed out: the server does full-price work to produce answers nobody is waiting for, which is the mechanism behind congestion collapse. Choosing the bound is choosing the worst latency you are willing to serve; admission control and load shedding are this idea applied deliberately.

## When the averages lie

Everything above is stated in means, and means hide two things. First, the *distribution* of $R$: at $\rho$ near 1 the tail grows faster than the mean (for M/M/1 the p99 is 4.6x the mean, and both scale as $1/(1-\rho)$), so an SLO on p99 saturates far earlier than a mean-based capacity plan predicts. Second, *mixtures*: a mean over two request classes, or over bursty and quiet periods, describes no real request — and burstiness raises queueing pain at identical average $\rho$ (worked example in the queueing note). The rule of thumb: plan capacity with the formulas here, but state objectives and read dashboards in percentiles — the full argument is in [[systems/performance/tail-latency-percentiles|Tail Latency, Percentiles, and Queueing Distributions]].

## Worked example

A request touches an API server ($S = 2$ ms CPU) and a database ($S = 8$ ms). Offered load 100 req/s. Demand: API $\rho = 0.2$, DB $\rho = 0.8$ — the DB is the bottleneck and caps throughput at 125 req/s. Expected in-flight count by Little's Law with $R \approx 2 + 8/(1-0.8) = 42$ ms: $N = 100 \times 0.042 = 4.2$ requests. If measured $N$ is 40, not 4, then measured $R$ must be ~400 ms — and the model says DB queueing is the only term that can be that large, before any profiler runs. Doubling DB capacity ($m = 2$) drops its $\rho$ to 0.4 and its queueing to $\approx 8/(1-0.4) = 13$ ms; the API at $\rho = 0.2$ was never worth touching.

## Related notes

- [[systems/operating-systems/v2-concurrency/7-queueing-theory|queueing theory]]
- [[systems/performance/tail-latency-percentiles|tail latency, percentiles, and queueing distributions]]
- [[systems/performance/streaming|Streaming Data]]
- [[ml/serving-systems/performance-modeling|performance modeling for model serving]]
- [[systems/scheduling/0-foundations/littles-law-and-bottleneck-analysis|Little's Law and bottleneck analysis]]

## Sources

- [Millsap (2010), Thinking Clearly about Performance, ACM Queue](https://queue.acm.org/detail.cfm?id=1854041)
- [Brewer, CS262 queueing theory notes](https://people.eecs.berkeley.edu/~brewer/cs262/queueing.pdf)
