---
title: Little's Law and Bottleneck Analysis
category: Scheduling
tags:
  - scheduling
  - queueing
  - little's law
  - bottlenecks
  - throughput
  - latency
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: "The small set of operational laws that keep showing up in scheduling arguments: utilization law, Little's Law, and bottleneck analysis, with simple derivations and code."
sources:
  - title: "Operating Systems: Principles and Practice"
    url: https://www.kea.nu/files/textbooks/ospp/
    type: textbook
  - title: "The Tail at Scale"
    url: https://research.google/pubs/the-tail-at-scale/
    type: paper
---

## Purpose

This note is the first scheduling note to memorize. Most system arguments about "too much load", "not enough headroom", or "wrong place to optimize" reduce to a handful of algebraic identities:

- utilization law
- Little's Law
- bottleneck law

They are not queueing-model assumptions. They are bookkeeping identities for stable systems.

## Model

Take one service stage with:

- arrival rate $\lambda$ requests/second
- throughput $X$ completions/second
- service time $S$ seconds/request
- response time $R$ seconds/request
- average number in service $U$
- average number in the whole system $N$

For a stable stage, long-run throughput equals long-run arrival rate:

$$
X = \lambda
$$

If the stage is unstable, the queue is growing and the averages are not stationary enough to be useful.

## Utilization Law

Apply Little's Law only to the server itself, not the queue. The average number of jobs "inside the server" is the utilization:

$$
U = X S
$$

For a single server, $U$ is the busy fraction, so $0 \le U \le 1$.

With service rate $\mu = 1/S$:

$$
U = \frac{X}{\mu}
$$

This is the cleanest way to check whether a plan is impossible. If a stage needs 3 ms of CPU per request and you want 500 requests/second from one core:

$$
U = 500 \cdot 0.003 = 1.5
$$

That is impossible on one core before queueing is even discussed.

## Little's Law

For any stable subsystem:

$$
N = X R
$$

Average concurrency equals throughput times average time spent inside.

This identity is more useful than it first looks because the subsystem can be chosen freely:

- the whole service
- one queue
- one RPC stage
- one disk
- the decode queue of a model server

If a service does 20,000 requests/second and p50 end-to-end time is 50 ms, the average concurrent requests implied by the mean relation is on the order of

$$
N \approx 20{,}000 \cdot 0.05 = 1000
$$

That does not say the distribution is narrow. It says any steady-state design claiming 20k QPS with only a handful of in-flight requests is wrong.

## Bottleneck Law

Suppose request $r$ visits stage $i$ an average of $V_i$ times and each visit costs service time $S_i$. The total demand per request at stage $i$ is

$$
D_i = V_i S_i
$$

Then stage $i$ cannot sustain throughput above

$$
X_i^{\max} = \frac{1}{D_i}
$$

for one server, or

$$
X_i^{\max} = \frac{m_i}{D_i}
$$

for $m_i$ identical servers.

The system throughput limit is the minimum across stages:

$$
X^{\max} = \min_i X_i^{\max}
$$

This is the operational form of "the bottleneck wins."

## Worked Example

Suppose one request does:

- 2 ms of CPU
- 6 ms of network-bound downstream wait on a pool of 4 workers, each spending 6 ms of service
- 1 ms of local serialization

The demands are:

$$
D_{\text{cpu}} = 0.002 + 0.001 = 0.003
$$

and

$$
D_{\text{rpc}} = 0.006
$$

with $m_{\text{rpc}} = 4$, so

$$
X_{\text{cpu}}^{\max} = \frac{1}{0.003} \approx 333
$$

and

$$
X_{\text{rpc}}^{\max} = \frac{4}{0.006} \approx 667
$$

The CPU side is the bottleneck. Speeding up the RPC pool changes little until CPU demand drops.

## Why Queueing Starts Late and Then Gets Ugly Fast

Operational laws tell you where the cliff is. Queueing models tell you how the cliff looks. In many systems the shape is:

- low utilization: $R \approx S$
- moderate utilization: queueing appears but is tolerable
- high utilization: tail latency explodes

That last step is why a bottleneck running at 95% can dominate the whole service even if all other stages are comfortable.

## Tiny Python Helper

```python
from dataclasses import dataclass

@dataclass
class Stage:
    name: str
    visits: float
    service_s: float
    servers: int = 1

    @property
    def demand_s(self) -> float:
        return self.visits * self.service_s

    @property
    def max_throughput(self) -> float:
        return self.servers / self.demand_s


stages = [
    Stage("cpu", visits=1, service_s=0.003, servers=1),
    Stage("rpc_pool", visits=1, service_s=0.006, servers=4),
]

for stage in stages:
    print(stage.name, stage.max_throughput)

print("system_limit", min(stage.max_throughput for stage in stages))
```

## What This Note Does Not Do

This note does not predict the full latency distribution. It only tells you:

- whether capacity math is even plausible
- how much concurrency a measured throughput implies
- which stage is limiting throughput

That is enough to rule out many bad explanations quickly.

## Related Notes

- [[systems/scheduling/0-foundations/queueing-models-and-tail-latency|Queueing Models and Tail Latency]]
- [[systems/performance/latency-throughput-and-utilization|Latency, Throughput, and Utilization]]
- [[systems/operating-systems/v2-concurrency/7-queueing-theory|Queueing Theory]]
