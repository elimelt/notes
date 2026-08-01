---
title: Failure Detectors, Leases, and Leader Election
category: Distributed Systems
tags:
  - failure detectors
  - leases
  - leader election
  - distributed coordination
  - fencing
date: 2026-08-01
status: draft
description: How systems suspect failure, bound authority with time, and elect leaders - the Chandra-Toueg detector hierarchy, lease mechanics under clock drift, fencing tokens, and the Chubby, ZooKeeper, etcd, and Raft patterns.
sources:
  - title: Chandra and Toueg (1996), Unreliable Failure Detectors for Reliable Distributed Systems
    url: https://dl.acm.org/doi/10.1145/226643.226647
    type: paper
  - title: Burrows (2006), The Chubby Lock Service for Loosely-Coupled Distributed Systems
    url: https://research.google/pubs/pub27897/
    type: paper
  - title: Gray and Cheriton (1989), Leases - An Efficient Fault-Tolerant Mechanism for Distributed File Cache Consistency
    url: https://dl.acm.org/doi/10.1145/74850.74870
    type: paper
  - title: Kleppmann (2016), How to Do Distributed Locking
    url: https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
    type: blog
---

## Purpose

The machinery underneath [[systems/distributed-systems/paxos-intro|consensus]] and [[systems/distributed-systems/managing-critical-state|critical-state management]]: how a system decides someone is dead, how it grants time-bounded authority, and how it keeps two nodes from both acting as leader. The theory says perfect detection is impossible; the engineering answer is to make *wrong* detection safe and merely slow.

## Suspicion is all you get

In an asynchronous system — unbounded message delay, unbounded processing pauses — a crashed process and a slow one are indistinguishable by any observation. This is the operational content of the FLP impossibility result (Fischer, Lynch, Paterson 1985): deterministic consensus is unsolvable with even one possible crash, because no protocol can safely wait out the ambiguity. Every real "failure detector" is therefore a *suspicion* mechanism whose verdicts can be wrong, and every correct system design starts from the question: what happens when it is?

[Chandra and Toueg (1996)](https://dl.acm.org/doi/10.1145/226643.226647) turned this into a taxonomy by scoring detectors on two axes — **completeness** (crashed processes get suspected) and **accuracy** (correct processes do not) — and asking how much accuracy consensus actually needs. The hierarchy: a perfect detector $P$ (never suspects a correct process) requires synchrony no real network has. The consequential class is **eventually strong** $\Diamond S$: suspicion can be arbitrarily wrong for an arbitrary prefix, as long as *eventually* some correct process stops being suspected by anyone. Their two theorems frame all of practice: consensus is solvable with $\Diamond S$ plus a majority of correct processes, and (with Hadzilacos) nothing weaker suffices — $\Diamond W$/$\Omega$, the "eventual leader oracle," is the weakest detector for consensus. The translation: a system does not need reliable failure detection, only an eventually-stable leader hint plus quorums — which is exactly the shape of Paxos and Raft.

Practical detectors approximate $\Diamond S$ with heartbeats and timeouts. The tuning tension is fundamental: short timeouts detect fast but suspect wrongly under load spikes (and a wrongly-suspected leader triggers a gratuitous election, which causes more load — a classic metastable loop); long timeouts are calm but leave the system leaderless longer after real crashes. Two refinements are standard. The **phi-accrual detector** (Cassandra, Akka) replaces the binary verdict with a suspicion level computed from the observed heartbeat-interval distribution, letting the timeout adapt to current network behavior. **SWIM**-style protocols decouple detection (randomized pings, with indirect probes through third parties before declaring suspicion) from dissemination (gossip), keeping per-node load constant as the cluster grows.

## Leases: authority with an expiry date

A **lease** ([Gray and Cheriton 1989](https://dl.acm.org/doi/10.1145/74850.74870)) is a grant of authority — cache validity, lock ownership, leadership — valid for a bounded time and renewable by communication. The crucial property: expiry needs no communication. If the holder crashes or partitions, the grantor waits out the term and reassigns; a lock with a timeout is a lease. Correctness does not require synchronized clocks, only **bounded drift rate**: grantor and holder each measure the term on their own clock, and if clocks tick within (say) 1% of true rate, the grantor adds a small margin and the holder conservatively expires early. Bounded-rate assumptions are among the safest in systems practice — this is the same clock discussion as [[systems/distributed-systems/clocks|Clocks]], but leaning only on rates, not on synchronization.

The trap is what the holder does at the edge. [Kleppmann's distributed-locking critique](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html): a client acquires a lease, then stalls — GC pause, VM migration, swap storm — past its expiry. The lease service correctly reassigns. The stalled client resumes *believing it holds the lease* (its check ran before the pause) and writes to shared storage: two writers, data corrupted, and no amount of timeout tuning fixes it, because the pause can exceed any timeout. The fix is the **fencing token**: the lease service issues a monotonically increasing number with each grant, every write to the protected resource carries it, and the resource rejects tokens older than the highest seen. The stale writer's token is stale; the write bounces. The same mechanism recurs as Raft's term numbers, ZooKeeper's zxid epochs, and Chubby's lock generation numbers — versioned authority, checked at the point of effect, is the universal answer to "the detector was wrong and the old leader is still moving."

This is the safety/liveness split in one sentence: **timeouts and elections provide liveness** (a dead leader is eventually replaced), while **quorums and fencing provide safety** (a falsely-suspected leader cannot do damage) — wrong suspicion may slow the system, but must never corrupt it.

## Leader election in practice

**Chubby** ([Burrows 2006](https://research.google/pubs/pub27897/)) is the canonical packaging: a Paxos-replicated, five-node lock service exposing a small filesystem with advisory locks, built explicitly for coarse-grained use — locks held for hours, not milliseconds, so the cost of an election amortizes. Clients hold **sessions** maintained by keepalive RPCs with a ~12-second lease; if a session's lease lapses, the client enters a ~45-second grace period ("jeopardy") in which caches are disabled but handles survive, masking brief master failovers. Applications elect leaders by racing to acquire a lock file: GFS and Bigtable both pick masters this way, and the winner writes its identity into the file for discovery. Ephemeral files double as liveness signals. Burrows's deployment observation is a design lesson in itself: a service intended for election and configuration became, in practice, a name server — coarse coordination points attract every use that needs "one agreed value, rarely changed."

**ZooKeeper**'s election recipe: every candidate creates a sequential-ephemeral znode; the lowest sequence number is leader; each other node watches only its immediate predecessor. When the leader's session dies, its znode vanishes and exactly one successor wakes — avoiding the thundering herd of everyone re-racing. **etcd** exposes election directly over its lease API: campaign on a key bound to a lease, leadership persists while the lease is kept alive, and the key's creation revision serves as the fencing token. **Raft** internalizes election into the consensus protocol: followers that miss heartbeats become candidates after a *randomized* timeout (the randomization is the entire split-vote-avoidance mechanism), majority vote elects, and the incremented term number fences the old leader — any RPC carrying a stale term is rejected by protocol rule.

All three reduce to the same layering, which is the note's takeaway:

```text
suspicion:  heartbeats + timeouts        (approximate an eventual leader hint)
liveness:   election on suspicion        (randomized or ordered tie-breaking)
authority:  lease with bounded term      (self-expiring, renewable)
safety:     epoch/term/fencing token     (checked by every downstream effect)
```

A coordination service sells this stack as a primitive so that applications above it — masters, shard owners, singleton workers — inherit consensus-grade safety while writing only lock-acquire loops. That inheritance has a condition: the *resources those applications write to* must check the fencing token too. A leader elected perfectly through Chubby can still corrupt a storage system that accepts unfenced writes; the election machinery bounds who may act, but only token checks at the data bound what a zombie can do.

## Related notes

- [[systems/distributed-systems/paxos-intro|Paxos Intro]]
- [[systems/distributed-systems/managing-critical-state|Managing Critical State]]
- [[systems/distributed-systems/mutual-exclusion|Mutual Exclusion]]
- [[systems/distributed-systems/clocks|Clocks]]
- [[systems/distributed-systems/google-file-system|Google File System]]
- [[systems/distributed-systems/bigtable|Bigtable]]

## Sources

- [Chandra and Toueg (1996), Unreliable Failure Detectors for Reliable Distributed Systems, JACM 43(2)](https://dl.acm.org/doi/10.1145/226643.226647)
- [Burrows (2006), The Chubby Lock Service for Loosely-Coupled Distributed Systems, OSDI](https://research.google/pubs/pub27897/)
- [Gray and Cheriton (1989), Leases: An Efficient Fault-Tolerant Mechanism for Distributed File Cache Consistency, SOSP](https://dl.acm.org/doi/10.1145/74850.74870)
- [Kleppmann (2016), How to Do Distributed Locking](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)
- [Ongaro and Ousterhout (2014), In Search of an Understandable Consensus Algorithm (Raft), USENIX ATC](https://raft.github.io/raft.pdf)
- [ZooKeeper recipes, leader election](https://zookeeper.apache.org/doc/current/recipes.html)
