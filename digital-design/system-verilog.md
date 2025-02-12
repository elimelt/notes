---
title: SystemVerilog
category: hardware
tags: system-verilog, hardware, digital electronics, programming languages for hardware
description: Programming language for describing hardware behavior, including modules, primitives, execution, and structural representation
---

# SystemVerilog

## Verilog

A programming language for describing hardware. Lets you programmatically describe the behavior you want, giving you the ability to test things beforehand with simulation. Help prevents hurting your hardware.

Syntax can be similar to C, but behavior is different. SystemVerilog is a superset of the older Verilog. Will refer to SV as Verilog.

## Primitives

### Nets (`wire`): transmit value of a connected source.
- It is problematic to have two different voltage sources connected.
- Can connect to many places. Think about like a split wire.

### Variables (`reg`): variable Voltage source.
- Can assign arbitrary values.
- Variable `logic` can be used as a variable as well.

### Values
- 0: low, TRUE
- 1: high, FALSE
- X: unknown
- Z: floating, high impedance


### Modules

- Modules: "classes" in Verilog that define blocks
- Input: Signals passed from outside to inside of block
- Output: Signals passed from inside to outside of block

## Execution

You can't turn wires off. They transmit voltages near instantly. Gates and modules are constantly performing computation, which can be hard to keep track of.

In pure hardware, there is no notion of initialization. Wires can naturally pick up voltages from their enviornment.


## Structural Verilog

```sv
// SystemVerilog code for AND-OR-INVERT circuit
module AOI (F, A, B, C, D);
    output logic F;                     // each variable
    input logic A, B, C, D;             // is 1-bit (logic)
    
    assign F = ~((A & B) | (C & D));    // continuous assignment
endmodule
// end of SystemVerilog code
```

### Equivalently with wires

```sv
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

### Equivalently with gates

```sv
// SystemVerilog code for AND-OR-INVERT circuit
module AOI (F, A, B, C, D);
    output logic F;
    input logic A, B, C, D;
    logic AB, CD, O; // now necessary
    
    // and is the module name. a1 is the instance name
    // AB, A, B are port connections
    and a1(AB, A, B);
    and a2(CD, C, D);
    or o1(O, AB, CD);
    not n1(F, O);
endmodule
```

## 2-input MUX
```sv
// SystemVerilog code for AND-OR-INVERT circuit
module AOI (F, A, B, C, D);
    output logic F;
    input logic A, B, C, D;

    assign F = ~((A & B)|(C & D));
endmodule
```

```sv
// 2:1 multiplexer built on top of AOI module
module MUX2 (V, SEL, I, J);
    output logic V;
    input logic SEL, I, J;
    logic SELN, VN;

    not G1 (SELN, SEL);
    // order of ports matter. this is explicit
    // port assignment
    AOI G2 (.F(VN), .A(I), .B(SEL), .C(SELN), .D(J));
    not G3 (V, VN);
endmodule
```
