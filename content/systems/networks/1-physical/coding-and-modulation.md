---
title: Coding and Modulation
aliases:
  - networks/1-physical/coding-and-modulation
category: Networks
tags:
  - nrz
  - rz
  - clock-recovery
  - manchester-encoding
  - scrambling
  - keying
  - bandwidth-delay-product
date: 2024-02-03
updated: 2026-07-30
status: evergreen
description: How bits are put on a link. Covers NRZ and RZ coding, clock recovery, code design (4b/5b), the keying schemes (ASK, FSK, PSK), and the link model with latency and the bandwidth-delay product.
sources:
  - title: "Computer Networks: A Systems Approach (Peterson and Davie)"
    url: https://book.systemsapproach.org/
    type: textbook
  - title: UW CSE 461 Computer Networks
    url: https://courses.cs.washington.edu/courses/cse461/
    type: course
---

## Purpose

Answer one question. How does information actually get sent over a link? Coding puts bits directly on a wire, modulation rides them on a carrier wave, and the link model at the end quantifies what the link costs you in time.

## Coding

### Non-return-to-zero (NRZ)

A 1 is a high voltage and a 0 is a low voltage. Long runs of the same bit cause two problems.

- **Clock drift**: the receiver loses track of the clock when the signal doesn't transition, and starts sampling in the wrong places.
- **Baseline wander**: the receiver keeps a running average of the signal to set the threshold between 1s and 0s. A long run drags the average toward one rail and the receiver starts misreading bits.

### Clock recovery

Recovering the clock from an NRZ signal that rarely transitions is hard because the receiver has nothing to synchronize its sampling against. Manchester encoding and scrambling both force transitions back into the signal.

### Return-to-zero (RZ)

After each bit, the signal returns to zero. Every bit now comes with a transition, so the receiver can resynchronize on each one. The cost is that each bit takes twice the signal changes, which halves the data rate for a given symbol rate.

### Designing codes

More generally, you can map one set of bits to another set of bits and send the mapped bits over the link, choosing the mapping so the output has good clock recovery and noise properties.

In 4b/5b, let $S$ be the set of all 4-bit sequences and $C$ the set of 5-bit sequences actually used on the wire. The code is a function $f: S \to C$:

$$
f(0000) = 11110 \\
f(0001) = 01001 \\
f(0010) = 10100 \\
\vdots
$$

The 5-bit codewords are chosen so that long runs of 0s and 1s can't happen. Since $C$ has more symbols than $S$ needs, the leftovers can carry control information such as the start of a frame.

## Modulation

**Modulation** transmits a digital signal over an analog channel by varying a carrier wave. The original signal is the **baseband** and the modulated signal is the **passband**. **Keying** is the digital form of modulation, playing the same role coding plays on a wire.

### Amplitude shift keying (ASK)

The amplitude of the carrier encodes the bit, high amplitude for 1 and low for 0. ASK shares NRZ's weakness, since a long run of one bit produces a steady signal with nothing to recover the clock from.

### Frequency shift keying (FSK)

The frequency of the carrier encodes the bit, high frequency for 1 and low for 0. FSK resists noise better than ASK because noise mostly perturbs amplitude.

### Phase shift keying (PSK)

The phase of the carrier encodes the bit, for example 0 degrees for 1 and 180 degrees for 0. PSK supports more bits per symbol than ASK or FSK, which gives higher data rates.

## Link model

- **Transmitter**: converts the digital signal to an analog signal.
- **Channel**: the medium the signal crosses. See [[systems/networks/1-physical/media|media]].
- **Receiver**: converts the analog signal back to digital.

### Properties of the channel

- **Rate** (bandwidth): bits per second the channel can carry.
- **Delay**: time for a signal to cross from transmitter to receiver, roughly proportional to distance.

### Latency

Latency is the sum of the **transmission delay** and the **propagation delay**.

Transmission delay is the time to put an $M$-bit frame on the link:

$$
D_{\text{transmission}} = \frac{\text{message size}}{\text{transmission rate}} = \frac{M}{R}
$$

where $R$ is the link rate in bits/sec. Propagation delay is the time the signal spends in flight:

$$
D_{\text{propagation}} = \frac{\text{distance}}{\text{speed in the medium}} = \frac{d}{.66c}
$$

where $d$ is the distance and $c$ is the speed of light. Signals in copper and fiber travel at roughly two thirds of $c$. Together:

$$
L = \frac{M}{R} + D_{\text{propagation}}
$$

### Bandwidth-delay product

Messages take up space on the wire, and the wire only holds so many bits at once. The **bandwidth-delay product** is the number of bits in transit at any moment when the link is kept full:

$$
BD = R \cdot D_{\text{propagation}}
$$

Usually either the bandwidth or the delay is the bottleneck, and BD tells you the overall capacity of the pipe. It matters for [[systems/networks/2-direct-links/retransmission|retransmission]] protocols, which must keep BD bits outstanding to use the link fully.

> [!example] A fat, long pipe
> A 100 Mbps cross-country link with 25 ms propagation delay holds $BD = 10^8 \cdot 0.025 = 2.5$ Mbit, about 312 KB in flight. A protocol that sends one 1500-byte frame and then waits a full 50 ms round trip for the reply moves 12,000 bits per 50 ms, about 240 kbps, using under 0.3% of the link.

## Related notes

- [[systems/networks/1-physical/media|media]]
- [[systems/networks/0-foundation/2-physical-layer|the physical layer]]
- [[systems/networks/2-direct-links/errors|error detection]]
