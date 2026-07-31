---
title: Motivation behind the Network Layer
aliases:
  - networks/3-network/motivation
category: Networks
tags:
  - networks
  - network-layer
  - link-layer
  - routing
  - forwarding
  - icmp
  - bgp
date: 2024-02-16
updated: 2026-07-30
status: evergreen
description: Why the link layer alone can't build the internet, what the network layer adds, and the difference between routing and forwarding. Ends with a map of the other network layer notes.
sources:
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Explain why the network layer exists at all. The link layer with packet forwarding can already build a network, so this note pins down what breaks when you try to build the internet out of it, and what the network layer does about each problem.

## Shortcomings of the link layer

- **No global addressing**: link layer addresses only mean something on the local network. Reaching hosts on other networks needs an address scheme that spans networks.
- **Doesn't scale**: no host can maintain a routing table with an entry for every other host on the internet.
- **Only one technology**: link layer technologies are not interoperable with each other. Ethernet and 802.11 frames don't mix without something above them.
- **Limited traffic control**: the link layer has no mechanism for handling congestion, routing around failures, or controlling the bandwidth different applications use.

## Network layer approach

- **Scaling**: hierarchical addressing in the form of prefixes, so routers track networks instead of hosts.
- **Heterogeneity**: IP as a common protocol that any link layer technology can carry.
- **Bandwidth control**: congestion control and lowest-cost routing manage traffic, and the layer leaves room for quality of service (QoS).

## Routing vs. forwarding

**Routing** is the process of deciding which paths traffic should take. It happens on a global scale and involves routers exchanging information.

**Forwarding** is the process of actually sending a packet from one node to the next, one local table lookup per packet.

## Where the details live

- Network service models, datagrams and virtual circuits: [[systems/networks/3-network/networking-services|networking services]]
- IP, addressing, and forwarding by longest prefix match: [[systems/networks/3-network/internetworking|internetworking]]
- The helper protocols: [[systems/networks/3-network/ARP|ARP]] and [[systems/networks/3-network/DHCP|DHCP]]
- Errors and diagnostics: [[systems/networks/3-network/ICMP|ICMP]]
- Routing algorithms: [[systems/networks/3-network/routing|routing]]
- Scaling routing to the world: [[systems/networks/3-network/global-internet|the global Internet]] and [[systems/networks/3-network/BGP|BGP]]
