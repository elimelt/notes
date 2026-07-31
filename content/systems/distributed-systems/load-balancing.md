---
title: Load Balancing
aliases:
  - distributed-systems/load-balancing
category: Distributed Systems
tags:
  - load-balancing
  - distributed-systems
  - sharding
  - queueing-theory
  - zipf
date: 2024-05-06
updated: 2026-07-30
status: evergreen
description: What good load balancing has to achieve, sharded Paxos and edge caching as strategies, and the queueing and key-popularity math that explains tail latency.
sources:
  - title: "The Power of Two Choices in Randomized Load Balancing (Mitzenmacher, 2001)"
    url: https://www.eecs.harvard.edu/~michaelm/postscripts/tpds2001.pdf
    type: paper
---

## Purpose

This note lists what a load balancing scheme has to achieve, then covers the strategies I've studied for getting there and the queueing math that explains why utilization drives tail latency.

## What we want

1. Clients all follow the same assignment
2. Load is evenly distributed
3. Adding or removing a server only moves a few keys
4. Tail latency is minimized
5. Redistributing keys should not overload a single server
6. Load stays even despite differences in key popularity

## Scaling Paxos with sharding

This design combines [[systems/distributed-systems/paxos-intro|Paxos consensus]] with [[systems/distributed-systems/sharding|sharding]].

Use Paxos to define the order of a state machine running on a set of servers. For a key-value store, split the key space into shards, assigning a set of keys to each shard. A dedicated Paxos group called the **shard master** owns the assignment of keys to shards. Each shard is then its own Paxos group running the state machine for its subset of keys.

This spreads request load across multiple servers and distributes the data along with it.

## Edge caching

Content local to a user should be cached on the user's machine. For content that is popular and not user specific, like `logo.png`, cache it on one designated server and redirect all requests for that content there. Requests spread across servers by content, and each piece of content occupies cache memory on only one server instead of every server.

## Queueing

Assume completely random (Poisson) arrivals and exponentially distributed service times, the M/M/1 queueing model. The mean response time is

$$
R = \frac{S}{1 - U}
$$

where $R$ is response time, $S$ is service time, and $U$ is server utilization. In an M/M/1 queue the response time is exponentially distributed, so its standard deviation equals its mean, $\frac{S}{1-U}$. As utilization approaches 1, both the mean and the spread of response times blow up, which is exactly where tail latency comes from.

The system can be modeled as a Markov chain with states $0, 1, 2, \ldots$, where state $i$ means $i$ requests are in the system. The transition rate from state $i$ to $i+1$ is the arrival rate $\lambda$, and from $i$ to $i-1$ is the service rate $\mu$. The formulas above fall out of solving this chain's steady state.

In practice load is bursty rather than Poisson, so services get overprovisioned to absorb spikes. The variance result explains why that overprovisioning is worth paying for. Run a server near full utilization and its tail latency becomes enormous.

## Key popularity

The **Zipf distribution** says the $k$th most popular item has frequency proportional to $\frac{1}{k^c}$ for some $1 \le c \le 2$. It roughly fits a lot of observed workloads, including web page hits, file access frequency, file sizes, word frequency, and friend counts on social networks. The consequence for load balancing is that hashing keys uniformly across servers still leaves whichever server holds the hottest keys overloaded.

The **power of two choices** copes with popular keys: hash each key to two (or in general $k$) candidate servers, and forward each request to whichever candidate is under less load. [Mitzenmacher's analysis](https://www.eecs.harvard.edu/~michaelm/postscripts/tpds2001.pdf) shows that moving from one choice to two gives an exponential improvement in the maximum load, while more than two choices adds little.

## Related notes

- [[systems/distributed-systems/scaling-web-services|scaling web services]]
- [[systems/distributed-systems/sharding|sharding]]
