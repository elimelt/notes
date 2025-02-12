---
title: Combinational Logic
category: hardware
tags: combinational logic, sequential logic, boolean algebra, logic gates, minimization
description: Explains the concept of combinatorial logic, its differences with sequential logic, and various techniques for minimizing boolean expressions.
---

# Combinational Logic

## Combinational Logic vs. Sequential Logic

- **Combinational Logic**:
  - Output depends only on the current input.
  - No feedback.
  - Examples: Multiplexers, decoders, adders, etc.
- **Sequential Logic**:
    - Output depends on the current input and the state of the circuit.


## Representation

Can represent logic with text, circuits, truth tables, or equations.

For example:

Door is ajar if driver door is open OR passenger door is open.

```plaintext```
DoorAjar = DriverDoorOpen OR PassengerDoorOpen
```
Seat belt light is on if driver seat belt is not fastened OR passenger seat belt is not fastened AND the passenger is present.

```plaintext```
SeatBeltLight = (NOT DriverSeatBeltFastened) OR (NOT PassengerSeatBeltFastened AND PassengerPresent)
```

## Translating Truth Table to Boolean Expressions

- **Sum of products**: Take the rows where the output is 1 and OR the inputs.
- **Product of sums**: Take the rows where the output is 0 and AND the complements of the inputs.




## Boolean Identities

| Identity | Description |
|----------|-------------|
| `A + 0 = A` | Identity |
| `A + A = A` | Idempotent |
| `A + 1 = 1` | Identity |
| `A + A' = 1` | Complement |
| `A + B = B + A` | Commutative |
| `A + (B + C) = (A + B) + C` | Associative |
| `A(B + C) = AB + AC` | Distributive |
| `A + AB = A` | Absorption |

## Logic Minimalization

It is nice to reduce complexity at the gate level. This allows us to build smaller and faster hardware. We care about...

- number of gates: fewer gates is better
- number of literals (gate inputs): fewer literals is better
- number of levels: able to parallelize better using fewer levels/depenencies
- types of logic gates: some gates are faster than others

Generally, simpler boolean expressions lead to smaller transistor networks, and smaller circuit delays/faster hardware.

| Type | CMOS required |
|------|----------------|
| NOT | 2 |
| AND | 6 |
| OR | 6 |
| NAND | 4 |
| NOR | 4 |
| XOR | 8 |
| XNOR | 8 |

You can recreate EVERY gate type using just NAND and NOR (universal gates). e.g. `AND = NAND(NAND(A, B))`


## DeMorgan's Law

```plaintext
NOT(A AND B) = NOT(A) OR NOT(B)
NOT(A OR B) = NOT(A) AND NOT(B)
```

$$
\overline{A \cdot B} = \overline{A} + \overline{B}
$$

$$
\overline{A + B} = \overline{A} \cdot \overline{B}
$$

In a circuit, the more general rule is that if you have an AND or OR gate with some inverted terminals, to apply demorgans law, you just change the type of gate (ie AND to OR or OR to AND) and invert the inputs (ie change all the points that are inverted to not inverted and vice versa).
