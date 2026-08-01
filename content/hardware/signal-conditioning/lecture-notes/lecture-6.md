---
title: Capacitors
aliases:
  - signal-conditioning/lecture-notes/lecture-6
category: Signal Conditioning
tags:
  - capacitance
  - inductance
  - impedance
  - complex numbers
  - phasors
  - energy storage
date: 2024-01-17
updated: 2026-07-30
status: draft
description: Lecture 6 notes on capacitors and inductors as energy storage elements, complex number representation of AC signals, impedance, and phasors.
sources:
  - title: Signal conditioning course, lecture 6
    type: lecture
---

## Purpose

Capacitors and inductors store energy, and their behavior depends on frequency. This note records their defining relations, then the complex number machinery (impedance and phasors) that lets you analyze AC circuits with the same rules you use for resistors.

## Capacitors

A capacitor stores energy in the electric field between two plates. It passes AC and blocks DC, which is why a series capacitor acts as a high pass filter.

Capacitance is the ratio of charge to voltage, measured in Farads:

$$
C = \frac{Q}{V}
$$

The energy stored in a capacitor is

$$
E = \frac{1}{2}CV^2
$$

Differentiating $Q = CV$ with respect to time gives the current through the capacitor:

$$
I_C = C\frac{dV}{dt}
$$

## Inductors

An inductor stores energy in the magnetic field around a coil of wire, built up by the current flowing through it. Units are Henrys (H). It passes DC and blocks AC, acting as a low pass filter in series.

The energy stored in an inductor is

$$
E = \frac{1}{2}LI^2
$$

and the voltage across it is

$$
V_L = L\frac{dI}{dt}
$$

## Complex numbers review

With $j$ defined by $j \cdot j = -1$, Euler's formula connects exponentials to sinusoids:

$$
e^{j\theta} = \cos(\theta) + j\sin(\theta)
$$

## Complex numbers for AC signals

Pretend signals are complex during analysis, then take the real part at the end. Multiplying by a real number scales the amplitude. Multiplying by a unit complex number $e^{j\phi}$ shifts the phase. Multiplying by a general complex number does both.

For example, a shifted cosine is the real part of a complex exponential:

$$
\cos(2\pi ft + \phi) = \operatorname{Re}\left\{e^{j\phi}e^{j2\pi ft}\right\}
$$

## Impedance

Impedance is the AC generalization of resistance:

$$
Z_{cap} = \frac{1}{j\omega C}, \qquad Z_{ind} = j\omega L, \qquad Z_{res} = R
$$

The capacitor's impedance shrinks as frequency grows, which matches "passes AC, blocks DC" above. The inductor's impedance grows with frequency, matching "passes DC, blocks AC".

> [!tip] Sanity check at the frequency extremes
> As $\omega \to 0$, $Z_{cap} \to \infty$ (open circuit) and $Z_{ind} \to 0$ (short circuit). As $\omega \to \infty$ the roles flip. Evaluating a derived transfer function at these two limits catches most algebra mistakes before you plot anything.

## Phasors

A phasor is a complex number that represents the amplitude and phase of a sinusoidal signal. Since impedances obey Ohm's law with phasors, the differential equations from $I_C = C\,dV/dt$ and $V_L = L\,dI/dt$ turn into algebra, and series and parallel combination rules carry over from resistors.

## Related

- [[hardware/signal-conditioning/lecture-notes/lecture-2|Electricity]]
- [[hardware/signal-conditioning/lecture-notes/lecture-3|Resistance]]
- [[reference/cheatsheets/circuits/components|Electronic Components]]
- [[reference/cheatsheets/circuits/electricity|Electric Circuit Analysis]]
