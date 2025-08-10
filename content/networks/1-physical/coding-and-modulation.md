---
title: Coding and Modulation
category: Hardware
tags: NRZ, RZ, Clock Recovery, Manchester encoding, Scrambling
description: Describes technical concepts related to coding and modulation techniques in hardware applications, specifically focusing on NRZ, RZ, clock recovery, Manchester encoding, scrambling, ASK, FSK, PSK, channel properties, latency, and bandwidth-delay product. The document covers the design of codes for error detection and correction, types of modulation schemes used for data transmission, and characteristics of communication channels that affect signal quality.
---

# Coding and Modulation

*How information sent over a link?*

## Coding

### None-return-to-zero (NRZ)

1 is represented by a high voltage and a 0 is represented by a low voltage. This can however lead to problems with long runs of 1s or 0s.

- **Long runs of 1s**: The receiver might lose track of the clock, and the signal might be corrupted.
- **baseline wander**: The receiver keeps an average of the signal to determine the threshold for 1s and 0s. If there are long runs of 1s or 0s, the average might drift, and the receiver might start to misinterpret the signal.

### Clock Recovery

It is difficult to recover the clock from a NRZ signal that doesn't transition often. This is because the receiver doesn't know when to sample the signal. Several techniques are used to solve this problem, including manchester and scrambling. 

### Return-to-Zero (RZ)

After each bit, the signal returns to zero. This makes it easier to recover the clock, since the receiver can sample the signal after each return to zero.

### Designing Codes

One can design codes that are more robust to noise, or that have better clock recovery properties. In general, you map one set of bits to another set of bits, and then send the new bits over the link.

For example, in 4b/5b, we let $S$ be the set of all possible 4-bit sequences, and let $C$ be the set of all possible 5-bit sequences. Then we can define a code $f: S \to C$:

$$
f(0000) = 11110 \\
f(0001) = 01001 \\
f(0010) = 10100 \\
\vdots
$$

One can then choose a set $C$ such that there aren't long runs of 1s or 0s, or such that the clock can be recovered easily. Since there are left over symbols in $C$, we can use them to represent control information, such as the start of a frame.

## Modulation

**Modulation** transmits a digital signal over an analog channel by modulating a carrier. **Baseband** is the original signal, and **passband** is the modulated signal. **Keying** is the digital form of modulation (equivalent to coding, but using modulation instead).

### Amplitude Shift Keying (ASK)

In ASK, the amplitude of the carrier is changed to represent the digital signal. For example, a 1 might be represented by a high amplitude, and a 0 by a low amplitude. This faces the same problem as NRZ, in that it is difficult to recover the clock.

### Frequency Shift Keying (FSK)

In FSK, the frequency of the carrier is changed to represent the digital signal. For example, a 1 might be represented by a high frequency, and a 0 by a low frequency. This is more robust to noise than ASK.

### Phase Shift Keying (PSK)

In PSK, the phase of the carrier is changed to represent the digital signal. For example, a 1 might be represented by a phase of 0 degrees, and a 0 by a phase of 180 degrees. PSK can support more bits per symbol than ASK or FSK, leading to higher data rates.

## Link Model

- **Transmitter**: Converts digital signal to analog signal.
- **Channel**: The medium over which the signal is sent.
- **Receiver**: Converts analog signal to digital signal.

### Properties of the Channel

- **Rate** (or bandwidth): The number of bits per second that can be sent over the channel.
- **Delay**: The time it takes for a signal to travel from the transmitter to the receiver. Usually, the delay is proportional to the distance between the transmitter and the receiver.

### Latency

The delay in sending a signal from the transmitter to the receiver. This is the sum of the **propagation delay** and the **transmission delay**.

- **Propagation delay**: The time it takes for a signal to travel from the transmitter to the receiver.
- **Transmission delay**: The time it takes to put an $M$-bit frame on the link.

$$
D_{\text{transmission}} = \frac{\text{message size}}{\text{transmission rate}} = \frac{M}{R}
$$

where $R$ is the rate of the link in bits/sec and $M$ is the size of the frame in bits.

$$
D_{\text{propagation}} = \frac{\text{distance}}{\text{speed of the medium}} = \frac{d}{.66c}
$$

where $d$ is the distance between the transmitter and the receiver, and $c$ is the speed of light.

Overall, we can calulate the latency as:

$$
L = \frac{M}{R} + D_{\text{propagation}}
$$

### Bandwidth-Delay Product

Messages take up space on the wire, and the wire can only hold so many bits at a time. The **bandwidth-delay product** is the maximum number of bits that can be in transit at any time.

$$
\text{Bandwidth-Delay Product} = BD = R \cdot D_{\text{propagation}}
$$

Usually, either the bandwidth or the delay is the bottleneck. The BD gives us a sense of the overall capacity of the link