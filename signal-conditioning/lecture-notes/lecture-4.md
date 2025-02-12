---
title: Power Dissipation In a Resistor
category: Systems
tags: power dissipation, resistor, kvl, voltage source, current source
description: Covers the power dissipation in a resistor, including the application of Kirchhoff's Voltage Law (KVL) to analyze the behavior of resistors connected to voltage and current sources. Provides a detailed example circuit and discusses the key concepts of power dissipation, voltage, and current in resistive circuits.
---

# Lecture 4

## Power Dissipation In a Resistor

When a resistor starts getting warm, it is leaking power.

```math
P = V * I = I^2 * R = V^2/R
```

## KVL

Voltage: The sum of all the voltages on any path around a circuit are equal to zero.

Current: The current arriving at any node is the same as the current leaving that node.

## Example

```
      R_1 = 1 Ohm
  +--/\/\/|--+
  |          |
  _          |
  + 120 V    |
  -          |
  |          |
  +--\/\/\|--+
      R_2 = 10 Ohm
```

$$V_1 = I * R_1$$
$$V_2 = I * R_2$$

Need $P_2$ using $V/R$

$$P_1 = I^2 * R$$

$$V_L = V * R_2 / (R_ 1 + R_2) = 120 * 10/11 = 109 V$$

$$P_2 = V^2/R = (109)^2/10 = 1188 W$$

$$I_1 = V_1 / R_1 = (V - V_L) / R_1$$

$$= (120 - 109) / 1 = 11 A$$

$$P_1 = I_1^2 *  R_1 = 11^2 * 1 = 121 W$$


## Sources
A voltage source produces a *constant* voltage, regardless of current (an idealistic assumption).

A current source delivers *constant* current to a circuit. Current by load resistance (impedence)



## Situation

We previously estimated an iPhone in standby draws a current of 7.55 mA from its 3.8 V Lithium battery. 


## Circuit

```txt

ground
  ^
  |     battery
  |       |
  |       |
  +----- |-  +|-----+ 
  |                 | 
  |                 | 
  +-----|/\/\/|-----+
           |
           | 
 phone power consumption

```
