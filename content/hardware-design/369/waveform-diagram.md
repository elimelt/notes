---
title: Waveform Diagrams
category: Hardware
tags:
  - waveform diagrams
  - bit vectors
  - bus
  - circuit timing behavior
date: 2024-04-03
updated: 2026-07-30
status: draft
description: Reading waveform diagrams and bus values over time, plus the Verilog syntax for buses, multi-bit constants, concatenation, and test benches.
sources:
  - title: UW CSE 369 lecture notes
    type: lecture
---

## Purpose

Notes on reading waveform diagrams, along with the Verilog syntax from the same lecture for buses, constants, concatenation, and test benches.

## Buses and waveforms

Group related bits into a **bus**, also called a **bit vector**. A waveform diagram shows each signal's value over time. Slice the diagram at any time point and you get the full state of the system, with each bus's bits at that slice reading as a number.

## Circuit timing behavior

Every gate has some fixed delay. In reality you look delays up in the part's data sheet. For hand analysis in this course, assume every gate has a delay of 1 ns, which corresponds to 3 simulation ticks.

## Verilog buses

`[n-1:0]` declares an $n$-bit bus. Access individual bits with array syntax, and take a slice of the bus with `bus[msb:lsb]`.

```verilog
// SystemVerilog code for AND-OR-INVERT circuit
module AOI (F, A, B, C, D);
    output logic F;
    input logic A, B, C, D;
    logic [2:0] w; // necessary
    assign w[0] = A & B;
    assign w[1] = C & D;
    assign w[2] = w[0] | w[1];
    assign F = ~w[2];
endmodule
```

## Multi-bit constants

`n'b#...#` is a binary constant with width $n$. [[hardware-design/371/verilog-review|SystemVerilog Review]] covers the full constant syntax, including other radixes.

## Concatenation

`{A, B, C, ...}` concatenates signals into one wider value.

## Test benches

A test bench creates emulated inputs for all of the FPGA's physical connections, then drives them through a stimulus sequence:

```verilog
module MUX2_tb ();
    logic SEL, I, J; // simulated inputs
    logic V; // net for reading output

    // instance of module we want to test ("device under test")
    MUX2 dut (.V(V), .SEL(SEL), .I(I), .J(J));

    initial // build stimulus (test vectors)
    begin // start of "block" of code
      {SEL, I, J} = 3'b100; #10; // t=0: S=1, I=0, J=0 -> V=0
      I = 1; #10; // t=10: S=1, I=1, J=0 -> V=1
      SEL = 0; #10; // t=20: S=0, I=1, J=0 -> V=0
      J = 1; #10; // t=30: S=0, I=1, J=1 -> V=1
      end // end of "block" of code
endmodule // MUX2_tb
```

## Related

- [[hardware-design/371/static-timing-analysis|Static Timing Analysis]]
- [[hardware-design/369/quartus-workflow|the Quartus and ModelSim workflow]]
- [[hardware-design/369/system-verilog|SystemVerilog]]
