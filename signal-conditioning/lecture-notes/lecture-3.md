# Lecture 3

## Resistance

Resistance is the opposition to the flow of current. It is measured in Ohms (`\Omega`), and is the ratio of voltage to current. Is usually an intrinsic property of the material.

#### Ohm's Law
$$V = IR$$

## Power

The rate of change of energy, measured in Joules/sec -> Watts (W)

$$1$$

#### Power and Resistance

The power dissipated by a resistor is the product of the voltage across it and the current through it. Intuitively, this makes sense because it takes energy to push electrons through a resistor, and the more electrons you push through, the more energy you use. Similarly, holding I constant, the power is directly proportional to the resistance. 

$ P = IV = I^2R = V^2/R $

## Resistors in Series and Parallel

#### Series

Resistors in series are connected end-to-end. The total resistance is the sum of the individual resistances.

$$R_t = R_1 + R_2 + \ldots + R_n$$

The current through each resistor is the same because the current is the flow of electrons, and the electrons can't go anywhere else. 

The voltage across each resistor can be different, but the total voltage is the sum of all the voltages across each resistor. This can be derived from the above two properties and Ohm's law.

$$V_t = V_1 + V_2 + \ldots + V_n$$

$$V_t = IR_t = I(R_1 + R_2 + \ldots + R_n) = IR_1 + IR_2 + \ldots + IR_n = V_1 + V_2 + \ldots + V_n$$



#### Parallel

Connected such that both ends of each resistor are connected to the same two points of the circuit. The resistance of the circuit is the reciprocal of the sum of the reciprocals of the individual resistances.

$$R_t = 1/(1/R_1 + 1/R_2 + \ldots + 1/R_n)$$

The voltage across each resistor is the same because the voltage is the difference in potential between two points, and the two points are the same for each resistor (equal to the source voltage).

The current through each resistor can be different, but the total current from the two endpoints is the sum of all the currents through each resistor. This can be derived from the above two properties and Ohm's law, but also from the fact that the current is the flow of electrons, and the electrons can't go anywhere else.


$$I_t = I_1 + I_2 + \ldots + I_n$$

$$I_t = V_t/R_t = V_t/(1/(1/R_1 + 1/R_2 + \ldots + 1/R_n)) = V_t/(R_1 + R_2 + \ldots + R_n) = V_t/R_1 + V_t/R_2 + \ldots + V_t/R_n = I_1 + I_2 + \ldots + I_n$$



