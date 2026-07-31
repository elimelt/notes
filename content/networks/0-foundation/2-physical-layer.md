---
title: The Physical Layer
category: Hardware
tags:
  - physical-layer
  - modulation
  - coding
  - clock-recovery
  - latency
date: 2024-01-05
updated: 2026-07-30
status: evergreen
description: How bits become signals on a link. Covers simple codings (NRZ, RZ), clock recovery, the difference between coding and modulation, a simple link model, and message latency with a worked example.
sources:
  - title: UW CSE 461 Computer Networks
    url: https://courses.cs.washington.edu/courses/cse461/
    type: course
  - title: "Computer Networks: A Systems Approach (Peterson and Davie)"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Explain how signals carry bits over a link. That means how digital data becomes an analog signal and back, and what delays a message picks up along the way. [[networks/1-physical/coding-and-modulation|Coding and modulation]] goes deeper on the encoding schemes themselves.

## Coding and modulation

A modem (modulator-demodulator) converts digital signals to analog signals and back.

### A simple coding

Use a high positive voltage for 1 and a low negative voltage for 0. This is **NRZ** (non-return-to-zero). Each time interval carries one **symbol**, and the receiver samples once per symbol.

NRZ only gets 1 bit per symbol. Using more voltage levels packs more bits into each symbol. To get $N$ bits per symbol you need $2^N$ voltage levels, and the more levels you use, the more sensitive the signal is to noise. Practical coding schemes trade these off in different ways depending on the engineering constraints of the link.

### Clock recovery

The receiver needs frequent signal transitions to decode bits. A long run of identical bits gives it nothing to synchronize on, so it loses track of where symbols begin and end. Manchester coding and scrambling both solve this.

A simple fix is return-to-zero (RZ) coding, which alternates between the signal voltage and zero after each bit:

```txt
    0       1        1      1       0
+V |        ___     ___     ___
   |   |   |   |   |   |   |   |   |   |
   |   |   |   |   |   |   |   |   |   |
0  |   |___|   |___|   |___|   |___|   |
   |   |   |   |   |   |   |   |   |   |
   |   |   |   |   |   |   |   |   |   |
-V |___|   |   |   |   |   |   |   |___|
```

You can do better than RZ. Map input bit patterns to longer output patterns chosen so that long runs of zeros cannot occur (4b/5b works this way). Or XOR the data with a pseudorandom bit pattern before sending, which makes the encoded data look random and kills most long runs. Both approaches show up in [[networks/1-physical/coding-and-modulation|coding and modulation]].

### Modulation vs. coding

With **coding**, the signal goes directly onto the wire. That works poorly for wireless, so wireless links use **modulation** instead. Modulation carries a signal by varying the frequency, amplitude, or phase of a carrier wave. The original signal is the **baseband**, and the modulated signal is the **passband**.

Examples:

- NRZ signal of bits sent directly on a wire
- Amplitude shift keying (Zigbee)
- Frequency shift keying (Bluetooth)
- Phase shift keying

Modern WiFi goes further and uses a whole band of frequencies with many signal levels rather than two.

### Key points

- Everything is analog, even digital signals. A digital signal is conceptually discrete but lives in a continuous physical medium.
- Modulating and demodulating converts between the digital data and the analog carrier.
- A coding is an agreed-upon language for your data.

## Simple link model

Two main parameters describe a link:

- **Rate** (bandwidth, capacity, speed): bits per second
- **Delay**: how long a message takes to get across

Also relevant are the type of cast (unicast, multicast, broadcast) and the error rate.

### Message latency

**Latency** is the time a message takes to travel from one end of a link to the other. It is the sum of the **transmission delay** (time to put the bits on the wire) and the **propagation delay** (time for the bits to cross the link). Signals in copper and fiber travel at roughly $\frac{2}{3}c$, which is where the $3D/2c$ form comes from.

```txt
Transmission delay:
T = L (message length) / R (rate) = L/R seconds

Propagation delay:
P = D (distance) / S (speed) = D / (2/3 * C) = 3D/2C seconds

Total latency:
L_t = T + P = L/R + 3D/2C
```

#### Example

A broadband cross-country link with $P = 50\text{ ms}$, $R = 10$ Mbps, and a message of $L = 1$ MB:

```txt
L = 1 MB = 8 Mb
T = 8 Mb / 10 Mbps = 0.8 s
L_t = 0.8 s + 0.05 s = 0.85 s
```

Transmission delay dominates here. On a faster link the propagation delay would take over, since distance does not shrink with the rate.

### Cut-through routing

Store-and-forward switching pays the full transmission delay at every hop, because each node buffers the whole message before sending it on. Cut-through routing starts forwarding as soon as the destination header arrives, before the rest of the message is in. That cuts per-hop latency, at the cost of forwarding frames before their checksum can be verified.

## Related notes

- [[networks/1-physical/coding-and-modulation|coding and modulation]]
- [[networks/0-foundation/information-theory|information theory]]
- [[networks/0-foundation/3-performance|performance]]
