---
title: Information Theory in Networks
aliases:
  - networks/0-foundation/information-theory
category: Networks
tags:
  - information-theory
  - nyquist-limit
  - shannon-capacity
  - bandwidth
  - noise
date: 2024-01-13
updated: 2026-07-30
status: evergreen
description: The Nyquist limit and Shannon capacity, what each one bounds, and why adding bandwidth gives diminishing returns when noise scales with it.
sources:
  - title: A Mathematical Theory of Communication (Shannon, 1948)
    url: https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf
    type: paper
  - title: UW CSE 461 Computer Networks
    url: https://courses.cs.washington.edu/courses/cse461/
    type: course
---

## Purpose

Two classical results bound how fast any channel can carry bits. The Nyquist limit bounds the symbol rate of a band-limited channel, and the Shannon capacity bounds the bit rate once noise enters the picture. Every physical link in these notes lives under both bounds.

> [!abstract] Two limits, two regimes
> Nyquist assumes a noiseless channel and bounds the *symbol rate*: bandwidth alone caps how many signal changes per second the channel can carry. Shannon adds noise and bounds the *bit rate*: the signal-to-noise ratio caps how many levels per symbol the receiver can tell apart. Nyquist says how often you can signal, Shannon says how much each signal can say.

## Key channel properties

- **Bandwidth** $B$ (Hz): the range of frequencies the channel can carry.
- **Signal power** $S$: the strength of the transmitted signal at the receiver.
- **Noise power** $N$: the strength of everything else the receiver picks up.

## Nyquist limit

A channel of bandwidth $B$ can carry at most $2B$ symbols per second. Sending faster than that adds no information, because a band-limited signal is fully determined by samples taken at rate $2B$.

If each symbol can take one of $V$ distinguishable signal levels, each symbol carries $\log_2 V$ bits, so the maximum bit rate is

$$R = 2B \log_2 V \ \text{bits/sec}$$

Noise is ignored here. In practice noise decides how large $V$ can be, and that is Shannon's result.

## Shannon capacity

The **capacity** $C$ of a channel is the maximum rate at which it can carry information with arbitrarily low error:

$$C = B \log_2\left(1 + \frac{S}{N}\right) \ \text{bits/sec}$$

The intuition connects back to Nyquist. Noise smears the received signal, so only levels spaced further apart than the noise can be told apart. The signal-to-noise ratio $S/N$ therefore fixes the number of usable levels, and $\log_2(1 + S/N)$ plays the role $\log_2 V$ played above.

[Shannon's noisy-channel coding theorem](https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf) says both directions hold. For any rate below $C$ there exist codes that drive the error rate as low as you like, and no code can do better than $C$. You can't beat the Shannon limit.

### Diminishing returns from bandwidth

Read the formula carefully before concluding that more bandwidth means proportionally more capacity. If the noise power $N$ stays fixed while $B$ grows, capacity does grow linearly in $B$. But for white noise the noise power scales with the bandwidth you open up, $N = N_0 B$ for noise density $N_0$, so

$$C = B \log_2\left(1 + \frac{S}{N_0 B}\right) \xrightarrow{B \to \infty} \frac{S}{N_0} \log_2 e$$

Capacity flattens out. Past a point, extra bandwidth buys almost nothing, and only more signal power (or less noise) moves the ceiling.

## Related notes

- [[systems/networks/1-physical/media|media]]
- [[systems/networks/0-foundation/2-physical-layer|the physical layer]]
- [[systems/networks/0-foundation/3-performance|performance]]
