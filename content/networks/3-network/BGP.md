---
title: Border Gateway Protocol (BGP)
category: Networks
tags:
  - networks
  - bgp
  - routing
  - autonomous-systems
  - policy-routing
date: 2024-02-23
updated: 2026-07-30
status: evergreen
description: How BGP routes traffic between autonomous systems, covering AS types, the path vector mechanism, business relationships between ASes, and the export rules those relationships imply.
sources:
  - title: "RFC 4271: A Border Gateway Protocol 4 (BGP-4)"
    url: https://datatracker.ietf.org/doc/html/rfc4271
    type: rfc
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Explain how routing works between autonomous systems, where the deciding factor is policy rather than link cost. Covers the kinds of ASes, how BGP advertises paths, and which routes an AS is willing to share with whom.

## Core idea

You can view the internet as a graph of interconnected Autonomous Systems (ASes). Each AS acts on its own and handles routing within itself. The routers inside an AS connect to each other over high-speed links and reach other ASes through border routers. See [[networks/3-network/global-internet|the global Internet]] for why the internet is organized this way.

Traffic falls into two kinds from an AS's point of view. Transit traffic passes through the AS on its way somewhere else. Local traffic is destined for a device inside the AS. That distinction gives three AS types:

- **Stub AS**: has one connection to another AS and carries no transit traffic.
- **Multihomed AS**: connects to more than one other AS but still refuses transit traffic.
- **Transit AS**: connects to more than one other AS and carries both local and transit traffic.

BGP ([RFC 4271](https://datatracker.ietf.org/doc/html/rfc4271)) is the protocol that routes traffic between ASes. Intra-domain protocols like OSPF and RIP optimize a cost metric. BGP has no cost metric to optimize, since cost is not a well-defined concept across independently run ASes. It advertises reachability and lets each AS choose among reachable paths according to its own policies.

## Mechanism

Each AS has one or more border routers that handle ingress and egress traffic. It also needs at least one BGP speaker that exchanges routing information with other ASes. Border routers and BGP speakers are often the same device, but they don't have to be.

BGP is a path vector protocol. An advertisement carries the entire path to a destination as a sequence of ASes rather than a single next hop. An AS that sees itself in an advertised path knows accepting it would form a loop, and the full path gives each AS enough information to apply policy to the whole route a packet would take.

A BGP speaker is never obligated to advertise a given path. When it does advertise, it advertises the path it considers best under its own policies. It can retract an earlier advertisement with a withdraw route message.

BGP runs over TCP and uses keep-alives. If a speaker stops hearing keep-alives from a neighbor within the configured window, it treats the neighbor as down and stops advertising the routes it learned from that neighbor.

## Relationships between ASes

An AS pairs with its neighbors in one of two arrangements, and the arrangement drives what gets advertised:

- **Provider and customer**: the customer pays the provider to carry its traffic. The provider advertises all routes it knows to the customer, and advertises the customer's routes to everyone, since carrying traffic to the customer is what it gets paid for.
- **Customer toward its provider**: the customer advertises its own prefixes and any routes learned from its own customers. It advertises routes learned from the provider down to its customers. It never advertises routes learned from one provider to another provider, because that would make it carry transit traffic for free.
- **Peer and peer**: two ASes exchange traffic between their respective customers without money changing hands. Each peer advertises customer routes to the other and advertises the peer's routes to its own customers. Routes learned from a peer never go to a provider or to another peer.

## Route selection

When an AS knows several paths to the same destination, it prefers a path through a customer over a path through a peer, and a path through a peer over a path through a provider. Customer paths earn money, peer paths are free, and provider paths cost money. Among paths of the same class it picks the one with the fewest AS hops.

The same economics explain the export rules above. Customer paths get advertised to customers, peers, and providers, since more traffic toward a customer means more revenue. Peer paths and provider paths get advertised only to customers, because letting a peer or another provider use them brings in nothing and can cost money.

## Related notes

- [[networks/3-network/routing|routing]]
- [[networks/3-network/global-internet|the global Internet]]
