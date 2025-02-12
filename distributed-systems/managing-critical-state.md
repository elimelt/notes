---
title: Distributed Consensus Fundamentals
category: other
tags: Distributed Systems, Consensus Algorithms
description: This document covers the fundamentals of distributed consensus algorithms, including leader election, replicated state machines, reliable datastores, and coordination services.
---

# Managing Critical State
[reading](https://sre.google/sre-book/managing-critical-state/)

## CAP Theorem

The CAP theorem states that a distributed system can only guarantee two of the following three properties:
- **Consistency**: All nodes see the same data at the same time.
- **Availability**: Every request receives a response, without guarantee that it contains the most recent write.
- **Partition tolerance**: The system continues to operate despite network partitions.

Essentially, if some nodes go down in a distrubuted system, you can either choose to continue serving requests (availability), or to stop and wait for the nodes to come back up (consistency).

## ACID's Alternative: BASE

While ACID (Atomicity, Consistency, Isolation, Durability) lists properties that provide semantics for consistent transactions on a single node, this doesn't translate or scale well to distributed systems.

Instead, some datastores use BASE (Basically Available, Soft state, Eventually consistent) semantics, allowing for more flexibility in the face of network partitions. Most systems that support BASE semantics use multi-leader replication, where each leader can accept writes and propagate them to other leaders. This allows for better availability and partition tolerance, but at the cost of complexity to deal with eventual consistency in application code.

## Motivating the Use of Consensus: Distributed Systems Coordination Failures

### The Split Brain Problem

Split brain is where multiple nodes think they are the leader. A naiive approach to solving this is to use a heartbeat mechanism, where a leader sends out a heartbeat to followers. If multiple nodes think they are the leader, they will both send out heartbeats, and eventually one of the "leaders" will realize that there is another leader and issue a **STONITH** (Shoot The Other Node In The Head) command to kill the other leader.

However, due to the asynchronous and unreliable nature of networks, it is possible for these messages to be delayed to a point where both nodes issue a STONITH command to each other, causing both nodes to go down. Furthermore, the issue of actually detecting and avoiding a split brain is non-trivial, since it is difficult to distinguish between a network partition and a node failure, and nodes can be partitioned from eachother arbitrarily.

### Faulty Group Membership Algorithms

Using gossip protocols to maintain group memberships of clusters can lead to issues. Specifically, partitions within a cluster lead to multiple leaders being elected in the same cluster, often leading to data loss or corruption.

## How Distributed Consensus Works

In distributed software systems, we care about **asynchronous distributed consensus**, where nodes can fail and messages can be delayed, lost, or duplicated arbitrarily. Technically, this is impossible to solve in bounded time (see Dijkstra's FLP result), but we can solve problems by ensuring the system has sufficient healthy replicas and network connectivity, allowing the system to make progress *most of the time*. Futher, *exponential backoff* can be used to prevent cascading failures.

Some characteristics of distributed consensus algorithms include:
- **crash-fail**: nodes that fail never re-enter the system
- **crash-recovery**: nodes that fail can re-enter the system. This is more realistic, but also more complex.
- **Byzantine fault tolerance**: nodes can fail arbitrarily, including sending incorrect messages.

## Paxos Overview

Paxos is a distributed consensus algorithm that is used to ensure that a majority of nodes agree on a value. Importantly however, Paxos doesn't guarantee that all nodes agree on a value (this is impossible in an asynchronous network), but it does guarantee that a majority of nodes agree on a value.

Paxos operates as a sequence of proposals, which may or may not be accepted by a quorum (majority) of nodes. If a proposal isn't accepted, the proposal has failed/been rejected. Each proposal is given a `sequenceNumber`, such that there is a strict ordering of proposals. This `sequenceNumber` must be unique for all proposals, and must also be monotonically increasing.

In the first phase, a proposer sends a `sequenceNumber` to all acceptors. If the acceptors have not seen a proposal with a higher `sequenceNumber`, they respond with a `promise` to not accept any proposals with a lower `sequenceNumber`. Otherwise, they reject the proposal. Once a proposer has received a majority of `promise`s, it can commit the proposal by sending a `commit` message with a value.

The majority of nodes agreeing to a given proposal ensures that any committed proposal has a unique committed value, since two different quorums must have at least one node in common.

It is extremely important that any acceptors maintain a crash-recovery log of all proposals they have seen/accepted, so that they continue to honor their promises even after a crash.

## System Architecture Patterns for Distributed Consensus

Distributed consensus algorithms should be used as low-level building blocks for distributed systems, and should be hidden behind higher-level abstractions. This allows for better separation of concerns, and allows for easier testing and debugging. Furthermore, the specific protocol used can then be swapped out without affecting the rest of the system.

In fact, it is common to use a consensus service, such as Zookeeper, to provide distributed consensus within a system. Designing applications as clients to a consensus service allows for even better seperation of concerns, and is done at Google with Chubby.

### Reliable Replicated State Machines

A **replicated state machine** (RSM) is a system that maintains multiple copies of the same process by executing the same commands on all copies. Any deterministic program can be implemented as a highly available service by turning it into an RSM.

The order of operations is determined by a consensus algorithm running in a lower layer of the system. However, since there can be nodes part of a consensus group that aren't part of a given consensus quorum, nodes need to synchronize state from peers, which can be done using a **sliding-window protocol**.

### Reliable Replicated Datastores and Configuration Stores

Many non-distributed consensus-based storage systems use timestamps to determine order of operations, but this approach doesn't work in distributed systems (due to clock drift). While some systems (like Google's Spanner) use a probabilistic approach to determining timestamps (TrueTime), this gets complicated and expensive. There is inherent uncertainty in the time at any given nodes, and Spanner tries to account for this uncertainty, which also minimizing it through periodic slow-downs to resynchronize clocks.

Instead, distributed consensus protocols can be used when replicating data across multiple nodes. However, these protocols can be slow, especially since operations on a storage system are often small and frequent, yet consensus protocols require multiple round trips to complete.

### Highly Available Processing Using Leader Election

Leader election is an equivalent problem to distributed consensus, and is used in distributed systems to ensure that only one node is responsible for processing requests at a time. This might be used in cases where a single leader node is able to process requests, but it is often the case that a single leader needs to delegate work to a pool of worker nodes (like GFS or BigTable).

With this pattern, the leader election service is off of the critical path of the system, and so it has a smaller impact on the system's throughput.

### Distributed Coordination and Locking Services

A **barrier** is a synchronization primitive that allows a group of nodes to wait until all nodes have reached a certain point before continuing. This lets you split a distributed computation into multiple stages that must be completed in order. For instance, in MapReduce, a barrier is used to ensure that all mappers have finished before reducers start.

While barriers can be implemented as a single coordinator node, this introduces a single point of failure. Instead, once can use an RSM to implement a barrier, which is done by Zookeeper's implementation of the barrier pattern.

**Distributed locking** is a more general distributed synchronization primitive that allows for mutual exclusion of shared resources among nodes. In practice, it is essential to use renewable leases with timeouts to prevent deadlocks. Distributed locks are another fairly low-level primitive, and it is often a good idea to use a higher-level abstraction that provides distributed transactions.

### Reliable Distributed Queuing and Messaging
It is common to use a lease mechanism to ensure that only one node processes a message from a queue at a time, while also allowing for failover in case the node processing the message fails.

Queuing is also a powerful abstraction that can be used to implement other patterns like **atomic broadcast** and **publish-subscribe** messaging systems, where messages need to be reliably delivered to multiple nodes. This is useful for things like sending notifications to multiple clients, but can be used in other applications like distributed cache coherence. Furthermore, **queuing as workload distribution** can be used to distribute work among a pool of worker nodes

## Distributed Consensus Performance

People are apparently pretty pessimistic about the performance of distributed consensus algorithms, but they can actually be quite fast. According to Google SREs, this is not the case.

There are many factors that can affect the performance of distributed consensus algorithms, including:

- **Workload**
  - **Throughput**: number of proposals per second at peak load
  - Types of requests: read-heavy, write-heavy, mixed
  - **Consistency semantics**: can reads be stale?
  - **Request size**: how much data is being read/written?
- **Deployment**
  - **Network topology**: how many nodes are in the cluster, and how are they connected? LAN, WAN, etc.
  - **Quorum type**: how many nodes are in a quorum? Where are they located?
  - **Optimizations**: sharding, pipelining, batching, etc.

One common performance pitfall with single-leader replication is that a client's perceived latency is proportional to the round-trip time between the client and the leader.

### Multi-Paxos: Detailed Message Flow

