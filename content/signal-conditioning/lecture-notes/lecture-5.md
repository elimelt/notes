---
title: Thevenin's Theorem
category: Algorithms
tags: Thevenin's Theorem, Norton's Theorem, Equivalent Circuit, Resistor, Voltage Source, Current Source, Kirchhoff's Laws
description: Covers the implementation of Thevenin's and Norton's Theorems, which are fundamental techniques for analyzing electrical circuits. Describes how to derive the Thevenin and Norton equivalent circuits, consisting of a voltage source and series resistor, or a current source and parallel resistor, respectively. Discusses the application of Kirchhoff's laws and the use of these theorems to simplify complex circuits into an equivalent form for further analysis.
---

## Thevenin's Theorem

Any two-terminal circuit with only linear elements (resistors) and sources can be replaced by an equivalent circuit consisting of a voltage source in series with a resistor.

Voltage source represented as $V_{th}$, and resistor as $R_{th}$.

### Algorithm

1. Find $V_{th}$, the open circuit voltage from A to B using KCL and KVL.
2. Find $R_{th}$, the equiv resistance between A and B by replacing voltage sources with short circuits and current sources with open circuits.

## Norton's Theorem

Any two-terminal circuit with only linear elements (resistors) and sources can be replaced by an equivalent circuit consisting of a current source in parallel with a resistor.

Current source represented as $I_{no}$, and resistor as $R_{no}$.

### Algorithm
1. find $I_{no}$, the short circuit current from A to B using KCL and KVL.
2. find $R_{no}$, the equiv shunt (parallel with source) resistance between A and B by replacing voltage sources with short circuits and current sources with open circuits.

