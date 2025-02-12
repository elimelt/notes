---
title: Information Theory in Networks
category: Networks
tags: information theory, nyquist limit, shannon capacity, bandwidth, signal, noise
description: Describes the fundamental concepts of information theory in the context of networks. It covers key channel properties, the Nyquist limit, and Shannon capacity, and discusses the wired and wireless perspectives of information theory.
---

## Key Channel Properties

- **Bandwidth (B)**: The range of frequencies that can be transmitted over a channel.
- **Signal (S)**: The signal is the information that is being transmitted over the channel.
- **Noise (N)**: The noise is the unwanted information that is being transmitted over the channel.

## Nyquist Limit

Maximum *symbol* rate is 2B symbols/sec.

If there are V signal levels, max bit rate is:

R = 2B log_2(V) bits/sec

## Shannon Capacity

**Capacity (C)** limit is the maximum **lossless** information carrying rate of a channel.

C = B log_2(1 + S/N) bits/sec

- There is some rate at which we can transmit information over a channel without error.
- Assuming noise is fixed, we can increase the bandwidth to increase the capacity, albeit with diminishing returns.
- Increasing bandwidth increases capacity linearly

**Can't beat the Shannon limit**


## Wired/Wireless Perspecitive

