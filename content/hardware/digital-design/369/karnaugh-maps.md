---
title: Karnaugh Maps
aliases:
  - hardware-design/369/karnaugh-maps
category: Hardware Design
tags:
  - karnaugh maps
  - truth tables
  - boolean minimization
date: 2024-04-14
updated: 2026-07-30
status: draft
description: How to build a K-map from a truth table and group 1s to minimize a boolean expression, plus notes on Verilog procedural blocks from the same lecture.
sources:
  - title: UW CSE 369 lecture notes
    type: lecture
---

## Purpose

K-maps give a visual way to minimize boolean expressions. The goal is to find neighboring subsets of the on set so you can eliminate variables from the expression.

## Building and reading a K-map

A K-map redraws a truth table as a grid where adjacent cells differ in exactly one variable. That layout makes adjacencies visible for functions of up to about 4 variables.

1. Split the inputs into two evenly sized groups.
2. Draw a grid with the two groups as the axes, yielding $2^n$ cells for $n$ inputs.
3. Fill in each cell from the truth table.
4. Group the 1s into rectangles whose sizes are powers of two. Groups can span both axes and can wrap around the edges of the map.
5. Group any leftover 1s with adjacent 1s where possible.

> [!tip] Label the axes in Gray code
> Order each axis 00, 01, 11, 10 rather than counting in binary. Gray code ordering changes exactly one variable between neighboring rows and columns, which is what makes cells that touch on the grid actual logical neighbors. Binary ordering (00, 01, 10, 11) breaks that property between 01 and 10, and every grouping you read off the map after that is suspect.

A group of size $2^k$ covers cells that agree on all but $k$ of the variables, so its product term drops those $k$ variables. Bigger groups mean simpler terms, which is why you want the largest power-of-two groupings you can find.

> [!warning] The map wraps around
> Cells on opposite edges are adjacent. The leftmost and rightmost columns differ in one variable, and so do the top and bottom rows, so a group can span the edge of the map. In a 4-variable map the four corners form a legal group of 4. Missing a wrap-around group leaves an unnecessarily large expression even though every grouping you did find is correct.

## Verilog procedural blocks

This came up in lab while building a 7-segment display driver.

- `assign` is continuous assignment. The statement holds for all time.
- `initial` executes once at time zero. It only belongs in test benches, since time zero is a simulation concept with no hardware meaning.
- `always` re-executes whenever a signal in its *sensitivity list* changes. Any object assigned inside an `always` block must be declared as a variable (`reg` or `logic`). Writing `always @ (a or b or c)` is the same as `always @ (a, b, c)`, and `always @ (*)` implicitly includes every signal the block reads.
- `always_comb` is the SystemVerilog form of `always @ (*)`. It infers the sensitivity list from the signals read in the block and tells the tools you intend combinational logic.

## Related

- [[hardware/digital-design/369/combinational-logic|Combinational Logic]]
- [[hardware/digital-design/369/system-verilog|SystemVerilog]]
