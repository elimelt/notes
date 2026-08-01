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
updated: 2026-08-01
status: evergreen
description: Flow fairness in packet schedulers, from max-min fairness and bit-by-bit round robin through weighted fair queueing's virtual finish times to deficit round robin, with worked traces, a verified simulation, and a latency/fairness/complexity comparison.
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

Packet scheduling is the cleanest place to see fairness become mathematical. The core question is: if several flows share one output link, what does "fair" even mean? FIFO avoids almost all policy cost and answers that question badly. This note derives the answer — max-min fairness — then follows the implementation ladder from the fluid ideal (bit-by-bit round robin) through [WFQ's](https://dl.acm.org/doi/10.1145/75247.75248) virtual finish times to [DRR's](https://dl.acm.org/doi/10.1145/217391.217453) O(1) approximation, with traces at each step.

## Max-Min Fairness, and Why FIFO Fails It

An allocation is **max-min fair** if no flow's share can be increased without decreasing the share of a flow that already has less: satisfy small demands fully, then split what remains evenly among the unsatisfied. On one link, three flows demanding (2, 4, 10) Mbps of a 9 Mbps link get (2, 3.5, 3.5) — the demand below the fair share is met exactly, and the leftovers split.

FIFO allocates nothing of the kind. Service order is arrival order, so **bandwidth is proportional to bytes enqueued**: a flow that sends faster, or with bigger packets, takes more of the link, and a well-behaved flow's latency is set by how much backlog the aggressive flow keeps in the shared queue. [Demers, Keshav, and Shenker](https://dl.acm.org/doi/10.1145/75247.75248) frame the fair-queueing goal as exactly this isolation: a source should not be able to increase its share at others' expense. Nagle's earlier proposal — one queue per flow, packet-by-packet round robin — gets isolation but not fairness: a flow sending 1000-byte packets gets 10x the bandwidth of one sending 100-byte packets, since each "turn" is one packet regardless of size.

## Bit-by-Bit Round Robin and Virtual Time

The reference ideal fixes packet-size bias by shrinking the service unit to nothing: **bit-by-bit round robin** — one bit from flow 1, one from flow 2, and so on. In the fluid limit this is generalized processor sharing (GPS): each of the $n$ active flows progresses at rate $C/n$, exactly the processor-sharing ideal of [[systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling|CPU scheduling]] with packets for jobs.

Not implementable — but *simulatable*. Define **virtual time** $V(t)$ as the number of bit-rounds completed by time $t$: it advances at rate $C / n(t)$, slowing when more flows are active. A packet of length $L$ arriving when the fluid system would start serving it at virtual time $S$ would finish at virtual time $S + L$. That yields the per-packet **virtual finish time**, computable at arrival.

## Weighted Fair Queueing

WFQ transmits packets in increasing order of virtual finish time, giving flow $i$ weight $w_i$. For packet $k$ of flow $i$:

$$
F_i^k = \max(F_i^{k-1}, V(a_i^k)) + \frac{L_i^k}{w_i}
$$

where $a_i^k$ is arrival time and $L_i^k$ packet length. The $\max$ chooses between "flow is backlogged, start when my previous packet finishes" and "flow was idle, start now (at current virtual time)"; dividing by $w_i$ makes a weight-2 flow's packets finish virtual rounds twice as fast, yielding bandwidth in proportion to weight.

Worked trace (computed in the repo venv): flows A (3 x 1000 B), B (3 x 600 B), C (10 x 100 B) all backlogged at $V = 0$, equal weights. Finish times: A = 1000, 2000, 3000; B = 600, 1200, 1800; C = 100, 200, ..., 1000. Transmission order: C's first five packets (F = 100-500), then B's first (600) and C's sixth (600), interleaving so that after any prefix, each flow has received nearly equal *bytes* — C's ten mice all clear before A's second elephant. Under FIFO with A enqueued first, C's entire flow waits behind 3000 bytes of A.

The guarantee is tight: a WFQ packet finishes at most $L_{\max}/C$ later than it would under fluid GPS (the Parekh-Gallager bound), which for weighted flows turns into per-flow worst-case delay bounds — the foundation of link-level QoS guarantees.

The cost is the sorted structure: a priority queue over active flows' next finish times is $O(\log n)$ per packet, plus virtual-time bookkeeping ($n(t)$ changes on every arrival/departure). At line rate with a minimum-size packet every ~50 ns, that was unaffordable for 1990s router hardware and remains the reason pure WFQ lives in software schedulers, not fast paths.

## DRR

[Deficit Round Robin](https://dl.acm.org/doi/10.1145/217391.217453) keeps the spirit of fair queueing at $O(1)$ per packet. Each flow has a quantum $Q_i$ (its per-round byte budget) and a deficit counter $D_i$ (unspent budget). Each round, for each active flow:

1. add $Q_i$ to $D_i$
2. while the head packet fits ($L \le D_i$): send it, subtract its size
3. move on; keep the leftover deficit **only if the queue is nonempty** (reset to 0 on empty, so idle flows cannot bank credit)

```python
for flow in active_flows:
    flow.deficit += flow.quantum
    while flow.queue and flow.queue[0].size <= flow.deficit:
        pkt = flow.queue.pop(0)
        send(pkt)
        flow.deficit -= pkt.size
    if not flow.queue:
        flow.deficit = 0
```

The saved deficit is the whole point. A flow with large packets accumulates credit across rounds until a packet fits, so it is not permanently punished for packet size — Nagle's round robin with the size bias repaired.

Trace with the same three flows, $Q = 500$ (simulated in the repo venv, the loop above verbatim). Round 1: A banks 500 (< 1000, sends nothing), B banks 500 (< 600), C sends five 100 B packets and resets. Round 2: A's deficit reaches 1000 — first elephant goes out; B sends its first 600 B packet (deficit 400); C drains its remaining five. Round 3: B's second packet (deficit 300). By round 6 all 5800 bytes are out, and cumulative bytes per round track the equal-share line to within one packet. The Shreedhar-Varghese fairness theorem makes that precise: over any interval where two flows are both backlogged, their normalized service differs by $O(L_{\max} + Q)$ — a constant, versus FIFO's unbounded divergence — provided $Q \ge L_{\max}$, which is also the condition for $O(1)$ work per packet (every visited flow sends at least one packet per round).

The residual weakness is burstiness at round granularity: a flow can receive its whole round's allocation back-to-back rather than interleaved, so short-term delay jitter is worse than WFQ's — the price of dropping the sorted queue.

## FIFO vs WFQ vs DRR

| | FIFO | WFQ | DRR |
| --- | --- | --- | --- |
| Fairness | none; proportional to aggression | weighted max-min, tight bound | max-min within $O(L_{\max}+Q)$ per interval |
| Delay for mice | unbounded (behind elephants) | near-GPS, per-flow bounds | good, but round-granularity jitter |
| Isolation | none | per-flow | per-flow |
| Per-packet cost | $O(1)$ | $O(\log n)$ + virtual clock | $O(1)$ if $Q \ge L_{\max}$ |
| State | one queue | per-flow queue + sorted finish times | per-flow queue + one counter |
| Used in | default everywhere | software qdiscs, QoS edges, Linux CFS (as virtual runtime over threads) | hardware routers, `fq_codel`-family schedulers |

When per-flow state is too much, **stochastic fair queueing** hashes flows into a fixed set of queues, accepting occasional collisions; Linux's `fq_codel` combines that with per-queue [[systems/scheduling/4-cluster-and-datacenter/stragglers-speculation-and-overload|overload-aware]] dropping.

## What to Remember

- Max-min fairness is the objective; FIFO fails it because service order tracks arrival aggression.
- WFQ is the mathematically cleaner story: simulate the fluid system, transmit by virtual finish time, pay $O(\log n)$.
- DRR is the implementation-friendly story: a byte budget and a carry-over counter buy constant-factor fairness at $O(1)$.
- The same ladder — fluid ideal, virtual-time simulation, quantized approximation — reappears in CPU scheduling as processor sharing, stride scheduling/CFS, and round robin.

## Related Notes

- [[systems/networks/4-transport/TCP|TCP]]
- [[systems/networks/2-direct-links/multiple-access|Multiple Access]]
- [[systems/scheduling/4-cluster-and-datacenter/cluster-scheduling-and-dominant-resource-fairness|Cluster Scheduling and DRF]]

