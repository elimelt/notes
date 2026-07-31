---
title: Sliding Window Ack Clock
aliases:
  - networks/4-transport/ACK-clocking
category: Networks
tags:
  - sliding-window
  - ack-clocking
  - tcp
  - congestion-control
date: 2024-02-25
updated: 2026-07-30
status: evergreen
description: How a sliding window sender uses returning ACKs to pace new segments into the network, and why that pacing does not protect an overloaded receiver.
sources:
  - title: "CSE 461: Computer Networks, University of Washington"
    url: https://courses.cs.washington.edu/courses/cse461/
    type: lecture
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Explain the ACK clock, the mechanism by which a sliding window sender ends up transmitting at the pace of the slowest link on the path. Also cover the case the ACK clock does nothing about, a receiver that cannot keep up.

## Core idea

Each in-order ACK advances the sliding window and lets one new segment enter the network. New data goes out exactly as fast as ACKs come back, and ACKs come back at the rate the bottleneck link can deliver data. The sender is clocked by the network itself.

## Intuition

Say the sender sits on a fast link and the path crosses a slow link downstream. The first burst of segments arrives at the slow link faster than it can forward them, so they queue there and leave spaced out in time. The receiver generates ACKs with that same spacing, and the spacing survives the trip back because ACKs are small. When those ACKs arrive, the sender releases new segments one per ACK, already spread out to match the bottleneck rate. The network smooths the first burst once, and the ACK clock carries that smooth timing back to the sender for the rest of the transfer.

This keeps queues at the slow link small, which keeps loss and queueing delay low. TCP depends on this behavior. The window bounds how many segments are in the network at once, and the ACK clock stops later segments from arriving in bursts that would refill the queue.

## Problem at the receiver

The ACK clock matches the sender to the network path. It says nothing about whether the receiving application actually consumes the data. Consider a receiver with $w$ buffers. The application should call `recv` to drain them, but nothing forces it to. If it stops, the buffers fill with segments the network delivered perfectly well, and every segment after that gets dropped at the receiver. The sender then retransmits data that was never lost in the network.

Fixing this takes an explicit mechanism where the receiver tells the sender how much buffer space remains. TCP does this with the receive window, covered in [[systems/networks/4-transport/flow-control|flow control]].

## Related notes

- [[systems/networks/4-transport/flow-control|flow control]]
- [[systems/networks/4-transport/TCP|TCP]]
