---
title: Sliding Window Ack Clock
category: Networks
tags: sliding window, ack clocking, tcp, network congestion control
description: Covers the implementation of a sliding window-based acknowledgment (ACK) clocking mechanism for network congestion control. Discusses the problem at the receiver where the receiver's ability to process incoming data can become a bottleneck, leading to buffer buildup and reduced throughput. Describes the sliding window ACK clock approach as a solution to this issue, which aims to pace the transmission of data to match the receiver's processing capacity.
---

# ACK Clocking


## Sliding Window Ack CLock

Each in-order ACK advances the sliding window and lets a new segment enter the network. This prevents queuing buildups at slow links, and thus congestion. Segments are buffered and spread out on slow links.

- Helps run with low levels of loss and delay
- The network smooths out bursts of data segments
- ACK clock transfers smooth timing back to sender
- Subsequent data segments are not sent in burts so they don't queue up in the network.

TCP uses sliding window, controlling the number of segments in the network. It ensures that only small bursts of segments are sent to keep traffic smooth.

## Problem at the Receiver

Sliding window has pipelining to keep network busy, but what if the receiver is overloaded?

Consider receiver with $w$ buffers. Application *should* `recv` to accept packets, but if it didn't, then