---
title: Waveform Diagrams
category: Hardware
tags: waveform diagrams, bit vectors, bus, circuit timing behavior
description: Explains the concept of waveform diagrams in digital design, and how to use them to visualize the state of a system.
---

# Waveform Diagrams

Group bits of values into a **bus** or a **bit vector**. You can view the state of your system as slices of a waveform for each bit, corresponding to a number.

## Circuit Timing Behavior

Every gate has some fixed delay. In reality, you can look them up in their data sheet. However, for simplicity assume delay of all gates is 1 ns ( = 3 ticks).

# Verilog stuff

## Verilog bus

Defining them: `[n-1:0]` is an $n$-bit bus. Access with array syntax. Can access sub-bus using `bus[start:size]`.

## Multi-bit constants

`n'b#...#` is a constant with width $n$.

## Concat

 `{A, B, C, ...}`

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


## Test Benches

Create emulated inputs for all of the FPGA's physical connections.

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
