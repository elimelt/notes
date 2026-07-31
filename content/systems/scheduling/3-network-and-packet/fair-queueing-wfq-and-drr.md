---
title: Fair Queueing, WFQ, and DRR
category: Scheduling
tags:
  - scheduling
  - packet scheduling
  - fair queueing
  - wfq
  - drr
  - fairness
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Flow fairness in packet schedulers, from bit-by-bit round robin to weighted fair queueing and deficit round robin, with equations and pseudocode.
sources:
  - title: "Analysis and Simulation of a Fair Queueing Algorithm"
    url: https://dl.acm.org/doi/10.1145/75247.75248
    type: paper
  - title: "Efficient Fair Queueing Using Deficit Round Robin"
    url: https://dl.acm.org/doi/10.1145/217391.217453
    type: paper
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Packet scheduling is the cleanest place to see fairness become mathematical. The core question is:

- if several flows share one output link, what does "fair" even mean?

FIFO avoids almost all policy cost and answers that question badly.

## Bit-by-Bit Round Robin

The reference ideal is not packet-by-packet round robin. It is **bit-by-bit round robin**:

- serve one bit from flow 1
- then one bit from flow 2
- and so on

That ideal is not implementable, but it defines what fairness should approximate when packets have different lengths.

## Weighted Fair Queueing

WFQ approximates generalized processor sharing by assigning each packet a virtual finish time. For packet $k$ of flow $i$:

$$
F_i^k = \max(F_i^{k-1}, V(a_i^k)) + \frac{L_i^k}{w_i}
$$

where:

- $a_i^k$ is arrival time
- $L_i^k$ is packet length
- $w_i$ is the flow weight
- $V(t)$ is virtual time

Packets are transmitted in increasing order of $F_i^k$.

This gives a precise weighted fairness story, but maintaining a sorted structure over active flows is not cheap at line rate.

## DRR

Deficit Round Robin keeps the spirit of fair queueing without the expensive per-packet ordering.

Each flow has:

- a quantum $Q_i$
- a deficit counter $D_i$

On each round:

1. add $Q_i$ to $D_i$
2. if the head packet length is at most $D_i$, send it and subtract its size
3. keep sending while the next head packet still fits
4. otherwise move on and keep the leftover deficit

```python
for flow in active_flows:
    flow.deficit += flow.quantum
    while flow.queue and flow.queue[0].size <= flow.deficit:
        pkt = flow.queue.pop(0)
        send(pkt)
        flow.deficit -= pkt.size
```

The saved deficit is the whole point. A flow with large packets eventually accumulates enough credit to transmit them, so it is not permanently punished for packet size.

## Why FIFO Is Not Enough

With FIFO, one bursty or large-packet flow can dominate the queue seen by everyone else. Fair schedulers isolate flows from each other better:

- latency-sensitive mice are less likely to sit behind elephants
- weighted service can encode priorities
- fairness becomes per-flow rather than per-packet accident

## What to Remember

- WFQ is the mathematically cleaner story.
- DRR is the implementation-friendly story.
- FIFO is the baseline you beat when fairness or tail latency matters.

## Related Notes

- [[systems/networks/4-transport/TCP|TCP]]
- [[systems/networks/2-direct-links/multiple-access|Multiple Access]]
- [[systems/scheduling/4-cluster-and-datacenter/cluster-scheduling-and-dominant-resource-fairness|Cluster Scheduling and DRF]]

