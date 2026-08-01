---
title: Design Philosophy of DARPA Internet Protocols
aliases:
  - systems-research/internet-design-philosophy
category: Systems Research
tags:
  - internet
  - design
  - systems
  - networking
  - paper-notes
  - packet-switching
  - datagrams
date: 2025-01-14
updated: 2026-07-30
status: evergreen
description: Review notes on Clark's paper explaining the goals behind the DARPA internet protocols, covering packet switching, datagrams, the thin waist, and fate sharing.
sources:
  - title: The Design Philosophy of the DARPA Internet Protocols (SIGCOMM 1988)
    url: http://ccr.sigcomm.org/archive/1995/jan95/ccr-9501-clark.pdf
    type: paper
---

## Purpose

Reading notes on Clark's retrospective about why the internet protocols look the way they do. The note works through the goal hierarchy, the datagram building block, the thin waist, and fate sharing.

## Citation

- [The Design Philosophy of the DARPA Internet Protocols](http://ccr.sigcomm.org/archive/1995/jan95/ccr-9501-clark.pdf), David D. Clark.

## Problem

TCP/IP's structure looks arbitrary unless you know the goals it was designed against. Clark writes down those goals, in priority order, and shows how each design decision falls out of them. The ordering matters as much as the list; a network built for commercial operation instead of military survivability would have made different tradeoffs from the same catalog.

## Main idea

The fundamental goal was an effective technique for multiplexed utilization of interconnected networks. Both words carry weight.

Multiplexing means many communicating parties share a channel. Circuit switching dedicates a channel per pair of parties, which gives predictable performance because resources are reserved, but wastes capacity and scales badly; connecting $N$ parties pairwise needs $N(N-1)/2$ channels. Packet switching lets packets from many parties share one channel. Utilization improves, and in exchange packets can be lost, delayed, or reordered. Packet switching also exploits redundant paths between hosts. A transport-layer connection survives as long as some path exists, whatever the topology does underneath.

Interconnection means joining heterogeneous networks, each with its own protocols and addressing, into one internet that moves data between them.

The secondary goals, in the paper's order of importance:

- Continue despite failure
- Support multiple types of communication service
- Accommodate a variety of networks
- Distributed management of resources, since centralized control would bottleneck and each network should manage its own
- Cost effectiveness
- Easy host attachment, without requiring changes to the network
- Accountability, so hosts can identify themselves and quality of service can be enforced

## Datagrams

The [[systems/networks/3-network/networking-services|datagram]] is the key building block. It is a connectionless service with no state established ahead of time, and each packet is independent. UDP is the application-level interface to the internet's datagram service, and other protocols build on top of it conceptually; TCP adds connections, reliability, and in-order delivery, while UDP itself stays unreliable and unordered, with no QoS guarantees from the lower level.

## Supporting a variety of networks

The "thin waist" of the hourglass model. IP at the network layer gives all networks a common interface, and TCP/UDP at the transport layer give all applications one. The abstraction hides the details of the lower layers, so anything can happen down there while applications stay unaware.

The same hiding causes problems. Applications can't use hints from the lower level for optimization, and the workarounds (ECN, kernel-bypass systems like DPDK, with parallels in storage like SPDK and direct access) exist precisely to punch through the abstraction. And the IP interface itself can't evolve without changing everything above it.

## Fate sharing

Move connection state to the endpoints for survivability. The state shares fate with the endpoint that cares about it, so if a network element fails, the endpoints still hold everything needed to reestablish the connection. This is the [[systems/research/end-to-end-arguments-in-sys-design|end-to-end argument]] applied to network resilience.

> [!tip] Fate sharing in one line
> Keep connection state at the endpoint that cares about it, so a failure can only destroy state belonging to the party that failed.

## Strengths and weaknesses

The datagram is a simple idea that scales and distributes naturally, and the strongest evidence for the design is that it works at internet scale. On the other side, the narrow IP interface hurts innovation at the IP level, and hiding lower layers can hurt efficiency.

## Further reading

- [Principles of Computer System Design](https://ocw.mit.edu/courses/res-6-004-principles-of-computer-system-design-an-introduction-spring-2009/pages/online-textbook/)

## Sources

- [The Design Philosophy of the DARPA Internet Protocols](http://ccr.sigcomm.org/archive/1995/jan95/ccr-9501-clark.pdf)

## Related notes

- [[systems/research/end-to-end-arguments-in-sys-design|End-to-End Arguments in System Design]]
- [[systems/research/development-of-the-dns|Development of the Domain Name System]]
- [[systems/networks/3-network/networking-services|Networking Services]]
- [[systems/networks/0-foundation/1-network-components-and-protocols|Network Components and Protocols]]
- [[systems/networks/2-direct-links/multiple-access|Multiple Access]]
- [[systems/networks/5-application/overview|Application Layer Overview]]
- [[systems/networks/3-network/motivation|Motivation behind the Network Layer]]
