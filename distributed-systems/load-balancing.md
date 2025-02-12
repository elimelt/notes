---
title: Load Balancing
category: distributed-systems
tags: load balancing, distributed systems, paxos, sharding, edge caching, queueing, zipf distribution
description: Explains load balancing strategies and their implications on distributed systems.
---

# Load Balancing

In a load balancing systems, we want the following:

1. Clients all follow the same assignment
2. Load is evenly distributed
3. Adding/removing only moves a few keys
4. Tail latency is minimized
5. Redistributing keys should not overload a single server
6. Workload should be evenly distributed despite key popularity differences

## Scaling Paxos with Sharding

Use Paxos to define the order of a state machine running on a set of servers. For a key value store, we can split the key space into multiple shards, assigning some set of keys to a given shard. The Paxos group that performs this is known as the **shard master**. Then, each shard is a Paxos group that runs the state machine for its subset of keys.

This has the advantage of spreading load across multiple servers, as well as distributing the data.

## Edge Caching

Many things should be cached locally to the users machine. However, for content that is not user specific (like `logo.png`), we can cache it on a single server and redirect all requests for that content to that specific server, effectively load balancing the requests while condensing the cache to use less memory across all servers.

## Queueing

Assuming completely random (Poisson) arrivals and service times, the average number of requests in the system is given by:

$$
R = \frac{S}{1 - U}
$$

Where $R$ is the response time, $S$ is the service time, and $U$ is the utilization of the server. This formula is derived from the M/M/1 queueing model.

The variance of the response time is $\propto \frac{S}{1 - U}$, so as the server utilization approaches 1, the variance of the response time approaches infinity.

In practice, load is bursty and services need to be overprovisioned to handle the spikes in load. This is why the variance of the response time is so important, since tail latencies can be very high if the server is overloaded.

The system can be modeled as a Markov chain with states $0, 1, 2, \ldots, n$. The state $i$ represents the system with $i$ requests in the system. The transition rate from state $i$ to state $i+1$ is $\lambda$ and the transition rate from state $i$ to state $i-1$ is $\mu$.

## Key Popularity

The **Zipf distribution** says that the $k$th most popular item follows some curve $\frac{1}{k^c}$, where $1 \le c \le 2$. This is said to...sort of apply to many things

- Web pages hits/file access frequency
- File sizes
- Word/token frequency
- Friends on a social network

We can cope with popular keys using **power of two choices**. Keys can be hashed to multiple (in this case two, but generalizes to $k$) servers, and requests are forwarded to whichever server is under less load.