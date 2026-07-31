---
title: "Networking Services: Store-and-Forward Packet Switching and Datagrams vs. Virtual Circuits"
category: Networks
tags:
  - networks
  - packet-switching
  - datagrams
  - virtual-circuits
  - forwarding
date: 2024-02-16
updated: 2026-07-30
status: evergreen
description: The two service models a packet-switched network can offer, connectionless datagrams and connection-oriented virtual circuits, and the tradeoffs between them.
sources:
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Pin down what service the network layer offers to the layers above it. Both models below run on store-and-forward packet switching, and the choice between them shapes router state, addressing, and how failures look. See [[networks/3-network/motivation|motivation behind the network layer]] for why the network layer exists at all.

## Store-and-forward packet switching

A router receives a complete packet, stores it temporarily if necessary, and then forwards it toward the next hop. Links are shared over time by statistical multiplexing. Each switching element has internal buffering to absorb contention, typically a FIFO queue, and when the buffer fills, packets get dropped.

## Datagrams

Datagrams are a connectionless service. Each packet is independent, carries the full destination address, and can take a different route to the destination, like postal letters. A router forwards a datagram by looking up its destination address in a forwarding table that maps destinations to next hops, and the entries change over time as the network topology changes. Consecutive packets to the same destination may follow different paths. This is the model IP uses, and it dominates the internet (see [[networks/3-network/internetworking|internetworking]]).

## Virtual circuits

Virtual circuits are a connection-oriented service. The network sets up a path between source and destination before any data flows, like a phone call. Every packet follows that path and carries a short connection ID instead of a full address. Routers hold per-connection state. The internet mostly doesn't work this way, but ATM and Frame Relay do.

## Tradeoffs

| Issue | Datagram | Virtual Circuit |
|-------|----------|-----------------|
| Setup phase | Not needed | Required |
| Router state | Per destination | Per connection |
| Addresses | Packet carries full destination address | Short connection ID as label |
| Routing | Per packet | Per circuit |
| Failures | Easy to mask | Hard to mask |
| QoS | Hard to provide | Easier to provide |

The failure row is worth unpacking. When a link dies under a datagram service, routing updates the forwarding tables and later packets take another path. Under a virtual circuit service, every circuit through the dead link breaks and has to be set up again. Per-connection state is also what makes QoS easier for circuits, since the network can reserve resources per connection at setup time.

## Related notes

- [[networks/3-network/motivation|motivation behind the network layer]]
- [[networks/3-network/internetworking|internetworking]]
