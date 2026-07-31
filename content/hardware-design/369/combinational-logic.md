---
title: Combinational Logic
category: Hardware
tags:
  - combinational logic
  - sequential logic
  - boolean algebra
  - logic gates
  - minimization
date: 2024-03-29
updated: 2026-07-30
status: evergreen
description: Defines combinational logic, shows how to read boolean expressions out of truth tables, and collects the identities and gate costs that drive logic minimization.
sources:
  - title: UW CSE 369 lecture notes
    type: lecture
---

## Purpose

Pin down what makes a circuit combinational, and collect the tools for turning a truth table into a small boolean expression. Smaller expressions mean fewer transistors and less delay, so minimization is where most of this note goes.

## Combinational vs. sequential

The output of combinational logic depends only on the current input. There is no feedback, so the circuit holds no state. Multiplexers, decoders, and adders all work this way. Sequential logic adds feedback, so its output depends on the current input and on stored state. See [[hardware-design/369/sequential-logic|Sequential Logic]] for that side.

## Representation

The same logic can be written as text, a circuit, a truth table, or an equation. Take a car's warning lights. The door is ajar if the driver door is open or the passenger door is open:

```plaintext
DoorAjar = DriverDoorOpen OR PassengerDoorOpen
```

The seat belt light is on if the driver's belt is unfastened, or if a passenger is present with their belt unfastened:

```plaintext
SeatBeltLight = (NOT DriverSeatBeltFastened) OR (NOT PassengerSeatBeltFastened AND PassengerPresent)
```

## Truth table to boolean expression

Sum of products: for each row where the output is 1, AND the inputs together, complementing any input that is 0 in that row. OR all of those product terms.

Product of sums: for each row where the output is 0, OR the inputs together, complementing any input that is 1 in that row. AND all of those sum terms.

## Boolean identities

| Identity | Description |
|----------|-------------|
| `A + 0 = A` | Identity |
| `A + A = A` | Idempotent |
| `A + 1 = 1` | Annihilation |
| `A + A' = 1` | Complement |
| `A + B = B + A` | Commutative |
| `A + (B + C) = (A + B) + C` | Associative |
| `A(B + C) = AB + AC` | Distributive |
| `A + AB = A` | Absorption |

## Logic minimization

Reducing complexity at the gate level buys smaller and faster hardware. The things worth counting:

- Number of gates. Fewer gates means less area.
- Number of literals (gate inputs). Fewer literals means less wiring.
- Number of levels. Fewer levels means a shorter critical path and fewer dependencies.
- Types of gates. Some gates cost fewer transistors than others.

Simpler boolean expressions generally map to smaller transistor networks, which means smaller circuit delays. CMOS transistor counts per gate, from lecture:

| Type | CMOS transistors required |
|------|---------------------------|
| NOT | 2 |
| AND | 6 |
| OR | 6 |
| NAND | 4 |
| NOR | 4 |
| XOR | 8 |
| XNOR | 8 |

NAND and NOR are universal gates. You can build every other gate type from just one of them. For example, AND is a NAND followed by an inverter, and the inverter itself is a NAND with both inputs tied together. The table above also explains why NAND-based implementations are attractive, since NAND costs 4 transistors while AND costs 6.

## DeMorgan's law

$$
\overline{A \cdot B} = \overline{A} + \overline{B}
$$

$$
\overline{A + B} = \overline{A} \cdot \overline{B}
$$

In a circuit, the general rule for applying DeMorgan's law to an AND or OR gate with some inverted terminals is to swap the gate type (AND becomes OR, OR becomes AND) and toggle the inversion on every terminal, so inverted points become plain and plain points become inverted.

## Related

- [[hardware-design/369/karnaugh-maps|Karnaugh Maps]]
- [[hardware-design/369/sequential-logic|Sequential Logic]]
- [[hardware-design/369/system-verilog|SystemVerilog]]
