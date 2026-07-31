---
title: Cluster Scheduling and Dominant Resource Fairness
category: Scheduling
tags:
  - scheduling
  - cluster scheduling
  - dominant resource fairness
  - mesos
  - placement
  - multi-resource fairness
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Scheduling when jobs compete for several resource types at once, with the dominant-resource-fairness idea, placement tradeoffs, and a simple worked example.
sources:
  - title: "Mesos: A Platform for Fine-Grained Resource Sharing in the Data Center"
    url: https://www.usenix.org/event/nsdi11/tech/full_papers/Hindman.pdf
    type: paper
  - title: "Dominant Resource Fairness: Fair Allocation of Multiple Resource Types"
    url: https://www.usenix.org/system/files/conference/nsdi11/nsdi11-ghodsi.pdf
    type: paper
---

## Purpose

Cluster scheduling is different from CPU scheduling because jobs want vectors of resources, not one scalar quantity. A job may be:

- CPU hungry
- memory hungry
- GPU hungry
- network hungry

So "fair share" has to mean something multi-dimensional.

## Dominant Share

Suppose cluster capacity is

$$
C = (C_{\text{cpu}}, C_{\text{mem}}, C_{\text{gpu}})
$$

and user $i$ currently holds allocation vector

$$
x_i = (x_{i,\text{cpu}}, x_{i,\text{mem}}, x_{i,\text{gpu}})
$$

The share of resource $r$ is

$$
s_{i,r} = \frac{x_{i,r}}{C_r}
$$

The **dominant share** is the largest coordinate:

$$
d_i = \max_r s_{i,r}
$$

DRF equalizes dominant shares rather than raw CPU or memory fractions.

## Why Single-Resource Fairness Fails

If one job wants lots of CPU and little memory while another wants little CPU and lots of memory, equalizing only CPU share is not fair. One user can monopolize memory while looking innocent on CPU.

DRF fixes that by asking:

- on which resource is this user most "large" relative to cluster capacity?

That becomes the fairness coordinate.

## Tiny Example

Cluster capacity:

$$
(12 \text{ CPU}, 12 \text{ GB})
$$

Framework A task:

$$
(3 \text{ CPU}, 1 \text{ GB})
$$

Framework B task:

$$
(1 \text{ CPU}, 3 \text{ GB})
$$

After giving one task to each:

- A dominant share is $\max(3/12, 1/12) = 1/4$
- B dominant share is $\max(1/12, 3/12) = 1/4$

So one task each is balanced under DRF.

After two A tasks and one B task:

- A dominant share becomes $\max(6/12, 2/12) = 1/2$
- B dominant share stays $1/4$

So the next fair allocation should go to B.

## Placement Is More Than Fairness

Even if DRF decides who should get resources next, the scheduler still has to decide where to put the work:

- data locality
- anti-affinity
- fragmentation
- bin packing
- preemption cost

That is why many cluster schedulers split the problem:

- fair resource allocation policy
- placement policy

Mesos makes this explicit through resource offers.

## What the Cluster Scheduler Is Really Balancing

A production scheduler usually balances several incompatible goals:

- fairness between users
- locality to data
- high utilization
- low preemption churn
- isolation between workloads

There is no single scalar objective that captures all of them cleanly. DRF is one principled piece, not the whole scheduler.

## Related Notes

- [[systems/distributed-systems/load-balancing|Load Balancing]]
- [[ml/recommender-systems/intro-mapreduce-spark|MapReduce and Spark]]
- [[systems/scheduling/3-network-and-packet/fair-queueing-wfq-and-drr|Fair Queueing, WFQ, and DRR]]

