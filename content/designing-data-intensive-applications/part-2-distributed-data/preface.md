---
title: Scalable Distributed Data Systems
category: Distributed Systems
tags:
  - distributed-systems
  - scalability
  - fault-tolerance
  - shared-nothing-architecture
date: 2023-12-26
updated: 2026-07-30
status: evergreen
description: Reading notes on the preface to part 2 of Designing Data-Intensive Applications. Contrasts shared memory, shared disk, and shared nothing architectures for distributing data across machines.
sources:
  - title: Designing Data-Intensive Applications, Martin Kleppmann
    url: https://dataintensive.net/
    type: book
---

## Purpose

Reading notes on the preface to part 2 of [Designing Data-Intensive Applications](https://dataintensive.net/) by Martin Kleppmann. It sets up why data gets distributed across machines and which hardware architecture the rest of the book assumes.

## Why distribute data

Moving up a level to data systems that run on multiple machines, the motivations echo the single-machine concerns:

- **Scalability.** Split load between multiple machines.
- **Fault tolerance.** Keep serving when one or more machines fail.
- **Latency.** Put data geographically close to users, via CDNs, caching, and regional replicas.

## Scaling up

A **shared memory architecture** is a single computer with many CPUs sharing memory over a common bus. Doubling the power of one machine costs far more than double the price, and the shared bus becomes a bottleneck anyway.

A **shared disk architecture** gives each machine its own CPU and memory while all machines access the same disks over the network. This stretches further, and then the shared disks and the locking needed to coordinate access become the bottleneck.

## Scaling out

In a **shared nothing architecture**, each machine has its own CPU, memory, and disk. Each machine, physical or virtual, is a **node**, and nodes coordinate purely by sending messages over the network in software. This is the most scalable arrangement, and it pushes all the coordination problems into software, which is what the rest of part 2 is about.

Part 2 of the book focuses on shared nothing architectures.

## Sources

- [Designing Data-Intensive Applications](https://dataintensive.net/), Martin Kleppmann, part 2 preface

## Related notes

- [[designing-data-intensive-applications/part-2-distributed-data/ch5-replication|replication]]
