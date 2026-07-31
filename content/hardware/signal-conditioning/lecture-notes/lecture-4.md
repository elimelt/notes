---
title: Power Dissipation In a Resistor
aliases:
  - signal-conditioning/lecture-notes/lecture-4
category: Signal Conditioning
tags:
  - power dissipation
  - resistor
  - kirchhoff's laws
  - voltage source
  - current source
date: 2024-01-10
updated: 2026-07-30
status: evergreen
description: Lecture 4 notes on power dissipation, Kirchhoff's laws, and ideal sources, with a worked voltage divider example and a resistor model of iPhone standby draw.
sources:
  - title: Signal conditioning course, lecture 4
    type: lecture
---

## Purpose

A resistor that is getting warm is leaking power. This note states the power relations and Kirchhoff's laws, works one divider example end to end, and models the iPhone standby draw from [[hardware/signal-conditioning/lecture-notes/lecture-2|lecture 2]] as a single resistor.

## Power dissipation

$$P = VI = I^2R = V^2/R$$

## Kirchhoff's laws

**Voltage (KVL)**: The voltages along any closed path around a circuit sum to zero.

**Current (KCL)**: The current arriving at any node equals the current leaving that node.

## Worked example

A 120 V source drives two resistors in series:

```txt
      R_1 = 1 Ohm
  +--/\/\/|--+
  |          |
  _          |
  + 120 V    |
  -          |
  |          |
  +--\/\/\|--+
      R_2 = 10 Ohm
```

By Ohm's law, $V_1 = I R_1$ and $V_2 = I R_2$. The voltage divider gives the voltage across $R_2$:

$$V_2 = V \cdot \frac{R_2}{R_1 + R_2} = 120 \cdot \frac{10}{11} = 109\,\text{V}$$

$$P_2 = \frac{V_2^2}{R_2} = \frac{109^2}{10} = 1188\,\text{W}$$

The current follows from the voltage left across $R_1$:

$$I = \frac{V - V_2}{R_1} = \frac{120 - 109}{1} = 11\,\text{A}$$

$$P_1 = I^2 R_1 = 11^2 \times 1 = 121\,\text{W}$$

## Ideal sources

A voltage source produces a *constant* voltage regardless of the current drawn, which is an idealistic assumption. A current source delivers *constant* current to a circuit, with the voltage across it determined by the load resistance (impedance).

## Modeling the iPhone as a resistor

In [[hardware/signal-conditioning/lecture-notes/lecture-2|lecture 2]] we estimated that an iPhone in standby draws 7.55 mA from its 3.8 V lithium battery. Model the phone's power consumption as a single resistor across the battery:

```txt

ground
  ^
  |     battery
  |       |
  |       |
  +----- |-  +|-----+
  |                 |
  |                 |
  +-----|/\/\/|-----+
           |
           |
 phone power consumption

```

The equivalent resistance is $R = V/I = 3.8\,\text{V} / 7.55\,\text{mA} \approx 503\,\Omega$.

## Related

- [[hardware/signal-conditioning/lecture-notes/lecture-3|Resistance]]
- [[hardware/signal-conditioning/lecture-notes/lecture-5|Thevenin's Theorem]]
