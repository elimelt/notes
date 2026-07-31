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
updated: 2026-07-31
status: evergreen
description: A compact model for reasoning about service time, arrival rate, queueing, and the bottlenecks they create.
---

## Purpose

This note records the small set of quantities I keep reaching for when a system feels slow.

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

## Bottlenecks

A bottleneck is the stage with the highest demand relative to its capacity. If stage $i$ needs $S_i$ seconds of a resource per request, then its maximum throughput is roughly

$X_i^{max} \approx 1 / S_i$

for one server, or $m_i / S_i$ for $m_i$ identical servers.

Optimizing a non-bottleneck changes little. Optimizing the bottleneck either raises system throughput or lowers queueing where it forms.

## Related notes

- [[systems/operating-systems/v2-concurrency/7-queueing-theory|queueing theory]]
- [[systems/performance/streaming|Streaming Data]]
- [[ml/serving-systems/performance-modeling|performance modeling for model serving]]
