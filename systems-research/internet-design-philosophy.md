---
title: Design Philosophy of DARPA Internet Protocols
category: Networks
tags: internet, design, systems
description: A summary of the design philosophy of the DARPA internet protocols.
---

# [source](http://ccr.sigcomm.org/archive/1995/jan95/ccr-9501-clark.pdf)

###### Design Philosophy of the DARPA Internet Protocols

---

### What is the Problem?


### Summary

**Fundamental Goal**: develop effective technique for **multiplexed** utilization of **interconnected** networks.

**Multiplexing**: single channel used by many communicating parties
- Circuit-switching: dedicated channel for each pair of communicating parties, i.e. point-to-point comms
    - Predictable performance because resources are "reserved" for each connection
    - Inefficient use of resources, number of connections limited by number of channels. With `N` parties, `N(N-1)/2` channels needed.
- Packet-switching: packets from many parties share a single channel
    - More efficient use of resources, but performance less predictable
    - Packets can be lost, delayed, or delivered out of order

At a high level, packet switching needs to happen in order to take advantage of the redundancy in paths between any two hosts. Connection at the transport layer can be established and maintained regardless of the underlying network topology, so long as a path exists between the two hosts.

Another fundamental goal: connecting heterogeneous networks. The internet is a network of many different types of networks, each with its own protocols and addressing schemes. The internet protocols need to be able to connect these networks together/transmit data between them.

Secondary Goals:

- Continue despite failure
- Multiple types of communication
- Variety of networks
- Distributed management of resources
    - Any centralized control would be a bottleneck
    - Each network should be able to manage its own resources
- Cost effective
- Host attachment
    - Hosts should be able to connect to the network without requiring changes to the network
- Accountability
    - Hosts should be able to identify themselves to the network
    - Quality of service should be able to be enforced


#### Datagrams

- Connectionless service
    - no state established ahead of time
- Key building block for switching
- UDP is app-level interface to datagram service of the internet
    - building block for other protocols (TCP)
- Each packet is independent

#### TCP vs. UDP

- TCP: connection-oriented, reliable, in-order delivery
- UDP: connectionless, unreliable, unordered delivery (loss is OK)
    - No QoS guarantees in lower-level

#### Supporting Variety of Networks

"Thin waist" of the internet/hourglass model: IP at the network layer, TCP/UDP at the transport layer.

- IP: provides a common interface for all networks
- TCP/UDP: provides a common interface for all applications

Abstraction hides details of lower layer, allowing whatever you want to happen at the lower level while the application remains unaware.

Unfortunately, can also lead to some problems
- Can't use hints directly from lower level for optimizations
    - Workarounds: ECN, dpdk
    - Parallels in storage, e.g. direct access, spdk
- Can't evolve interface of IP without changing everything above it

#### Fate Sharing

Move state to endpoints for **survivability**. If a network fails, the endpoints can reestablish the connection.

### Strengths

- Simple idea of datagrams
- Scalable/distributed
- It works!

### Weaknesses

- Narrow IP interface hurts innovation at IP level
- Hiding secrets can hurt efficiency


### Further Reading

- [Principles of Computer System Design](https://ocw.mit.edu/courses/res-6-004-principles-of-computer-system-design-an-introduction-spring-2009/pages/online-textbook/)
