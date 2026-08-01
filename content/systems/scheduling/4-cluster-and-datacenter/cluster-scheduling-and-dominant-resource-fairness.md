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
updated: 2026-08-01
status: evergreen
description: Scheduling when jobs compete for several resource types at once - why single-resource fairness breaks, DRF with its properties and the canonical worked allocation, placement and preemption tradeoffs, and how Mesos, YARN, Borg, and Kubernetes divide the problem.
sources:
  - title: "Mesos: A Platform for Fine-Grained Resource Sharing in the Data Center"
    url: https://www.usenix.org/event/nsdi11/tech/full_papers/Hindman.pdf
    type: paper
  - title: "Dominant Resource Fairness: Fair Allocation of Multiple Resource Types"
    url: https://www.usenix.org/system/files/conference/nsdi11/nsdi11-ghodsi.pdf
    type: paper
  - title: "Large-scale cluster management at Google with Borg"
    url: https://research.google/pubs/pub43438/
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

## The Canonical Allocation, Traced

The [DRF paper's](https://www.usenix.org/system/files/conference/nsdi11/nsdi11-ghodsi.pdf) running example, executed as progressive filling — repeatedly grant a task to the user with the *lowest* dominant share (script run in the repo venv, this trace verbatim). Cluster (9 CPU, 18 GB); user A's tasks need (1 CPU, 4 GB) — memory-dominant; user B's need (3 CPU, 1 GB) — CPU-dominant:

| step | granted to | A tasks | A dom. share | B tasks | B dom. share | CPU used | mem used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | A | 1 | 4/18 = 0.222 | 0 | 0 | 1/9 | 4/18 |
| 2 | B | 1 | 0.222 | 1 | 3/9 = 0.333 | 4/9 | 5/18 |
| 3 | A | 2 | 0.444 | 1 | 0.333 | 5/9 | 9/18 |
| 4 | B | 2 | 0.444 | 2 | 0.667 | 8/9 | 10/18 |
| 5 | A | 3 | 0.667 | 2 | 0.667 | 9/9 | 14/18 |

Final allocation: A gets 3 tasks (3 CPU, 12 GB), B gets 2 tasks (6 CPU, 2 GB), dominant shares equal at $2/3$, and the cluster's CPU is exhausted — no further task fits. Neither user's raw share is "equal" on any single resource (A holds 2/3 of memory, B holds 2/3 of CPU); each is equal on the axis where it is hungriest, which is the fairness DRF sells.

## Why DRF and Not Something Simpler

The DRF paper evaluates alternatives and the failure modes are instructive. **Asset fairness** (equalize the sum of resource shares) can leave a user better off *outside* the shared cluster than in it, violating **sharing incentive**. Equalizing per-resource shares independently is gameable. DRF satisfies the four properties the paper argues a datacenter allocator needs:

- **Sharing incentive**: every user does at least as well as under a static $1/n$ partition of the cluster.
- **Strategy-proofness**: inflating your stated demand cannot increase your allocation — important because users demonstrably pad their asks when it helps (the paper cites production examples).
- **Envy-freeness**: no user prefers another's allocation.
- **Pareto efficiency**: no allocation change helps someone without hurting someone else.

DRF is max-min fairness from [[systems/scheduling/3-network-and-packet/fair-queueing-wfq-and-drr|fair queueing]] applied to dominant shares — the same progressive-filling waterline, with each user measured along their own steepest axis. Weighted DRF divides dominant shares by per-user weights, giving priority classes the same way WFQ's weights do.

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

## Placement, Packing, and Preemption

Fairness decides *who*; placement decides *where*, and the objectives conflict:

- **Locality**: put the task near its data. Delay scheduling (wait briefly for a slot on the right machine rather than taking the first offer) recovers most locality at small latency cost.
- **Packing vs. fragmentation**: bin-packing tasks tightly raises utilization but leaves odd-shaped holes no pending task fits; [Borg](https://research.google/pubs/pub43438/) scores placements to balance packing against leaving room, and deliberately mixes latency-sensitive and batch work on the same machines to reclaim stranded capacity.
- **Anti-affinity and spreading**: replicas of one service must not share failure domains, directly opposing packing.
- **Preemption**: when a high-priority job arrives and nothing fits, evict lower-priority tasks. Cheap for stateless batch work with checkpoints, expensive for anything warm; preemption churn is itself a utilization tax, so schedulers rate-limit it and prefer to preempt the newest or least-progressed tasks.

## Real Systems

The architectural split the Purpose section promises shows up in every production scheduler, in different places:

- **Mesos**: two-level via resource *offers* — the allocator applies (weighted) DRF to decide which framework is offered resources next, and the framework's own scheduler decides placement, accepting or declining offers. DRF is literally the allocator module.
- **YARN**: the Capacity and Fair schedulers both ship DRF as the multi-resource policy option (`DominantResourceCalculator`); queues get dominant-share fairness, applications get containers within queues.
- **Borg**: quota and priority bands rather than continuous DRF, with a scoring-based placement engine and aggressive overcommit reclaimed by eviction; the paper's utilization argument — shared multi-workload cells beat segregated ones by enough to pay for the whole scheduler — is the economic case for all of this machinery.
- **Kubernetes**: requests/limits per resource with a filter-then-score placement cycle descended from Borg's; fairness across tenants is bolted on above (namespace quotas), which is why multi-tenant K8s fairness remains rougher than Mesos-style DRF.

GPU clusters strain the model: GPUs are indivisible, workloads are gang-scheduled (all-or-nothing groups), and placement is topology-sensitive (NVLink domains), which pushes schedulers toward reservation and packing heuristics layered over the fairness substrate — the serving-side scheduling story continues in [[systems/scheduling/5-ml-and-serving/request-scheduling-for-llm-serving|request scheduling for LLM serving]].

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
- [[systems/scheduling/4-cluster-and-datacenter/stragglers-speculation-and-overload|Stragglers, Speculation, and Overload]]

