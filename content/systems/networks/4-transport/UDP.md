---
title: UDP
aliases:
  - networks/4-transport/UDP
category: Networks
tags:
  - udp
  - transport-layer
  - datagrams
date: 2024-02-25
updated: 2026-07-30
status: draft
description: What UDP provides and what it leaves out, the datagram header, and when an application should pick it over TCP.
sources:
  - title: "RFC 768: User Datagram Protocol"
    url: https://datatracker.ietf.org/doc/html/rfc768
    type: spec
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Record what UDP actually does, which is very little on purpose, and when that is the right choice.

## Core idea

UDP ([RFC 768](https://datatracker.ietf.org/doc/html/rfc768)) delivers discrete messages, called datagrams, between application processes. It adds process-to-process demultiplexing via ports and an optional checksum on top of the network layer, and nothing else. There is no connection setup, no ordering, no retransmission, no flow control, and no congestion control. A datagram either arrives once, arrives duplicated, or never arrives, and the application deals with it.

The header is 8 bytes with four 16-bit fields.

| Field | Meaning |
| --- | --- |
| Source port | Sending process, so the peer can reply |
| Destination port | Receiving process |
| Length | Header plus data, in bytes |
| Checksum | Integrity check over header and data |

## When to use it

TCP's guarantees cost connection setup latency, retransmission delays, and in-order delivery stalls. Applications that would rather lose a message than wait for it run on UDP. Real-time audio and video and online games fall in this bucket, since a retransmitted frame arrives too late to matter. DNS uses UDP because a full TCP handshake per lookup would dominate the cost of the tiny query, see [[systems/networks/5-application/DNS|DNS]]. Anything needing reliability on UDP has to build it in the application itself.

## Related notes

- [[systems/networks/4-transport/TCP|TCP]]
- [[systems/networks/4-transport/transport-overview|transport layer overview]]
- [[systems/networks/5-application/DNS|DNS]]
