---
title: Dynamic Host Configuration Protocol (DHCP)
aliases:
  - networks/3-network/DHCP
category: Networks
tags:
  - networks
  - dhcp
  - udp
  - ip-addressing
date: 2024-02-23
updated: 2026-07-30
status: evergreen
description: How DHCP assigns IP addresses on a network, covering the discover, offer, request, and ack exchange, renewal, and relays for networks without a local server.
sources:
  - title: "RFC 2131: Dynamic Host Configuration Protocol"
    url: https://datatracker.ietf.org/doc/html/rfc2131
    type: rfc
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Explain how a device joining a network gets an IP address without manual configuration. Covers the server, the client, and the relay.

## Core idea

DHCP ([RFC 2131](https://datatracker.ietf.org/doc/html/rfc2131)) assigns IP addresses within a network. A MAC address is burned into the device. An IP address is assigned, and the assignment can move to a different device over time. That flexibility is what lets networks renumber and reuse addresses, and DHCP is the protocol that manages the assignments.

DHCP runs on top of UDP, with the server on port 67 and the client on port 68. It has to work before the client has an address, which is why the exchange starts with broadcast.

## DHCP server

The DHCP server assigns IP addresses on the network. It is typically a router or a server, and it manages a pool of addresses. The exchange when a device joins:

1. The device broadcasts a **DHCP Discover** to the all-ones address, since it doesn't yet know the server's address or its own.
2. The server answers with a **DHCP Offer** containing an IP address it is willing to assign.
3. The device sends a **DHCP Request** for that address.
4. The server confirms with a **DHCP Ack**.

A network can run more than one DHCP server for fault tolerance. If one server fails, a client can get an address from another.

## DHCP client

DHCP clients are built into most devices that connect to a network. Assignments are leases, and a client renews by sending a **DHCP Request** to the server, which confirms the renewal with a **DHCP Ack**.

## DHCP relay

Some networks have no DHCP server of their own. A **DHCP relay** on the local network listens for **DHCP Discover** broadcasts and forwards them to a server on another network. The server's **DHCP Offer** comes back through the relay to the client.

## Related notes

- [[systems/networks/3-network/ARP|ARP]]
- [[systems/networks/3-network/internetworking|internetworking]]
