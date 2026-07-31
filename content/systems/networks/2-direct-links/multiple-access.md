---
title: Multiple Access
aliases:
  - networks/2-direct-links/multiple-access
category: Networks
tags:
  - multiplexing
  - tdm
  - fdm
  - csma
  - aloha
  - binary-exponential-backoff
  - ethernet
date: 2024-02-05
updated: 2026-07-30
status: evergreen
description: How multiple senders share one link. Covers TDM and FDM, centralized versus distributed access control, ALOHA, CSMA/CD, binary exponential backoff with the expected-wait derivation, and classic Ethernet.
sources:
  - title: "Computer Networks: A Systems Approach (Peterson and Davie)"
    url: https://book.systemsapproach.org/
    type: textbook
  - title: UW CSE 461 Computer Networks
    url: https://courses.cs.washington.edu/courses/cse461/
    type: course
---

## Purpose

A link often has more than one sender. This note covers how senders share it, from fixed schedules (TDM, FDM) to distributed random access (ALOHA, CSMA), and how classic Ethernet put the pieces together.

## Multiplexing

**Multiplexing** shares one resource among multiple clients. Network traffic is bursty, so the shared capacity can be much smaller than the sum of the peaks. Two users who each burst at 1 Mbps might share 1.5 Mbps comfortably.

### Time division multiplexing (TDM)

Users take turns on a fixed schedule, often round-robin. Each user sends at a high rate for a short time.

### Frequency division multiplexing (FDM)

Users get different frequency bands and transmit at the same time with minimal interference. Each user sends at a low rate constantly.

### TDM vs. FDM

For a fixed set of users, TDM suits bursty traffic and FDM suits constant traffic. TV and radio use FDM. GSM (2G cellular) uses TDM inside FDM.

## Controlling access

Fixed schedules need someone to set the schedule. There are two classes of access control, centralized and distributed.

### Centralized

A privileged scheduler allocates the resource. Overhead is low and the scheduler can enforce policy like QoS, but it is a single point of failure and a bottleneck at scale. Cellular networks work this way, with the base station scheduling access to the channel.

### Distributed

The participants figure it out among themselves. Distributed access holds up well under low load, sets up easily, and tolerates faults, though scaling it is hard. WiFi and Ethernet work this way.

## Random access protocols

Random access assumes no one is in charge and collisions will happen.

**ALOHA**: send whenever you want. If there's a collision (no ACK), wait a random time and retry. Simple, and wasteful under load. The classic analysis puts pure ALOHA's peak utilization at about 18% of capacity, and slotting time (senders start only on slot boundaries) doubles that to about 36%.

### Carrier sense multiple access (CSMA)

Listen to the channel before sending, and wait if it's busy. Carrier sensing only really works on wired links (see [[systems/networks/2-direct-links/wireless|wireless]] for why it fails over the air). CSMA beats ALOHA, but collisions still happen because a competing transmission takes a propagation delay to become audible. That makes CSMA a good idea only when the bandwidth-delay product is small, so the vulnerable window is short.

#### CSMA/CD (collision detection)

Classic Ethernet adds collision detection. A sender that detects a collision stops immediately and retries after a random wait. The complication is that every node involved in the collision must be able to detect it.

A collision can take up to $2 \cdot D_{\text{propagation}}$ to detect (the signal crosses the wire, collides at the far end, and the interference crosses back). If a sender could finish its frame before that window closes, it would never learn about the collision. So the standard imposes a minimum frame length that takes at least $2 \cdot D_{\text{propagation}}$ to transmit, plus a maximum network length. That is why Ethernet has a 64-byte minimum frame, a 500 m limit for coaxial Ethernet, and a 100 m limit for twisted pair.

#### CSMA persistence

Waiting for the channel to go free and then sending immediately fails, because every queued sender does the same thing and they all collide the moment the channel clears. The design goal instead is that with $N$ queued senders, each sends with probability about $1/N$.

### Binary exponential backoff

Ethernet approximates that probability without knowing $N$ by widening the retry window after each collision. Given a base time quantum $q$, after collision $i$ the sender waits

$$t_i = q \cdot \text{rand}(0, 2^i - 1)$$

```python
Q = 1 # seconds
def send(frame):
    t = 1
    while not send_frame(frame):
        time.sleep(Q * randint(0, t))
        t *= 2
```

The expected wait after the $k$-th collision follows directly. $W_k$ is uniform over $\{0, q, 2q, \dots, (2^k - 1)q\}$, and the mean of a uniform distribution over $0$ to $M$ is $M/2$, so

$$E[W_k] = \frac{q(2^k - 1)}{2}$$

Each collision doubles the expected wait, which backs the senders off fast enough to thin out the contention.

## Ethernet

Classic Ethernet (IEEE 802.3) ran at 10 Mbps over shared coaxial cable and was everywhere in the 80s and 90s. Its multiple access scheme is 1-persistent CSMA/CD with binary exponential backoff. Modern Ethernet is built on [[systems/networks/2-direct-links/switching|switches]], which give each host a point-to-point link and remove the need for CSMA/CD.

### Ethernet frames

- Source and destination addresses identify sender and receiver.
- A CRC-32 checksum detects errors. There is no ACK or retransmission.
- A physical-layer preamble marks the start of the frame.

```plaintext
+----------------+
| Preamble (8B)  |
|                |
+----------------+
| Destination    |
| Address (6B)   |
+----------------+
| Source Address |
| (6B)           |
+----------------+
| Type (2B)      |
+----------------+
| Data (0-1500B) | --->
|                | ---> network layer (IP packet)
|      ...       | --->
+----------------+
| Padding (0-46B)|
+----------------+
| Checksum (4B)  |
+----------------+
```

## Related notes

- [[systems/networks/2-direct-links/wireless|wireless]]
- [[systems/networks/2-direct-links/switching|switching]]
- [[systems/networks/2-direct-links/framing|framing]]
