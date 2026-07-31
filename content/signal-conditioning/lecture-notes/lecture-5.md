---
title: Thevenin's Theorem
category: Hardware
tags:
  - thevenin's theorem
  - norton's theorem
  - equivalent circuit
  - resistor
  - voltage source
  - current source
  - kirchhoff's laws
date: 2024-01-17
updated: 2026-07-30
status: evergreen
description: How to reduce any linear two-terminal circuit to a Thevenin equivalent (voltage source plus series resistor) or Norton equivalent (current source plus parallel resistor), and how the two relate.
sources:
  - title: Signal conditioning course, lecture 5
    type: lecture
---

## Purpose

Thevenin's and Norton's theorems collapse any linear two-terminal circuit into a single source and a single resistor. That equivalent circuit makes whatever you attach at the terminals much easier to analyze.

## Thevenin's theorem

Any two-terminal circuit with only linear elements (resistors) and sources can be replaced by an equivalent circuit consisting of a voltage source in series with a resistor. The voltage source is written $V_{th}$ and the resistor $R_{th}$.

To find the equivalent between terminals A and B:

1. Find $V_{th}$, the open-circuit voltage from A to B, using KCL and KVL.
2. Find $R_{th}$, the equivalent resistance between A and B, by replacing voltage sources with short circuits and current sources with open circuits.

## Norton's theorem

Any two-terminal circuit with only linear elements (resistors) and sources can be replaced by an equivalent circuit consisting of a current source in parallel with a resistor. The current source is written $I_{no}$ and the resistor $R_{no}$.

1. Find $I_{no}$, the short-circuit current from A to B, using KCL and KVL.
2. Find $R_{no}$, the equivalent shunt (parallel with the source) resistance between A and B, by the same replacement of sources as above.

## The two equivalents describe the same circuit

Both procedures compute the resistance the same way, so $R_{no} = R_{th}$. Matching the open-circuit voltage of the two equivalents gives $V_{th} = I_{no} R_{no}$. Converting between the two forms is called a source transformation.

## Related

- [[signal-conditioning/lecture-notes/lecture-3|Resistance]]
- [[signal-conditioning/lecture-notes/lecture-6|Capacitors]]
- [[cheatsheets/circuits/electricity|Electric Circuit Analysis]]
