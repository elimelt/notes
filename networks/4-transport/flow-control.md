---
title: Flow Control
category: Networks
tags: flow control, sliding window, ARQ, bandwidth-delay product
description: Covers the implementation of flow control mechanisms in computer networks, with a focus on the sliding window protocol. Discusses the sender and receiver-side operations of the sliding window, including the use of sequence numbers and the Go-Back-N and Selective Repeat Automatic Repeat Request (ARQ) schemes. Explains the concept of bandwidth-delay product and its importance in determining the appropriate window size for efficient data transfer.
---

# Flow Control

Recall **stop and wait** ARQ. This only allows a single packet to be transmitted at a time. This is inefficient, as the sender is often waiting for the receiver to acknowledge the packet. 

Next recall **sliding window** ARQ. This allows multiple packets to be transmitted at a time. The sender can keep sending packets until the window is full. The receiver can acknowledge packets in any order, and the sender can keep sending packets until the window is full. With a window size of $w$, you can send $w$ packets before waiting for an acknowledgement (ie $w$ packets per RTT).

### Sliding Window Example

Assuming $10$ kb packets, $R = 1$ Mbps, $d = 50$ ms, what window size $w$ do you need to use the network capacity?

First, knowing RTT = $2d = 100$ ms, we can calculate the maximum throughput using the bandwidth-delay product:

BD $= R \times d = 1 \times 10^6 \times 0.05 = 50,000$ bits

so $100000$ bits per RTT can be stored in the network. Therefore, the window size $w$ is:

$w = \frac{100000}{10000} = 10$



### Sliding Window Sender

Sender buffers up to $w$ segments until they are acked. LFS (Last Frame Sent) is the sequence number of the last frame sent. LAR (Last Ack Received) is the sequence number of the last frame acked. The sender can send up to $w$ frames, and the receiver can receive up to $w$ frames, where

$w > LFS - LAR$


### Sliding Window Receiver

#### Go-Back-N ARQ

In Go-Back-N ARQ, the sender can send multiple packets before waiting for an acknowledgement. The receiver can acknowledge packets in any order, and the sender can keep sending packets until the window is full. If a packet is lost, the sender will have to resend all packets from the lost packet onwards.

The reciever keeps only a single packet buffer for the next segment. (ie keeps LAS = LAST ACK SENT). On receive, if seq number is LAS + 1, then accept, update LAS, and send ACK. Else, discard.

Uses a single timer to detect lost packets. On timeout, resends buffered packets starting from LAS + 1.

#### Selective Repeat ARQ

In Selective Repeat ARQ, the sender can send multiple packets before waiting for an acknowledgement. The receiver can acknowledge packets in any order, and the sender can keep sending packets until the window is full. If a packet is lost, the sender will only have to resend the lost packet.

Receiver buffers $w$ segments, and keeps LAS = LAST ACK SENT. On reeive, buffer segments $[LAS + 1, LAS + w]$. If seq number is LAS + 1, then accept, update LAS, and send ACK.

If it receives something out of order, it will buffer it and send an ACK for the last in-order segment. If it receives a duplicate, it will send an ACK for the last in-order segment.

Uses a timer for each segment. On timeout, resends the segment.

### Sequence Numbers

For stop and wait, only need 0/1. For selective repeat, need $w$ numbers for packets, and $w$ numbers for acks of earlier packets. ($2w$ in total). For go-back-n, need $w$ numbers for packets, and 1 number for the ack of the last packet. ($w + 1$ in total).


