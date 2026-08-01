---
title: Distributed Systems Consistency Models
aliases:
  - distributed-systems/consistency
category: Distributed Systems
tags:
  - consistency-models
  - linearizability
  - sequential-consistency
  - causal-consistency
  - paxos
date: 2024-05-06
updated: 2026-08-01
status: evergreen
description: The consistency vocabulary hub - model comparison table, concrete operation histories for linearizability, sequential and causal consistency, and serializability, session guarantees, register semantics, and what stronger models cost in coordination.
sources:
  - title: "On Interprocess Communication (Lamport, 1986)"
    url: https://lamport.azurewebsites.net/pubs/interprocess.pdf
    type: paper
  - title: Herlihy and Wing (1990), Linearizability - A Correctness Condition for Concurrent Objects
    url: https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf
    type: paper
  - title: Jepsen, Consistency Models
    url: https://jepsen.io/consistency
    type: docs
---

## Purpose

This note is the vocabulary hub for consistency models: definitions from strong down to eventual, concrete histories that separate them, Lamport's register semantics, session guarantees, and what linearizability costs in a Paxos-based system. Database-side transaction isolation shares vocabulary but not definitions; the mapping is spelled out below and the details live in [[systems/databases/transactions-serializability-isolation|Transactions, Serializability, and Isolation Levels]].

## Core idea

**Consistency** is the allowed semantics of operations that mutate a data store or shared object. It specifies the interface of your system rather than the implementation, a contract between the programmer and the implementer. An **anomaly** is a violation of the consistency semantics of the system.

| Type                 | Description                               |
|----------------------|-------------------------------------------|
| Strong Consistency   | The system behaves as if there is a single server. Systems that maintain a single consistent log of operations are often strongly consistent. |
| Weak Consistency     | Definitions vary, but basically just anything short of strong consistency.  |
| Eventual Consistency | Weak consistency with any anomalies guaranteed to be temporary. |

## The models at a glance

Each model is a set of histories the system may exhibit; stronger models permit fewer. The [Jepsen hierarchy](https://jepsen.io/consistency) is the standard reference map. The comparison that matters day to day:

| Model | Real-time order? | Single total order? | Respects causality? | Multi-object? | Coordination needed |
|---|---|---|---|---|---|
| Linearizability | yes | yes (per object) | yes | no | quorum per operation |
| Sequential | no | yes | yes | no | total order broadcast |
| Serializability | no | yes (of transactions) | not necessarily | yes | concurrency control |
| Strict serializability | yes | yes (of transactions) | yes | yes | both of the above |
| Causal | no | no | yes | can be | metadata only (vector clocks) |
| Session guarantees | no | no | per-session only | no | sticky sessions / versions |
| Eventual | no | no | no | no | none (anomalies temporary) |

Two rows deserve flagging because the names mislead. **Serializability is not "sequential consistency for databases"** — it permits executing transactions in an order that contradicts real time (a transaction started *after* another committed may serialize *before* it), unless you pay for strict serializability. And **linearizability is per-object**: a system can be linearizable on every key yet exhibit non-serializable multi-key behavior, which is exactly the write-skew territory of [[systems/databases/mvcc-snapshot-isolation|MVCC and Snapshot Isolation]].

## Histories that separate the models

Notation: `P1: w(x,1)` means process P1 writes 1 to x; time runs left to right; `|--|` spans are operation durations. Following [Herlihy and Wing](https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf), a history is linearizable if each operation appears to take effect atomically at some point between its start and end.

**Linearizable vs. not.** x starts at 0:

```plaintext
P1:  |-- w(x,1) --|
P2:                  |-- r(x) -> 0 --|
```

P2's read *begins after* P1's write completes, yet returns the old value. No linearization point assignment can explain this — the write's point must precede the read's — so the history is not linearizable. It **is** sequentially consistent: the total order `r(x)->0, w(x,1)` respects each process's program order. This single history is the entire difference between the two models: sequential consistency lets the system order operations against real time, linearizability does not. A stale read from a replica produces exactly this history.

**Sequentially consistent vs. not.** Both start at 0:

```plaintext
P1: w(x,1)         P3: r(x)->1, r(y)->0
P2: w(y,1)         P4: r(y)->1, r(x)->0
```

P3 observes x's write before y's; P4 observes y's write before x's. Any single total order puts one of the writes first, contradicting one reader. Not sequentially consistent (and not causal-anomaly-free either — but note the writes here are concurrent, so *causal* consistency permits this history; that is the gap between causal and sequential).

**Causal vs. eventual.** The reply-before-post anomaly:

```plaintext
P1: w(post, "question")
P2: r(post)->"question", w(reply, "answer")     (reply caused by post)
P3: r(reply)->"answer", r(post)->null           (!!)
```

P2's reply is causally downstream of P1's post (P2 read it first). Causal consistency forbids P3 seeing the reply without the post; eventual consistency permits it, promising only that P3 *eventually* sees both. This is the anomaly that makes eventually-consistent systems maddening to program against, and the fix — tracking the happens-before relation of [[systems/distributed-systems/ordering-events-in-distributed-systems|ordering events]] — is what causal systems pay for with metadata instead of coordination.

**Serializable vs. strictly serializable.** T1 reads x then writes y; T2 writes x. T2 commits at 10:00; T1 starts at 10:05 and reads the *pre-T2* value of x. The serial order "T1 then T2" explains the reads, so the execution is serializable — even though T1 started after T2 committed in real time. Under strict serializability the real-time commit order binds, and T1's read would be an anomaly. Backup-restore and read-from-snapshot flows produce exactly this shape legally under plain serializability.

## Why the model matters

Consider coordinating two processes through a KV store:

```python
def Produce(key, lock, command):
  result = application.execute(command)
  storage.put(key, result)
  storage.put(lock, True)

def Consume(key, lock):
  while storage.get(lock) is False:
    pass
  return storage.get(key)
```

With strong consistency this works fine. With eventual consistency, and in particular in any system without multi-key transactions, the consumer might observe the write to `lock` before the write to `key`, and read a stale or missing result.

## Formalization

Lamport's [On Interprocess Communication](https://lamport.azurewebsites.net/pubs/interprocess.pdf) develops the theory. For a given RPC, the request starts at time $t$ and the reply returns at $t + x$. We cannot be sure what happens during $(t, t + x)$: the request or reply could be lost and retransmitted, and intermediate coordination sometimes has to take place.

With a single server you still don't know precisely when the operation takes effect, but you expect it to be some point within $(t, t + x)$. Weaker models relax this, sometimes allowing different readers to see different results concurrently.

We accept weaker models because of these tradeoffs:

- Performance: consistency requires coordination, so stronger consistency usually costs latency and throughput
- Availability: if a client is offline or the network partitions, strong consistency may be impossible to serve
- Programmability: weaker models are harder to reason about and program against

### Lamport's register semantics

Registers hold a single value. Define $r_i$ as the $i$th read and $w(v)$ as a write of value $v$. Each operation has a start time and an end time.

- A read is **safe** if it is not concurrent with any write, and thus obtains the previously written value.
- A read is **regular** if it is either safe, or, when concurrent with a write, obtains either the old or the new value.
- Reads and writes are **atomic** if operations are safe, or if reads and writes behave as if they occur in some definite order.

| Semantics | Constraints          |
|-----------|----------------------|
| safe      | $r_1 \to v_1$         |
| regular   | $r_1 \to v_1 \land (r_2 \to v_1 \lor r_2 \to v_2) \land (r_3 \to v_1 \lor r_3 \to v_2)$ |
| atomic    | $r_1 \to v_1 \land (r_2 \to v_1 \lor r_2 \to v_2) \land (r_3 \to v_1 \lor r_3 \to v_2) \land (r_2 \to v_2 \implies r_3 \to v_2)$ |

```plaintext
            r1           r2     r3
          |----|       |----| |----|
   w(v1)                w(v2)
|------|             |---------|
```

## Linearizability

A **linearizable** system is one in which operations appear to occur in a single global order consistent with real time. Not all systems enforce linearizability.

To serve a linearizable read from a Paxos leader, the leader must first verify it is still the leader at the time of the read. Otherwise another leader may have taken over and committed writes with a majority that excludes the old leader. One way to verify is to wait for the leader to successfully execute some other request, which only succeeds while it holds leadership.

### Linearizable sharding with Paxos

For linearizability across shards, we need:

- All operations from the same node occur in order
- All operations to the same shard occur in order
- All operations complete between the request send and the response receive

Batched requests make this painful. Splitting a batch into a pipeline across shards throws away the original order of the batch, so preserving linearizability kills the parallelism. This pressure is a big part of why weaker models get used.

## Weaker models

### Sequential consistency

**Sequential consistency** requires all operations to execute in some total order consistent with the order each process issued them, without requiring that order to match real time. It permits stale reads, while still guaranteeing every reader sees some prefix-consistent view of the system.

A terminology repair from the histories section: sequential consistency and **serializability** are frequently conflated, including in earlier drafts of this note, but they differ on both axes that matter. Sequential consistency is about single operations on single objects and preserves per-process program order; serializability is about multi-operation transactions over many objects and does *not* by itself constrain against real time — that stronger combination is strict serializability, which is what Spanner sells as "external consistency." The database-side ladder (read committed, snapshot isolation, serializable) is a different axis entirely — which anomalies transactions may observe — and lives in [[systems/databases/transactions-serializability-isolation|the transactions note]].

### Snapshot reads

Snapshot reads give a consistent view of global state at some point, while allowing that point to lag the present. Operations must still be serializable, but reads may return stale data.

- All reads in a transaction come from the same snapshot
- The client can define how stale is too stale for its use case

One implementation on top of Paxos, ignoring sharding:

1. The primary defines the update order in the log
2. Shadow replicas apply changes in that order
3. Each replica lags the primary by some variable amount
4. A snapshot read executes entirely at a single replica
5. If a replica crashes mid-transaction, the transaction restarts at another snapshot replica

### Causal consistency

- Causally related reads and writes (ordered by the happens-before relation) must be observed in that order
- Concurrent writes can be seen in different orders on different nodes
- Linearizability implies causal consistency

### Processor consistency

- Writes done by the same process are seen in that order
- Writes by different processors can be seen in different orders by different readers

### Memory barrier / fence

A **fence** marks a point such that all preceding operations happen before it and all subsequent operations happen after it. On either side of the fence, order is not enforced. If every operation is fenced, the system is linearizable. POSIX file operations follow this model, and multi-cache systems use fences to enforce coherence at chosen points.

## Session guarantees

Between causal and eventual sits a family of client-centric promises (Terry et al., from the Bayou project) that constrain only what *one session* observes, saying nothing about agreement across clients:

- **Read your writes**: a session's reads reflect its own earlier writes. The canonical violation: save a profile edit, refresh, see the old profile — write went to the primary, read went to a stale replica.
- **Monotonic reads**: once a session has seen a value, later reads see it or something newer; time never runs backward within a session.
- **Monotonic writes**: a session's writes apply everywhere in issue order.
- **Writes follow reads**: a write issued after reading some value is ordered after that value everywhere — the per-session slice of the reply-before-post guarantee.

All four together are equivalent to causal consistency for that session's operations. Implementations are cheap relative to their reassurance value: route a session stickily to one replica, or have clients carry version vectors and refuse to read from replicas that lag their high-water mark. Most "eventually consistent" products that feel sane to use — DynamoDB with session tokens, most CDN-backed apps — are session-guaranteed systems, which is why the anomalies users actually notice are so much rarer than raw eventual consistency permits.

## Why stronger models cost coordination

The table's rightmost column is the price list, and the prices are not implementation accidents:

- **Linearizability requires contacting a quorum on the critical path.** A read served locally, without checking that no newer write committed elsewhere, can produce the stale-read history above; hence leader reads with leases, read-index rounds in Raft, or quorum reads in Dynamo-style systems. Every one is a round trip that eventual consistency does not pay. The CAP theorem is the partition-time corner of this: a partitioned minority cannot serve linearizable operations at all, and the attainable-performance version (Attiya and Welch) shows latency proportional to network delay bounds even *without* partitions.
- **Sequential consistency requires agreeing on one order** — total order broadcast, which is consensus-equivalent — but not on real-time freshness, so reads can be stale but ordered.
- **Causal consistency is the strongest model attainable without giving up availability under partition**: it needs only metadata (version vectors) to travel with data, no synchronous coordination. That is its entire appeal, and the metadata growth is its tax.
- **Eventual consistency coordinates nothing** and hands the anomaly budget to the application, which is where [[systems/distributed-systems/crdts|CRDTs]] pick up: they keep the no-coordination property while making convergence automatic instead of ad hoc.

The engineering pattern that follows: mixed-consistency systems. Linearizable operations for the few paths that need them (uniqueness, counters that gate real resources, leader election through [[systems/distributed-systems/failure-detectors-leases-leader-election|leases and fencing]]), session or causal guarantees for user-facing reads, eventual for everything bulk. The consistency model is a per-operation choice, not a per-system one.

## Related notes

- [[systems/distributed-systems/clocks|clocks]]
- [[systems/distributed-systems/ordering-events-in-distributed-systems|ordering events in distributed systems]]
- [[systems/distributed-systems/distributed-cache-coherence|distributed cache coherence]]
- [[systems/distributed-systems/managing-critical-state|managing critical state]]
- [[systems/distributed-systems/crdts|CRDTs and conflict-free replication]]
- [[systems/databases/transactions-serializability-isolation|transactions, serializability, and isolation levels]]
