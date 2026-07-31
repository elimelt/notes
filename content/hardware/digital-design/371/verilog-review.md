---
title: SystemVerilog Review
aliases:
  - hardware-design/371/verilog-review
category: Hardware Design
tags:
  - systemverilog
  - review
  - combinational logic
  - sequential logic
  - fsm
  - test benches
date: 2025-04-03
updated: 2026-07-30
status: evergreen
description: SystemVerilog review for EE271/CSE371 Spring 2025, covering basic concepts for combinational and sequential logic, FSMs, and test benches.
sources:
  - title: UW CSE/EE 371 review material, Spring 2025
    type: lecture
---

## Purpose

Review sheet for the SystemVerilog assumed going into EE 271/CSE 371. It stays terse on purpose. [[hardware/digital-design/369/system-verilog|SystemVerilog]] has fuller explanations of the basics.

## Integer representation

- **Unsigned integers**: Standard binary (base 2) representation
  - With $n$ bits, can represent integers $0$ to $2^n - 1$
- **Signed integers**: Two's Complement representation
  - Most significant bit (MSB) has negative weight $(-2^{(n-1)})$
  - With $n$ bits, can represent integers $-2^{(n-1)}$ to $2^{(n-1)} - 1$
  - MSB functions as sign bit (0 = positive, 1 = negative)
  - Negation: Bitwise complement + 1 (e.g., `~x + 1`)

## Constants and data types

- Multi-bit constants format: `<n>'<s><b>#...#`
  - `<n>` = width (unsized by default)
  - `<s>` = signed designation (omit or 's')
  - `<b>` = radix/base (d=decimal, h=hex, b=binary, o=octal)
  - Case-insensitive, underscores allowed for readability

## Operators

- Arithmetic: `+`, `-`, `*`, `/`, `%` (modulus), `**` (exponentiation)
- Shift: `>>`, `<<`, `>>>` (arithmetic right shift)
- Relational: `>`, `<`, `>=`, `<=`
- Equality: `==`, `!=`, `===` (case equality)
- Bitwise: `~`, `&`, `|`, `^`
- Logical: `!`, `&&`, `||`
- Ternary operator: `select ? <then_expr> : <else_expr>`

## Bit manipulation

- Concatenation: `{sig, ..., sig}`
- Replication: `{n{m}}` (repeats value m, n times)

## Parameters

- Named constants with default values
- Format for parameterized modules:
  - `module <name> #(<parameter list>) (<port list>);`
  - Example: `#(parameter N = 8)`

## Modules and instantiation

- Modules are the building blocks of design hierarchy
- Ports define connections between module and environment
- Port direction: `input`, `output`, `inout`
- Module instantiation: `<type> <name> (<port connections>);`
- Connection styles:
  1. Positional: `my_tri(out, in, enable);`
  2. Named/explicit: `my_tri(.out(out), .in(in), .enable(enable));`
  3. Implicit: `my_tri(.out, .in, .enable);` (when port/signal names match)

## Procedural blocks

- **Always blocks**: Used for behavioral code, run repeatedly based on sensitivity list
- SystemVerilog variants:
  - `always_comb`: For combinational logic (auto sensitivity list)
  - `always_latch`: For latch-based logic (auto sensitivity list)
  - `always_ff`: For sequential/clocked logic (must specify sensitivity)
- **Initial blocks**: Run once at time zero (for simulation/test benches only)

## Latches vs. flip-flops

- Both store information, but operate differently:
  - Latches are asynchronous (level-sensitive)
  - Flip-flops are edge-triggered (synchronous)
- Beware of inadvertent latches from incomplete assignments

## Case statements

- Create combinational logic inside always blocks
- Must include `default` case to avoid incomplete assignments
- Each case has an implied break

## Finite State Machines (FSMs)

- A way to conceptualize computation over time using state transition diagrams
- Components:
  1. State register (sequential logic)
  2. Next state logic (combinational)
  3. Output logic (combinational)
- Implementation notes:
  - States require binary encoding (use enum for readability)
  - Reset can be synchronous or asynchronous
  - State logic can be one combined block or two separate blocks

### Moore vs. Mealy FSMs

- **Moore**: Outputs depend only on current state
  - Output changes synchronously with state changes
- **Mealy**: Outputs depend on state and inputs
  - Input changes can cause immediate output changes

## Test benches

- Special modules for simulation only
- Create simulated inputs for FPGA testing
- Control timing of signals using:
  - Delay: `#<time>`
  - Edge-sensitive: `@(<pos/neg>edge <signal>)`
  - Level-sensitive: `wait(<expression>)`
- Output test results using `$display` and related system tasks
- Format specifiers for output: `%h` (hex), `%d` (decimal), `%b` (binary), etc.

## Related

- [[hardware/digital-design/369/system-verilog|SystemVerilog]]
- [[hardware/digital-design/371/algorithmic-state-machines|Algorithmic State Machines]]
