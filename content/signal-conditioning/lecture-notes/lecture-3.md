---
title: Resistance
category: Hardware
tags:
  - resistance
  - ohm's law
  - power
  - series resistors
  - parallel resistors
date: 2024-01-08
updated: 2026-07-30
status: evergreen
description: Lecture 3 notes on resistance, Ohm's law, power dissipation, and how resistance, voltage, and current combine in series and parallel circuits.
sources:
  - title: Signal conditioning course, lecture 3
    type: lecture
---

## Purpose

Defines resistance and Ohm's law, then derives how voltage, current, and resistance combine when resistors sit in series and in parallel.

## Resistance

Resistance is the opposition to the flow of current. It is measured in Ohms ($\Omega$) and is the ratio of voltage to current. It is usually an intrinsic property of the material.

### Ohm's law

$$V = IR$$

## Power

Power is the rate of change of energy, measured in Joules per second, i.e. Watts (W).

The power dissipated by a resistor is the product of the voltage across it and the current through it. Intuitively this makes sense because it takes energy to push electrons through a resistor, and the more electrons you push through, the more energy you spend. Holding $I$ constant, power is directly proportional to the resistance:

$$P = IV = I^2R = V^2/R$$

## Resistors in series and parallel

### Series

Resistors in series are connected end to end. The total resistance is the sum of the individual resistances:

$$R_t = R_1 + R_2 + \ldots + R_n$$

The current through each resistor is the same, because current is the flow of electrons and the electrons have nowhere else to go.

The voltage across each resistor can differ, but the total voltage is the sum of the voltages across each resistor. This follows from the two properties above plus Ohm's law:

$$V_t = IR_t = I(R_1 + R_2 + \ldots + R_n) = IR_1 + IR_2 + \ldots + IR_n = V_1 + V_2 + \ldots + V_n$$

### Parallel

Resistors in parallel are connected so that both ends of each resistor attach to the same two points of the circuit. The total resistance is the reciprocal of the sum of the reciprocals:

$$R_t = \frac{1}{\frac{1}{R_1} + \frac{1}{R_2} + \ldots + \frac{1}{R_n}}$$

The voltage across each resistor is the same, because voltage is the potential difference between two points and every resistor shares the same two points (equal to the source voltage).

The current through each resistor can differ, but the total current between the two endpoints is the sum of the currents through each resistor. You can see this from conservation of charge at the shared nodes, and derive it from Ohm's law:

$$I_t = \frac{V_t}{R_t} = V_t\left(\frac{1}{R_1} + \frac{1}{R_2} + \ldots + \frac{1}{R_n}\right) = \frac{V_t}{R_1} + \frac{V_t}{R_2} + \ldots + \frac{V_t}{R_n} = I_1 + I_2 + \ldots + I_n$$

## Related

- [[signal-conditioning/lecture-notes/lecture-4|Power Dissipation in a Resistor]]
- [[signal-conditioning/lecture-notes/lecture-5|Thevenin's Theorem]]
