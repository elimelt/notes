---
title: Replication Strategies in Distributed Data Systems
category: Distributed Systems
tags: data replication, leader-follower model, synchronous vs asynchronous, failover, replication logs
description: This document explores various replication strategies in distributed data systems, focusing on leader-follower models, synchronous and asynchronous replication, and handling node failures. It also discusses different implementations of replication logs and their implications for system consistency and durability.
---

# Chapter 5
## Replication

**Replication** is the process of keeping a copy of the same data on multiple machines that are connected via a network. Replication is important for a few reasons:

- **High Availability**: If one machine goes down, the data can still be served from other machines.
- **Latency**: If the data is replicated to multiple machines in different locations, the user can be served from the machine that is closest to them.
- **Scalability**: If the load is split between multiple machines, the system can handle more read requests.


Most distributed data systems that use replication follow one of **single-leader**, **multi-leader**, or **leaderless** replication. The hard part is keeping replicas consistent with each other in the event of updates.


## Leaders and Followers

Also known as **master slave** or **active passive** replication, this is the simplest form of replication. One node is designated as the **leader/master/primary** and the rest are **followers/slaves/secondary**. The leader handles all write requests and propagates the changes to the followers. The followers handle all read requests. If the leader goes down, one of the followers is promoted to leader. This is a common setup for relational databases. Followers are read-only, and writes are only sent to the leader.

Many relational, and some non-relational databases use this setup, as does non-database systems like distributed message-brokers (Kafka, RabbitMQ, etc.).


## Synchronous Versus Asynchronous Replication

The leader can propagate changes to the followers in two ways: **synchronous** and **asynchronous**. In synchronous replication, the leader waits for a response from the follower before acknowledging the write request. In asynchronous replication, the leader does not wait for a response from the follower before acknowledging the write request.

With synchronous replication, the leader can guarantee that the followers are up to date. However, if the network is slow or the follower is down, the leader cannot acknowledge the write request. This means that the leader cannot accept any more writes until the follower responds. This can cause a cascading failure if the leader is waiting on multiple followers. This is known as **write availability**.

If there is a substantial delay between the leader and the follower, the leader may not be able to accept any writes at all. This is known as **write latency**, and is a common problem with synchronous replication. In practice, if you enable synchronous replication in a database, this often means that you have a syngle syncronous follower, and the rest are asynchronous. This is known as **semi-synchronous replication**. If the synchronous follower goes down, the leader elects a new synchronous follower. This guarantees that there is always at least two up to date copies of the data.

Leader-based replication is often fully asynchronous. This means that the leader does not wait for a response from the follower before acknowledging the write request. This means that the leader can accept writes even if the follower is down. However, this means that the followers may not be up to date. This is known as **replication lag**. If the leader goes down, the follower with the most up to date data is elected as the new leader. This means that the new leader may not have all of the writes that the old leader had. This is known as **read-your-writes consistency** and is a tradeoff that incurs *weakened durability*. This is a common setup for non-relational databases.


## Research on Replication

Preventing data loss is a hot topic in distributed systems research. There are a few different approaches to this problem, but one example is **Chain Replication**, a variant of syncronous replication, where the leader sends the write to the first follower, which sends it to the second follower, and so on. The leader does not acknowledge the write until all followers have acknowledged it. This is a synchronous replication protocol that guarantees that the followers are up to date. However, it is not fault tolerant. If any follower goes down, the leader cannot accept any more writes. This is a common setup for distributed message brokers.


## Setting Up New Followers

A simple "file copy" might read across inconsistent snapshots of the data. To avoid this, maintain a consistent snapshot of the data by using a consistent snapshot protocol. Follower nodes start from snapshot and request all writes that have happened since the snapshot (using the log sequence number is Postgres and the binlog coordinates in MySQL). The leader keeps a log of all writes, and the followers request all writes since the snapshot. This workflow varies depending on the database.

1. take consistent snapshots periodically, and ideally asynchronously
2. copy the snapshot to the new follower node
3. the follower connects to the leader and requests all writes since the snapshot
4. follower processes backlog until it catches up to the leader

## Handling Node Outages

Goal is to keep the whole system running despite individual failures. Ideally should be able to reboot individual nodes without affecting the whole system.

### Follower Failure

If a follower fails, it can be restarted from the log located on its disk. Once the node has processed its log, it then requests any new writes from the leader. This is known as **catch-up recovery**.

### Leader Failure

If the leader fails, one of the followers is elected as the new leader during **failover**. This is way harder. It usually consists of the following:

1. Determining the leader failed. This can be acieved passively with a timeout or actively with a heartbeat.
2. Assigning a new leader. Can be done through an election process, or a designated controller node. Probably a good idea to look for nodes with most up-to-date data.
3. Reconfigure to use new leader. Set clients to write to new leader, and set followers to read from new leader.

#### Common problems with failover:

- With async replication, new leader might not have all writes in log. Some systems just throw these writes away, although this hurts our durability
- Scenarious leading to multiple nodes thinking they are leader (*split-brain*). If they both accept writes, it is difficult to resolve and may lead to data loss. Can try to detect this and shut one down, but need to be careful not to shut both down.
- Choosing a timeout has tradeoffs. Too short leads to unnecessary failovers, too long leads to longer time to recovery.


## Implementation of Replication Logs

### Statement-based replication

Leader logs ever write request (*SQL statement* in the case of a RDB) and sends log to followers. Each follower parses and executes the statement as if it were initiated by the client.

#### Problems:

- Non-deterministic functions (e.g. `NOW()`) will return different values on different machines
- Order of operations matters (ie auto incrementing keys)
- Side effects (e.g. triggers) may not be replicated

Although there are workarounds, usually not used today. MySQL <5.1 used it, and still sometimes does for deterministic functions.

### Write-ahead log (WAL) shipping

Append only sequence of bytes that record every write to the database. Leader sends WAL to followers, which apply the writes to their own database to build up the same data structures as the leader. Used by Postgres, Oracle, and more.

#### Problems:
- WAL is implementation specific (decided by leader), so followers must be same database as leader
- Couples replication to the storage engine and prevents easy migration and version upgrades

In particular, WAL prevent us from doing downtime-free upgrades. Without them, we could upgrade all the followers and catch them up, then failover and upgrade the leader. WAL make this impossible in many cases because the leader and follower must both read and write the same WAL format.

### Logical (row-based) log replication

Use different formats for storage engine (*physical*) log and replication (*logical*) log. For RDB, usually a sequence of records describing writes to rows in database.

- For inserted row, log contains all values
- for deleted row, log contains identifier of row (typically pk, or all values if none)
- for updated row, log contains identifier of row and new values

With multi-row transactions, log contains entry for all rows, as well as entry for transaction commit (MySQL binlog uses this approach)

Logical logs decouple the replication from the storage engine, allowing better compatibility between versions. Also allows integrations with external services (e.g. Kafka, Elasticsearch, etc.)