---
title: Scalable Distributed Data Systems
category: Distributed Systems
tags: scalable distributed systems, scalability, fault tolerance, latency, shared memory architecture, shared disk architecture
description: Covers core concepts in building scalable distributed data systems, including scaling up and out through architectures like shared memory and shared disk, to achieve improved fault tolerance, reduced latency, and increased system capacity. It likely delves into the trade-offs between these approaches and their applications in real-world distributed systems. The focus is on technical details of scalability and its relationship with distributed data systems.
---

# Preface
## Distributed Data

Moving up a level to data systems that run on multiple machines, we still care about similar things.

- **Scalability**: splitting load between multiple machines
- **Fault tolerance**: tolerating failure at one or more machines
- **Latency**: minimizing the time between a request and response using geographic proximity of CDNs, caching, etc.

### Scaling Up

**Shared memory architecture** is a single computer with multiple CPUs, each with their own cache and memory. The CPUs communicate via a shared memory bus. Prices to double power of machine quickly become prohibitive, and the shared memory bus becomes a bottleneck anyways.

**Shared Disk Architecture** is a multi machine setup with each machine having its own CPU and memory, but all machines share a disk over the network. This is a bit better, but the disk becomes a bottleneck.


### Scaling Out

**Shared Nothing Architecture** is a multi machine setup with each machine having its own CPU, memory, and disk. This is the most scalable, but it requires a lot of coordination between machines. Each machine (or VM) is a **node**, and each node is completely independent. Inter-node communication is done over the network through software. 

**For the remainder of this part (Part 2), we will be focusing on shared nothing architectures.**