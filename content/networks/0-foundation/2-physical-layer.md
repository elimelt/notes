---
title: The Physical Layer
category: Hardware
tags: dsp, modulation, coding, noise immunity, clock recovery
description: Describes the hardware component responsible for transmitting and receiving data in a communication system. It focuses on coding, modulation techniques, noise immunity, and clock recovery to ensure reliable data transfer. Key concepts include message latency, cut-through routing, and the differences between modulation and coding methods.
---

# The Physical Layer

**Scope**: How signals are used to transfer bits over a link. i.e, how analog signals are converted to digital signals, and vise versa.

## Coding and Modulation

A modem (modulator-demodulator) converts digital signals to analog signals, and vise versa.

### A simple coding

A high positive voltage for 1, and a low negative voltage for 0. This is called **NRZ**(Non-Return-to-Zero). Each time interval (**symbol**) is like a sample point.

### Problems?

Only 1 bit/symbol. Can use more than just 2 voltage levels to get more bits/symbol. To get N bits/symbol, need 2^n voltage levels. There is a tradeoff between encoding efficiency and the sensitivity to noise.

There are many other practical coding schemes, all of which are driven by engineering considerations.

### Clock Recovery

Reciever needs requent signal transitions to decode bits. Several possible designs, including Manchester Coding and Scrambling.

A simple solution is to alternate between positive/negative, and zero voltages. This is return to zero (RZ) coding.

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

#### Better Solution

-  Can map arbitrary bit patterns to eachother (as long as you don't decrease the number of bits to decode). Design encoding such that long runs of zero can't happen
-  Can even use xor and a psuedorandom bit pattern to encode and decode to make the encoded data random looking as well, getting rid of most long runs of zero.

### Modulation vs. Coding

In order to agree on the timing of data streams, AKA the start and end of a symbol being transmitted, you need to have a common clock between the two systems that are communicating.

With **coding**, signal is sent directly on a wire. This doesn't work well for wireless, so we use **modulation**. **Modulation** carries a signal by varying the frequency, amplitude, or phase of a carrier wave. *Baseband* is the original signal, and *passband* is the modulated signal. We can modulate a signal by varying the amplitude, frequency, or phase of a carrier wave.

#### Some examples:
- NRZ signal of bits
- Amplitude shift keying (zigbee)
- Frequency shift keying (bluetooth)
- Phase shift keying

WiFi for example goes all in and listens on an entire band of frequencies instead of just the binary 2 frequencies.Modern WiFi uses 256 frequency levels.

### Key Points

- Everythign is analog, even digital signals.
- Digital signals are conceptually discrete, but are represented physically in a continuous medium.
- Modulating and demodulating a signal is converting between analog to digital, and vise versa.
- A coding is an agreed upon "language" for your data.

## Simple Link Model

Two main parameters:

- **Rate** (bandwidth, capacity, speed): Number of bits per second
- **Delay**: Related to the time it takes to deliver a message

Additional info:

- **type of cast**: unicast, multicast, broadcast
- **error rate**

### Message Latency

**Latency** is the time it takes for a message to travel from one end of a link to the other. It is the sum of the **transmission delay** (time to put bits on wire) and the **propagation delay** (time for bits to travel from one end of the link to the other).

```txt
Transimission Delay:
T (delay) = L (message length) / R (rate) = L/R seconds

Propagation Delay:
P (delay) = D (distance) / S (speed) = D/(2/3 * C) = 3D/2C seconds

Total Latency:
L_t = T + P = L/R + 3D/2C
```

#### Example

```txt
Broadband cross-country link:
P = 50ms, R = 10Mbps, L = 1MB

L_t = 1MB/10MBps + 50ms = .1s + .05s = .15s
```


### Cut Through Routing








