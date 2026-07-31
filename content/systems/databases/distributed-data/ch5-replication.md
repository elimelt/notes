---
title: Replication Strategies in Distributed Data Systems
aliases:
  - designing-data-intensive-applications/part-2-distributed-data/ch5-replication
category: Database Systems
tags:
  - data-replication
  - leader-follower-model
  - synchronous-vs-asynchronous
  - failover
  - replication-logs
date: 2023-12-26
updated: 2026-07-30
status: evergreen
description: Reading notes on chapter 5 of Designing Data-Intensive Applications. Covers leader-based replication, synchronous versus asynchronous propagation, failover, and the main replication log implementations.
sources:
  - title: Designing Data-Intensive Applications, Martin Kleppmann
    url: https://dataintensive.net/
    type: book
  - title: "Chain Replication for Supporting High Throughput and Availability (van Renesse and Schneider, OSDI 2004)"
    url: https://www.cs.cornell.edu/home/rvr/papers/OSDI04.pdf
    type: paper
---

## Purpose

Reading notes on chapter 5 of [Designing Data-Intensive Applications](https://dataintensive.net/) by Martin Kleppmann, focused on leader-based replication: why replicate at all, synchronous versus asynchronous propagation, what failover involves, and how replication logs are implemented.

## Why replicate

Replication keeps a copy of the same data on multiple machines connected by a network. It buys three things:

- **High availability.** If one machine goes down, the data can still be served from others.
- **Latency.** Replicas in different locations let users read from the machine closest to them.
- **Read scalability.** Splitting read load across machines raises the read throughput the system can handle.

Most replicated data systems follow one of single-leader, multi-leader, or leaderless replication. The hard part in all of them is keeping replicas consistent with each other when the data changes.

## Leaders and followers

Leader-based replication (historically called master-slave, also active/passive) is the simplest form. One node is the leader and the rest are followers. The leader handles all writes and propagates the changes to the followers, which serve reads. If the leader dies, a follower is promoted.

Many relational databases use this setup, as do some non-relational databases and non-database systems like the distributed message brokers Kafka and RabbitMQ.

## Synchronous versus asynchronous replication

With **synchronous replication**, the leader waits for the follower's acknowledgment before confirming the write to the client, so the follower is guaranteed to have an up-to-date copy. The cost is availability: if the follower is slow or down, the leader cannot confirm the write and blocks. Waiting on many synchronous followers compounds this, since any one of them can stall all writes.

In practice, enabling synchronous replication usually means **semi-synchronous replication**: one synchronous follower, everyone else asynchronous. If the synchronous follower goes down, an asynchronous one is promoted to synchronous. This guarantees at least two up-to-date copies of the data without letting any single follower block writes forever.

Leader-based replication is often fully **asynchronous**: the leader confirms writes without waiting for any follower. The leader keeps accepting writes even when followers are down, but followers can fall arbitrarily behind, which is called **replication lag**. Durability is weakened too: if the leader fails and an out-of-date follower is promoted, writes that were confirmed but never replicated are lost.

### Chain replication

Preventing that durability loss without giving up throughput is an active research area. [Chain replication](https://www.cs.cornell.edu/home/rvr/papers/OSDI04.pdf) is a variant of synchronous replication in which nodes form a chain: writes enter at the head, pass node to node down the chain, and are acknowledged from the tail once every node has them. Every acknowledged write therefore exists on all replicas. The protocol handles failures by having a coordination service cut the failed node out of the chain, after which writes resume.

## Setting up new followers

A naive file copy would capture different parts of the data at different points in time. Instead:

1. Take a consistent snapshot of the leader's database, ideally without locking writes.
2. Copy the snapshot to the new follower node.
3. The follower connects to the leader and requests all writes since the snapshot, identified by a position in the replication log (the log sequence number in Postgres, the binlog coordinates in MySQL).
4. The follower processes the backlog until it catches up.

## Handling node outages

The goal is to keep the system as a whole running through individual failures, ideally allowing single-node reboots without disruption.

### Follower failure: catch-up recovery

A recovering follower replays the log on its local disk, then requests from the leader every write it missed while it was down.

### Leader failure: failover

Failover is much harder. It has three steps:

1. Determine that the leader failed, passively via timeout or actively via heartbeats.
2. Choose a new leader, through an election or a designated controller node. The best candidate is the replica with the most up-to-date data.
3. Reconfigure the system so clients write to the new leader and followers replicate from it.

Common failure modes:

- With asynchronous replication, the new leader may lack writes the old leader confirmed. Some systems discard those writes, which sacrifices durability.
- Two nodes can both believe they are the leader, called **split brain**. If both accept writes, conflicting data is hard or impossible to reconcile. Systems try to detect this and shut one node down, and have to be careful not to shut down both.
- The failure-detection timeout is a trade-off. Too short causes unnecessary failovers under load spikes; too long stretches the outage.

## Implementation of replication logs

### Statement-based replication

The leader logs every write request (each SQL statement, in a relational database) and ships the log to followers, which parse and execute each statement as if a client had issued it. Problems:

- Nondeterministic functions like `NOW()` and `RAND()` produce different values on each replica.
- Statements that depend on existing data, like auto-incrementing keys, must execute in exactly the same order, which constrains concurrency.
- Side effects such as triggers may behave differently per replica.

Workarounds exist, for example replacing nondeterministic calls with literal values at log time, but statement-based replication is mostly historical. MySQL used it before 5.1 and still falls back to it for statements it can prove deterministic.

### Write-ahead log (WAL) shipping

The storage engine already appends every write to a WAL. The leader ships that same byte sequence to followers, which apply it to build identical data structures. Postgres and Oracle use this approach. The drawback is coupling: the WAL describes data at the level of disk blocks and bytes, so leader and followers must run the same database software, often the same version. That coupling can rule out zero-downtime upgrades. The upgrade pattern of upgrading followers first, failing over, then upgrading the old leader only works when the new version can still read and write the old log format.

### Logical (row-based) log replication

Use different formats for the storage engine's physical log and the replication log. A logical log for a relational database is a sequence of records describing row-level changes:

- An inserted row logs all its column values.
- A deleted row logs enough to identify it, typically the primary key.
- An updated row logs its identity plus the new values.

A multi-row transaction logs one record per row plus a commit record; the MySQL binlog uses this approach in row-based mode. Logical logs decouple replication from storage engine internals, which restores cross-version compatibility and lets external systems consume the change stream, feeding data into Kafka, Elasticsearch, or a cache. Consuming a database's logical log this way is called change data capture.

## Sources

- [Designing Data-Intensive Applications](https://dataintensive.net/), Martin Kleppmann, chapter 5
- [Chain Replication for Supporting High Throughput and Availability](https://www.cs.cornell.edu/home/rvr/papers/OSDI04.pdf), van Renesse and Schneider, OSDI 2004

## Related notes

- [[systems/distributed-systems/consistency|consistency]]
- [[systems/distributed-systems/primary-backup|primary-backup replication]]
- [[systems/databases/foundations/ch4-encoding-and-evolution|encoding and evolution]]
