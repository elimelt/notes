---
title: Networks
category: Networks
tags:
  - networking
  - transport
  - routing
  - physical layer
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Overview of the networking notes, organized by layer from physical links up through application protocols.
---

## Purpose

The networking notes already have a clean internal progression by layer, so this page is the top-level map. Start with [[systems/networks/0-foundation/1-network-components-and-protocols|network components and protocols]] and [[systems/networks/0-foundation/3-performance|network performance]]. Then read downward through the stack: physical media, direct links, the network layer, transport, and application protocols.

Several notes are useful even outside a networking course. [[systems/networks/0-foundation/information-theory|Information theory]] explains the capacity bound behind the physical layer. [[systems/networks/4-transport/TCP|TCP]] and [[systems/networks/4-transport/ACK-clocking|ACK clocking]] are useful anywhere queues and feedback loops show up.

## Layers

- Foundations: [[systems/networks/0-foundation/1-network-components-and-protocols|components and protocols]], [[systems/networks/0-foundation/3-performance|performance]], [[systems/networks/0-foundation/information-theory|information theory]]
- Physical and link: [[systems/networks/1-physical/media|media]], [[systems/networks/1-physical/coding-and-modulation|coding and modulation]], [[systems/networks/2-direct-links/framing|framing]], [[systems/networks/2-direct-links/retransmission|retransmission]]
- Network layer: [[systems/networks/3-network/internetworking|internetworking]], [[systems/networks/3-network/routing|routing]], [[systems/networks/3-network/BGP|BGP]]
- Transport and applications: [[systems/networks/4-transport/TCP|TCP]], [[systems/networks/4-transport/UDP|UDP]], [[systems/networks/5-application/HTTP|HTTP]], [[systems/networks/5-application/DNS|DNS]]
