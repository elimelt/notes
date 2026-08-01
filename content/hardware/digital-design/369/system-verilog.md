---
title: SystemVerilog
aliases:
  - hardware-design/369/system-verilog
category: Hardware Design
tags:
  - system-verilog
  - hardware
  - digital electronics
  - hardware description languages
date: 2024-04-02
updated: 2026-07-30
status: evergreen
description: SystemVerilog basics from CSE 369, covering nets and variables, signal values, modules, the hardware execution model, and structural design shown through an AOI circuit and a 2:1 mux.
sources:
  - title: UW CSE 369 lecture notes
    type: lecture
---

## Purpose

Working notes on the SystemVerilog primitives and the structural style used in CSE 369. The examples build the same AND-OR-INVERT circuit three ways, then compose it into a mux.

## What Verilog is

Verilog is a language for describing hardware. You describe the behavior you want programmatically, which lets you test a design in simulation before it ever touches real hardware. The syntax can look like C, but the execution model is different. SystemVerilog is a superset of the older Verilog, and this note says Verilog for both.

## Nets and variables

A net (`wire`) transmits the value of a connected source. Think of it as a split wire, since it can connect to many places. Connecting two different voltage sources to the same net is a problem.

A variable (`reg`) acts as a voltage source you can assign arbitrary values to. `logic` can also be used as a variable.

## Signal values

- `0`: low, treated as false
- `1`: high, treated as true
- `X`: unknown
- `Z`: floating, high impedance

## Modules

Modules are the "classes" of Verilog. They define blocks with a boundary. Inputs are signals passed from outside the block to inside, and outputs are signals passed from inside to outside.

## Execution model

You can't turn wires off. They transmit voltages near instantly, and every gate and module computes constantly, which takes some getting used to if you come from software. Pure hardware also has no notion of initialization. A wire can pick up voltage from its environment before you drive it.

## Structural Verilog

The same AND-OR-INVERT circuit, written three ways. First with a single continuous assignment:

```verilog
// SystemVerilog code for AND-OR-INVERT circuit
module AOI (F, A, B, C, D);
    output logic F;                     // each variable
    input logic A, B, C, D;             // is 1-bit (logic)

    assign F = ~((A & B) | (C & D));    // continuous assignment
endmodule
```

Equivalently with intermediate signals:

```verilog
// SystemVerilog code for AND-OR-INVERT circuit
module AOI (F, A, B, C, D);
    output logic F;
    input logic A, B, C, D;
    logic AB, CD, O; // now necessary

    assign AB = A & B;
    assign CD = C & D;
    assign O = AB | CD;
    assign F = ~O;
endmodule
```

Equivalently with gate primitives:

```verilog
// SystemVerilog code for AND-OR-INVERT circuit
module AOI (F, A, B, C, D);
    output logic F;
    input logic A, B, C, D;
    logic AB, CD, O; // now necessary

    // "and" is the module name. a1 is the instance name.
    // AB, A, B are port connections.
    and a1(AB, A, B);
    and a2(CD, C, D);
    or o1(O, AB, CD);
    not n1(F, O);
endmodule
```

## 2-input MUX from AOI

A 2:1 multiplexer built by instantiating the AOI module above:

```verilog
// 2:1 multiplexer built on top of AOI module
module MUX2 (V, SEL, I, J);
    output logic V;
    input logic SEL, I, J;
    logic SELN, VN;

    not G1 (SELN, SEL);
    // Explicit (named) port assignment, so port
    // order doesn't matter.
    AOI G2 (.F(VN), .A(I), .B(SEL), .C(SELN), .D(J));
    not G3 (V, VN);
endmodule
```

The AOI output is inverted, so `VN` is low when the selected input is high, and the final `not` restores the intended mux output.

## Related

- [[hardware/digital-design/369/combinational-logic|Combinational Logic]]
- [[hardware/digital-design/369/sequential-logic|Sequential Logic]]
- [[hardware/digital-design/369/quartus-workflow|the Quartus and ModelSim workflow]]
- [[hardware/computer-architecture/rtl-reading-lab|Open-Source CPU RTL Reading Lab]]
