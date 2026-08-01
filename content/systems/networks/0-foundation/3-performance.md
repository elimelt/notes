---
title: Performance
aliases:
  - networks/0-foundation/3-performance
category: Networks
tags:
  - bandwidth
  - throughput
  - latency
  - delay
date: 2024-01-12
updated: 2026-07-30
status: incomplete
description: Stub on network performance metrics. Defines bandwidth and latency, then points to the notes that actually work the material.
---

This note was meant to cover how network performance is measured and never got past the first definition. The two headline metrics are **bandwidth** (or throughput), the number of bits per second a link or path can move, and **latency** (or delay), the time a message takes to cross it.

> [!abstract] Bandwidth vs. latency
> Bandwidth is how wide the pipe is, latency is how long it is, and the two are independent. A satellite link can be high-bandwidth and high-latency at once, and a short serial cable low-bandwidth and low-latency. More parallelism (more channels, wider signals) buys bandwidth, but only a shorter path or a faster medium cuts propagation latency.

Until this gets written, [[systems/networks/0-foundation/2-physical-layer|the physical layer]] works a latency example with the transmission and propagation delay formulas, [[systems/networks/1-physical/coding-and-modulation|coding and modulation]] covers the bandwidth-delay product, and [[systems/networks/0-foundation/information-theory|information theory]] covers the hard limits on link capacity.
