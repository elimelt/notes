---
title: Media in Networks
category: Networks
tags:
  - media
  - twisted-pair
  - coaxial-cable
  - fiber
  - wireless
  - nyquist-limit
  - shannon-capacity
date: 2024-02-03
updated: 2026-07-30
status: evergreen
description: The physical media that carry signals. Compares twisted pair, coaxial cable, fiber, and wireless, then states the channel properties and the Nyquist and Shannon limits that apply to all of them.
sources:
  - title: A Mathematical Theory of Communication (Shannon, 1948)
    url: https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf
    type: paper
  - title: "Computer Networks: A Systems Approach (Peterson and Davie)"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Media propagate the signals that carry information. This note compares the common wired media and wireless, then states the two limits that cap what any of them can carry.

## Wires

### Twisted pair

Two insulated copper wires twisted around each other. The twisting reduces radiation and crosstalk, so the pair picks up less interference than parallel wires would. Twisted pair is very common in LANs and phone lines. Ethernet and DSL run over it.

### Coaxial cable

A copper core, wrapped in insulation, wrapped in a braided metal shield, wrapped in plastic. The shielding supports higher data rates and longer distances than twisted pair. The cable costs more, installs harder, and barely bends. Cable TV and cable Internet run over it.

### Fiber

Long, thin strands of very pure glass that carry modulated light. Fiber gives very high data rates over long distances and is immune to electromagnetic interference, at the price of expensive hardware and installation. The Internet backbone runs on it. Multi-mode versus single-mode fiber comes down to whether the light has multiple paths through the strand or one.

## Wireless

A wireless sender radiates its signal through a region of space in all directions. Nearby signals **interfere** with each other, especially on the same frequency, so senders have to coordinate their use of time and frequency.

WiFi largely uses unlicensed (ISM) spectrum, which is free to use and therefore crowded. A running microwave oven can interfere with WiFi on the 2.4 GHz band.

Signals also take multiple paths to the receiver (**multipath**) and get absorbed by physical barriers. Higher frequencies get absorbed more easily by walls and obstacles, which is why millimeter-wave 5G struggles indoors.

## Channel properties

- **Bandwidth** $B$ (Hz): the range of frequencies the channel can carry. This is a different quantity from the data rate of a link, though it bounds it.
- **Signal power** $S$ (Watts): the strength of the signal.
- **Noise power** $N$ (Watts): the strength of the noise.

## Nyquist limit

The maximum symbol rate is twice the bandwidth, $2B$ symbols per second. Hitting it means running the channel at its maximum frequency and reading a symbol off each peak and trough of the wave.

With $V$ signal levels, and ignoring noise, the maximum data rate is $2B \log_2 V$ bits/sec.

## Shannon capacity

Noise limits how many signal levels the receiver can tell apart. The signal-to-noise ratio (SNR) determines that number, and it is usually quoted in decibels:

$$
SNR_{dB} = 10 \log_{10} \left( \frac{S}{N} \right)
$$

Capacity $C$ is the maximum lossless data rate over the channel:

$$
C = B \log_2 \left( 1 + \frac{S}{N} \right)
$$

The derivation is in [Shannon's 1948 paper](https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf), and [[networks/0-foundation/information-theory|information theory]] unpacks the intuition. Increasing bandwidth increases capacity linearly when noise is fixed, while increasing SNR only helps logarithmically.

## Related notes

- [[networks/1-physical/coding-and-modulation|coding and modulation]]
- [[networks/0-foundation/information-theory|information theory]]
