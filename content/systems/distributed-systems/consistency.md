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
updated: 2026-07-30
status: evergreen
description: Defines the common consistency models from strong to eventual, gives Lamport's register semantics, and covers how linearizability interacts with Paxos and sharding.
sources:
  - title: "On Interprocess Communication (Lamport, 1986)"
    url: https://lamport.azurewebsites.net/pubs/interprocess.pdf
    type: paper
---

## Purpose

This note defines the consistency models I keep reaching for, from strong down to eventual, and works through why weaker models exist at all. It also covers Lamport's register semantics and what linearizability costs in a Paxos-based system.

## Core idea

**Consistency** is the allowed semantics of operations that mutate a data store or shared object. It specifies the interface of your system rather than the implementation, a contract between the programmer and the implementer. An **anomaly** is a violation of the consistency semantics of the system.

| Type                 | Description                               |
|----------------------|-------------------------------------------|
| Strong Consistency   | The system behaves as if there is a single server. Systems that maintain a single consistent log of operations are often strongly consistent. |
| Weak Consistency     | Definitions vary, but basically just anything short of strong consistency.  |
| Eventual Consistency | Weak consistency with any anomalies guaranteed to be temporary. |

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

**Sequential consistency** requires all operations to execute in some total order consistent with the order each process issued them, without requiring that order to match real time. In the context of transactions this is called **serializability**. It permits stale reads, while still guaranteeing every reader sees some prefix-consistent view of the system.

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

## Related notes

- [[systems/distributed-systems/clocks|clocks]]
- [[systems/distributed-systems/distributed-cache-coherence|distributed cache coherence]]
- [[systems/distributed-systems/managing-critical-state|managing critical state]]
