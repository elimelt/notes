---
title: Karnaugh Maps
category: Hardware
tags: karnaugh maps, truth tables, graph theory, computer science
description: Method for simplifying Boolean expressions
---

# Karnaugh Maps

Goal: Find neighboring subsets of the On set to eliminate variables and simplify expressions.

A `K-map` is a method of representing a truth table to help visualize adjacencies into $\le$ 4 dimensions.

1. Split inputs into 2 evenly sized groups
2. Draw a grid with the 2 groups as the axes, yielding $2^n$ cells.
3. Number cells based on truth table
4. Group 1s in powers of two (can be in multiple dimensions, and also wraps around the map).
5. Left over 1s are corner cases and should be grouped with any adjacent 1s if possible.


## 7 Segment Display in Verilog

### Procedural Blocks

- `assign`: continuous assignment. Statement should hold true for ALL time
- `initial`: executes once at time zero. Only exists in test benches (since t = 0 isn't real)
- `always`: loop to execute over and over again.
  - Block gets triggered by *sensitivity list* (list of signals that trigger the block)
  - Any object that is assigned a value in an `always` statement must be declared as a variable (`reg/logic`).
  - EX:
    - `always @ (a or b or c) <-> always @ (a, b, c)`
    - `always @ (*)` implicitly contains all read signals within a block
  - `always_comb`: like `always @ (*)`, but only triggered when any of the signals change.


