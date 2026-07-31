---
title: The Global Internet
aliases:
  - networks/3-network/global-internet
category: Networks
tags:
  - networks
  - routing
  - autonomous-systems
  - inter-domain-routing
date: 2024-02-25
updated: 2026-07-30
status: draft
description: Why intra-domain routing protocols can't cover the whole internet, and how autonomous systems and inter-domain routing let routing scale to billions of devices.
sources:
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Explain how routing scales from a single network to the whole internet. Protocols like RIP and OSPF require every router to know about every network they can reach, and no router can hold a complete list of all the networks in the internet. The fix is hierarchy.

## Structure of the internet

The modern internet is mainly composed of end-user sites and service providers. An end-user site is a collection of devices reaching the internet through a single IP address (NAT in home networks) or through switched ethernet in an enterprise LAN. Service providers build the infrastructure and route traffic between end-user sites. A provider runs many high-performance routers in metro areas, connected to each other and to other providers over high-speed links.

## Routing areas

OSPF already divides a network into areas to shrink routing tables (see [[systems/networks/3-network/routing|routing]]). The global internet applies the same move at a much larger scale. It is divided into routing domains called **Autonomous Systems** (ASes). An AS is a collection of routers and networks under the control of a single organization. Each AS picks its own routing protocol and handles routing within itself. Routers inside an AS connect to each other over high-speed links and reach other ASes through border routers.

## Inter-domain routing

Routing between ASes is a separate problem from routing within one, because ASes are independently managed and don't share a cost metric. The interior routers handle traffic within the AS, the border routers handle traffic between ASes, and the protocol the border routers speak is [[systems/networks/3-network/BGP|BGP]].

## Related notes

- [[systems/networks/3-network/BGP|BGP]]
- [[systems/networks/3-network/routing|routing]]
