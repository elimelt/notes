---
title: Clocks
category: Distributed Systems
tags:
  - clocks
  - distributed-systems
  - logical-clocks
  - vector-clocks
  - causality
date: 2024-04-14
updated: 2026-07-30
status: evergreen
description: Why physical clocks cannot order events in a distributed system, and how logical and vector clocks order events using causality instead.
sources:
  - title: "Time, Clocks, and the Ordering of Events in a Distributed System (Lamport, 1978)"
    url: https://lamport.azurewebsites.net/pubs/time-clocks.pdf
    type: paper
  - title: "Exploiting a Natural Network Effect for Scalable, Fine-grained Clock Synchronization (Huygens, NSDI 2018)"
    url: https://www.usenix.org/conference/nsdi18/presentation/geng
    type: paper
---

## Purpose

This note explains why you cannot rely on physical clocks to order events across machines, and how logical clocks and vector clocks recover a useful ordering from causality alone.

## Physical clocks

Quartz clocks in commodity machines drift apart, on the order of 30 ppm, largely because oscillator frequency is temperature sensitive. More accurate clocks (atomic, GPS-disciplined) exist but are expensive, so at best a few machines in a datacenter have one.

The deeper problem is that clocks are never perfectly synchronized and message delay is unpredictable. Network latency has a lower bound but no useful upper bound, so a timestamp from another machine tells you less than it appears to.

A practical approach is NTP-style synchronization: query a set of time servers and combine the readings, for example by taking the minimum or an outlier-trimmed average. This gets you to roughly 50 microseconds of skew on a LAN.

[Huygens](https://www.usenix.org/conference/nsdi18/presentation/geng) pushed this much further. Its main techniques:

- Timestamp packets in the NIC to avoid OS scheduling noise
- Keep only evenly spaced probe packets in the sample, a heuristic for no queuing delay
- Estimate relative clock phase and drift between pairs of machines
- Feed pairwise estimates into a network-wide correction (the paper calls this network effect estimation)

Huygens achieves clock skew under about 50 ns 99% of the time. That sounds excellent, and it is fine when time is only a hint. It is still not good enough for correctness. At Google's scale, a billion RPCs per second with a 1% chance of exceeding the 50 ns bound means about 10 million RPCs every second whose timestamps you cannot trust to that precision. Ordering by physical timestamp will be wrong often enough to matter.

## Virtual clocks

Since physical time cannot be trusted, the goal shifts. Design the system so the ordering of events that can run concurrently does not matter, and the ordering of events that must be sequential is enforced on every possible execution.

Virtual (logical) clocks are a framework for reasoning about event order with no assumptions about clock skew or message delay. They respect causality and rely only on local information.

### Happens before

Event $a$ **happens before** event $b$ if any of these hold:

1. $a$ occurs earlier than $b$ in the same process
2. $a$ is the sending of a message and $b$ is the receipt of that message
3. $a$ happens before some $c$ and $c$ happens before $b$ (transitivity)

This relation is a **partial order**. The definition comes from [Lamport's 1978 paper](https://lamport.azurewebsites.net/pubs/time-clocks.pdf).

### Happens concurrently

Events $a$ and $b$ are concurrent if neither happens before the other. This is exactly the case where a correct system must not depend on their order.

### Logical clock implementation

- Keep a local counter $T$, incremented on every local event.
- Include the current $T$ as a timestamp $T_m$ on every message sent.
- On receiving a message, set $T = \max(T, T_m) + 1$.

This guarantees that if $a$ happens before $b$ then $T(a) < T(b)$. The converse fails: $T(a) < T(b)$ does not imply $a$ happened before $b$, since two concurrent events can get any pair of timestamps.

### Vector clocks

Vector clocks strengthen this to a two-way correspondence: $T(a) < T(b) \leftrightarrow a$ happens before $b$, where a vector $T(a)$ is less than $T(b)$ when every entry of $T(a)$ is $\le$ the corresponding entry of $T(b)$ and at least one entry is strictly smaller. If neither vector is less than the other, the events are concurrent. This precise representation of causal relationships is what eventually consistent and causally consistent systems build on, and the same idea shows up in Git and in Amazon's [[distributed-systems/dynamo-db|Dynamo]].

The algorithm, for a system of $n$ nodes, keeps a vector `C` of length $n$ per node:

- On node `i`, increment `C[i]` on each local event
- When node `i` sends a message, it attaches its vector `C_m`
- On receipt of a message with vector `C_m` at node `i`:
  - increment `C[i]`
  - for each `j != i`, set `C[j] = max(C[j], C_m[j])`

```java
public class VectorClock {
  private final int[] clock;
  private final int id;

  public VectorClock(int id, int n) {
    this.id = id;
    this.clock = new int[n];
  }

  // Call on every local event, including sends.
  public void tick() {
    clock[id]++;
  }

  // Call on receipt of a message carrying the sender's vector.
  public void receive(int[] senderClock) {
    clock[id]++;
    for (int j = 0; j < clock.length; j++)
      if (j != id)
        clock[j] = Math.max(clock[j], senderClock[j]);
  }

  // Returns true iff this clock's event happened before other's.
  public boolean happenedBefore(VectorClock other) {
    boolean strictlyLess = false;
    for (int j = 0; j < clock.length; j++) {
      if (clock[j] > other.clock[j]) return false;
      if (clock[j] < other.clock[j]) strictlyLess = true;
    }
    return strictlyLess;
  }
}
```

Two events are concurrent exactly when `a.happenedBefore(b)` and `b.happenedBefore(a)` are both false.

## Related notes

- [[distributed-systems/ordering-events-in-distributed-systems|ordering distributed events]]
- [[distributed-systems/consistent-global-state|consistent global state]]
