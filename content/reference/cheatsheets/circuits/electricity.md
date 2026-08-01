---
title: Electric Circuit Analysis
aliases:
  - cheatsheets/circuits/electricity
category: Reference
tags:
  - circuits
  - ohms-law
  - kirchhoffs-laws
  - impedance
  - power
date: 2024-03-11
updated: 2026-07-30
status: evergreen
description: Basics of circuit analysis, covering voltage, current, resistance, Ohm's law, Kirchhoff's laws, power, impedance, and phasors.
---

The basics I keep coming back to when analyzing circuits. Component-specific equations live in [[reference/cheatsheets/circuits/components|Electronic Components]].

## Flow of Electricity

Electricity is the flow of electrons, and it behaves like many other kinds of flow. Engineers use **conventional current**, which treats current as positive charge flowing from high potential to low potential. Electrons actually carry negative charge and drift the other way, from low potential to high.

**Potential** is the energy per unit charge at a point in space. It's measured in volts, and it's the driving force behind the flow of electricity. From this point on I'll call it voltage, like a true engineer.

It helps to think of voltage like the potential energy of a ball on a track. A higher voltage means the electron has a longer way to fall. The model only takes you so far, but it works as a mental picture of how electricity behaves.

If voltage is the driving factor behind the flow (like gravity), then **current** is the magnitude of the flow itself (like throughput). It's measured in amperes (A, Amp), a compound unit of charge per unit time.

**Resistance** is the opposition to the flow of electricity. It's measured in ohms ($\Omega$). Anything that drops the voltage when current flows through it acts like resistance, the way a hill or friction acts on a rolling ball.

## Short Circuit

A short circuit is any path with negligible resistance, or ideally zero resistance. Connecting any two points in a circuit with a wire could be called "shorting" them together. Doing this across something like a battery is bad, because forcing a voltage drop over near-zero resistance produces a theoretically limitless, and in practice destructive, amount of current.

Shorting two points together is fine on its own. They just need to be points that are supposed to sit at the same voltage.

## Open Circuit

Open circuits are the opposite of short circuits. They're non-conducting paths, or ideally infinite resistance. No current can flow through an open circuit, and it acts like a gap between two wires.

A simple switch is an open circuit in the off position, and is literally as simple as a gap in the wire that closes when the switch is flipped.

## Ohm's Law

$$
V = IR
$$

Where $V$ is voltage, $I$ is current, and $R$ is resistance. The voltage we lose *across* a resistor is the product of its resistance and the current flowing through it. This linear relationship holds any time we need to solve for one of the three values, or reason about the relationship between them.

## Power

$$
P = IV
$$

$$
P = I^2R
$$

$$
P = \frac{V^2}{R}
$$

Power is the rate at which energy is transferred. It's measured in watts (W), and is the product of voltage and current. Substituting Ohm's law gives the forms in terms of current and resistance, or voltage and resistance.

Power can either "sink" into a component or "source" from it. When power is being dissipated, the component is a sink. When power is being generated, it's a source. Typically, when current flows out of a component it's a source, and when current flows into a component it's a sink. We give a source a positive sign and a sink a negative sign.

## Kirchhoff's Laws

### Kirchhoff's Current Law (KCL)

The sum of currents entering a node is equal to the sum of currents leaving a node. Current has to go somewhere. It can't just disappear.

### Kirchhoff's Voltage Law (KVL)

The sum of voltages around a loop is equal to zero. This follows from conservation of energy. It's easiest to start from **ground**, a reference point with zero voltage, and work your way around the loop right back to any other ground in the circuit to complete the loop.

*Any other ground?* Yes, any other ground. Ground is a reference point, and can be placed anywhere in the circuit. If it helps, you can think of all the grounds as references to the same point in space, and the circuit as a series of loops around that point (only for the purpose of KVL analysis).

## Impedance

Impedance ($Z$) is measured in ohms ($\Omega$), and generalizes resistance to AC circuits. It similarly measures opposition to the flow of electricity, but can be a complex number, which shows up as a phase shift between the voltage and current.

It is convenient to transform sinusoidal AC signals into phasors so you don't need to solve a differential equation. A phasor represents a signal oscillating at a single frequency $\omega$ as a complex number that carries just its magnitude and phase, so you only track relative offsets and magnitudes.

Euler's formula ties the two views together:

$$e^{j\theta} = \cos(\theta) + j\sin(\theta)$$

The sinusoid $V(t) = V_m \cos(\omega t + \phi)$ has the phasor representation

$$V = V_m e^{j\phi} = V_m \angle \phi$$

which drops the time dependence and keeps the magnitude and phase.

## Series vs. Parallel

### Series

Connected end to end, so that the current flowing out of one flows into the other. Voltage drops accumulate across each component, and the current is the same through each component.

```plaintext
+---O---O---O---+
```

### Parallel

Connected side by side, on branches that originate from the same point. The current splits between the branches, and the voltage across each branch is the same.

```plaintext
   +---O---+
   |       |
---+       +---
   |       |
   +---O---+
```

## Related

- [[hardware/signal-conditioning/lecture-notes/lecture-3|Resistance]]
- [[reference/cheatsheets/circuits/components|Electronic Components]]
