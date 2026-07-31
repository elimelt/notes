---
title: Framing in Network Protocols
category: Networks
tags:
  - framing
  - byte-stuffing
  - bit-stuffing
  - ppp
  - hdlc
  - sonet
date: 2024-01-15
updated: 2026-07-30
status: evergreen
description: How link protocols mark frame boundaries in a bit stream. Covers byte-oriented framing (length fields, sentinels, PPP), bit-oriented framing (HDLC and bit stuffing), and clock-based framing (SONET).
sources:
  - title: "Computer Networks: A Systems Approach (Peterson and Davie)"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

The physical layer delivers a stream of bits. The link layer has to know where each frame starts and ends inside that stream. This note covers the three families of framing, based on Peterson and Davie's treatment: byte-oriented, bit-oriented, and clock-based.

## Byte-oriented framing

The oldest approach views a frame as a collection of bytes. BISYNC (IBM), DDCMP (DECNET), and PPP all frame this way. Within the family there are two ways to find the end of a frame.

### Length field approach

DDCMP puts the frame's byte count in the header, and the receiver counts bytes until the frame is done. The weakness is that a transmission error in the count field desynchronizes the receiver from the real frame boundaries, a framing error.

### Sentinel approach and byte stuffing

BISYNC instead marks frame boundaries with special characters (SYN, STX, ETX). The problem is that the payload can contain those same characters. The fix is to escape them, inserting an escape character before any sentinel byte that appears in the data, the same way C strings escape quotes. This is byte stuffing.

### PPP frame format

PPP carries IP packets over point-to-point links. Its flag field, 01111110, marks the start of a frame, several of its field sizes are negotiable, and a CRC protects the frame.

The negotiation happens through the Link Control Protocol (LCP). LCP control messages are themselves carried inside PPP frames, and LCP runs the link establishment between the two peers.

## Bit-oriented framing (HDLC)

Bit-oriented protocols treat the frame as a bit stream and ignore byte boundaries. IBM's SDLC was the first, later standardized by ISO as HDLC.

HDLC marks both the start and end of a frame with the bit sequence 01111110. Like the sentinel approach above, this raises the question of what happens when the payload contains the marker, and the answer is bit stuffing.

### Bit stuffing

The sender inserts a 0 after every five consecutive 1s in the body. The receiver, on seeing five 1s, looks at the next bit. A 0 was stuffed, so it gets removed. A 1 means this is either the end-of-frame marker or an error, and the bit after that decides which.

## Frame size

With stuffing, the bits on the wire depend on the payload, so frames of equal payload size can differ in length, and no fixed frame size can be enforced. Clock-based protocols take the opposite approach.

## Clock-based framing (SONET)

The Synchronous Optical Network (SONET) standard handles framing, encoding, and multiplexing for data over optical fiber. SONET frames have a fixed length and rely on timing rather than stuffing.

The receiver finds frame boundaries by looking for a special bit pattern that recurs at a fixed interval, every 810 bytes in an STS-1 frame. Since the frame length never depends on the data, no stuffing is needed. Payload bytes are scrambled to guarantee enough signal transitions for clock recovery, and a good chunk of SONET's complexity comes from its overhead bytes and network-level features.

### Multiplexing and concatenation

SONET links run at a hierarchy of rates from STS-1 up to STS-768, and a single SONET frame can carry subframes for multiple lower-rate channels. An STS-N frame is N interleaved STS-1 frames. When the payload should be treated as one fat pipe instead of N thin ones, the payloads are concatenated, written STS-Nc. Keeping the hierarchy synchronous simplifies clock coordination across carriers' networks.

## Related notes

- [[networks/2-direct-links/errors|error detection]]
- [[networks/2-direct-links/multiple-access|multiple access]]
