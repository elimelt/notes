---
title: Transport Layer Overview
aliases:
  - networks/4-transport/transport-overview
category: Networks
tags:
  - transport-layer
  - TCP
  - UDP
  - datagrams
  - bytestreams
date: 2024-02-25
updated: 2026-07-30
status: evergreen
description: What the transport layer provides on top of the network layer, and the two service models it exposes, datagrams via UDP and bytestreams via TCP.
sources:
  - title: "CSE 461: Computer Networks, University of Washington"
    url: https://courses.cs.washington.edu/courses/cse461/
    type: lecture
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Orient the transport layer within the stack and name its two service models before the per-protocol notes go into detail.

## Core idea

The network layer moves packets between hosts. The transport layer builds on that to provide end-to-end connectivity between application processes across the network. In terms of encapsulation, application data rides in segments, segments ride in packets, and packets ride in frames.

The layer exposes two service models. Messages, also called datagrams, are discrete units of data delivered independently, and UDP provides them with no delivery guarantees. Bytestreams are continuous ordered streams of bytes, and TCP provides them with reliability, flow control, and congestion control layered on top of the network's best-effort delivery.

Which one an application wants depends on whether it needs delivery guarantees more than it needs low overhead. [[systems/networks/4-transport/TCP|TCP]] and [[systems/networks/4-transport/UDP|UDP]] cover the two protocols.

## Related notes

- [[systems/networks/4-transport/TCP|TCP]]
- [[systems/networks/4-transport/UDP|UDP]]
- [[systems/networks/4-transport/flow-control|flow control]]
- [[systems/networks/0-foundation/3-performance|network performance]]
