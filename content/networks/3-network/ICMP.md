---
title: Internet Control Message Protocol (ICMP)
category: Networks
tags:
  - networks
  - icmp
  - ping
  - traceroute
  - ttl
date: 2024-02-25
updated: 2026-07-30
status: evergreen
description: What ICMP does at the network layer, covering error reporting, ICMP redirects, and how traceroute and ping are built on top of it.
sources:
  - title: "RFC 792: Internet Control Message Protocol"
    url: https://datatracker.ietf.org/doc/html/rfc792
    type: rfc
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Explain what ICMP is for and how `ping` and `traceroute` use it. IP itself gives no feedback when a packet dies in the network, so a companion protocol carries errors and control messages back to the sender.

## Core idea

ICMP ([RFC 792](https://datatracker.ietf.org/doc/html/rfc792)) is a network layer protocol for reporting errors and exchanging control messages. When a router drops a datagram or a TTL expires (see [[networks/3-network/internetworking|internetworking]] for the TTL field in the IP header), an ICMP message tells the source what happened.

One useful control message is the **ICMP Redirect**, which tells a host that a better route exists for a given destination. A host that receives one updates its routing table to use the new route.

## Traceroute

`traceroute` sends packets with increasing TTLs and listens for ICMP Time Exceeded messages. Each router along the path decrements the TTL, and the router where it hits 0 sends a Time Exceeded message back to the source. That message carries the router's IP address as its source, so a packet with TTL $n$ exposes the $n$-th router on the path. `traceroute` records the round-trip time to each router itself, prints the router's address and the timing, and keeps increasing the TTL until packets reach the destination.

## Ping

`ping` sends ICMP Echo Request messages to the destination and listens for ICMP Echo Reply messages. A host that receives an Echo Request answers with an Echo Reply, which gives the sender a connectivity check and a round-trip time. It repeats until the user stops the command.

## Related notes

- [[networks/3-network/internetworking|internetworking]]
- [[networks/3-network/routing|routing]]
