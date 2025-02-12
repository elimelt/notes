---
title: Distributed Systems Consistency Models
category: other
tags: Consistency Models,Paxos,Linearizability,Sequential Consistency,Snapshot Reads,Causal Consistency,Processor Consistency,Memory Barrier/Fence
description: This document discusses various consistency models used in distributed systems, including Paxos, linearizability, sequential consistency, snapshot reads, causal consistency, processor consistency, and memory barriers. It explains the differences between these models and when to use them.
---

# Consistency

**Consistency**: the allowed semantics of operations that mutate a data store/shared object.

Consistency specifies the interface (as opposed to implementation) for behavior of your system. It is essentially the contract between the programmer and implementer. An **anomaly** is a violation of the consistency semantics of the system

## Types of Consistency

| Type                 | Description                               | 
|----------------------|-------------------------------------------|
| Strong Consistency   | The system behaves as if there is a single server. Systems that maintain a single consistent log of operations are often strongly consistent. |
| Weak Consistency     | Definitions vary, but basically just *not* strong consistency.  |
| Eventual Consistency | Weak consistency with any anomalies guaranteed to be temporary. |

## Coordinating through a KV Store

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

With strong consistency semantics, the above approach works fine. However, with eventual consistency, and particularly for any system without multi-key transactions, we might see the update for `storage.get(done)` before the update for `storage.get(key)`, leading to unexpected behavior.

## Formalization

[Read here](https://lamport.azurewebsites.net/pubs/interprocess.pdf) for more info/theory.

For a given RPC, the initial request starts at time $t$ and the reply returns at time $t + x$. We cannot be sure what happens during $(t, t + x)$, since the request/reply could be lost and retransmitted, and intermediate coordination sometimes has to take place.

With only a single server, you don't know precisely when the operation takes place, but we expect it to be some time in $(t, t + x)$. However, weaker consistency models relax this assumption, also sometimes allowing different readers to see different results concurrently.

We use different models because of the following tradeoffs:

- Performance: Consistency requires coordination, so there is often a tradeoff between the level of consistency and the performance of the system
- Availability: If some client is offline or some network failure occurs, we might be forced to abandon strong consistency
- Programmability: Weaker consistency models are harder to reason about and program with

### Lamport's Register Semantics

Registers hold a single value, and we define operations $r_i, $w(v)$ as the $i$th read, and a write to the register with value $v$. Each operation has some starting time and ending time.

- A read is **safe** if it is not concurrent with any write, and thus obtains the previously written value.
- A read is **regular** if it is either safe, or if concurrent with a write, obtains either the old or new value.
- A read/write is **atomic** if operations are safe, or if reads and writes behave as if they occur in some definite order.


| Semantics | Constraints          |
|-----------|----------------------|
| safe      | $r_1 \to v_1$         |
| regular   | $r_1 \to v_1 \land (r_2 \to v_1 \lor r_2 \to v_2) \land (r_3 \to v_1 \lor r_3 \to v_2)$ |
| atomic    | $r_1 \to v_1 \land (r_2 \to v_1 \lor r_2 \to v_2) \land (r_3 \to v_1 \lor r_3 \to v_2) \land (r_2 \to v_2 \implies t_3 \to v_2)$ |

```plaintext
            r1           r2     r3
          |----|       |----| |----|
   w(v1)                w(v2)
|------|             |---------|
```

## Linearizability

A **linearizable** system is one in which actions appear to occur in a single global order that is consistent with real time/causal order. Not all systems enforce linearizability.

To do linearizable reads in Paxos, you need to first verify that the leader is **still** the leader at the time of the read. Otherwise, its possible that some other leader took over and formed a majority without the old leader. This can be done by waiting for the leader to execute some other request, which will only go through if we are indeed still the leader.

### Linearizable Sharding with Paxos

For linearizability with shards, we have the following requirements:

- All operations from the same node occur in order
- All operations to the same shard occur in order
- All operations complete between the request send and response receive.

Parallelism/concurrency of batched requests becomes difficult in a sharded system, since breaking up operations of a batched request into a pipeline completely throws out the original order of the request. We can instead think of systems in terms of a weaker consistency model.

### Sequential Consistency

**Sequential Consistency** is a weaker form of consistency that requires all operations to be executed in some order that is consistent with the order in which they were issued. However, S.C. doesn't always follow real-time order. This is also referred to as **serializability** in the context of transactions.

Simplistically, we can think of sequential consistency as a system where all operations are executed in some order that is consistent with the order in which they were issued, but not necessarily during their window of request/response timing. This allows stale reads, while still maintaining some order that is consistent with a prefix of the global state of the system.


### Snapshot Reads

Gives us a consistent view of our global state across some set of views of the system. This requires all operations being serializable, but it is okay if reads return stale data.

- All reads in a transaction must be from the same snapshot
- Client can define how old is too old for their usecase

To implement this (without sharding) in conjunction with Paxos, we can do the following:

1. Primary defines update order in log
2. Shadow replicas apply changes in that order
3. Each lag primary from some variable amount
4. Snapshot reads occur at a single replica
5. If a replica crashes during a transaction, restart transaction at another snapshot replica

### Causal Consistency

- Causally related reads and writes (ordered by happens before relation) must occur in that order.
- Concurrent writes can be seen in different orders on different nodes
- Note that linearizability imples causality

### Processor Consistency

- Writes done by the same process are seen in that order.
- Writes by different processors can be seen in different orders by different readers

### Memory Barrier/Fence

- Whenever consistency matters, you can insert a "fence" in a point of time that says all preceding operations happen before the fence, and all subsequent operations happen after
- On either side of the fence, order is not enforced
- If every operation is fenced, your system is linearizable

This is how POSIX files work. Also many mutli-cache systems use fences to enforce consistency.
