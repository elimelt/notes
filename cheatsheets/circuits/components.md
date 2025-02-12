---
title: Electronic Components
category: Hardware
tags: Transistors, Op-Amps, Filters, Amplifiers, Comparators
description: A comprehensive overview of electronic components used in electronics devices, including Transistors, Op-Amps, Filters, Amplifiers, and Comparators.
---

# Component Dictionary

## DC Sources

Direct current sources are sources that provide a constant voltage or current. Batteries are a common example of a DC voltage source. If you graph the voltage over time, it's a flat line.

Voltage sources supply the required current to maintain a constant voltage, and current sources supply the required voltage to maintain a constant current.

## AC Sources

Alternating current sources provide an oscillating voltage or current over time. The voltage or current will oscillate between the two peek values, the distance between them being referred to as the **peak-to-peak** voltage ($V_{pp}) or current ($I_{pp}$). The frequency of oscillation ($f$) is the number of oscillations per second, and is measured in hertz (Hz), but can also be represented in radians per second ($\omega$). The average value, or mid point between the two peek values, is referred to as the **DC offset** ($V_{dc}). Finally, the phase shift ($\phi$) is the amount of time shift between the voltage and current oscillations.

$$
V(t) = \frac{V_{pp}}{2} \sin(\omega t + \phi) + V_{dc}
$$

$$
I(t) = \frac{I_{pp}}{2} \sin(\omega t + \phi) + I_{dc}
$$

$$
\omega (rad/s) = 2\pi f (Hz)
$$

## Resistors

Resistors are simple components that drop the voltage of a circuit branch as current flows through them. Their **resistance** measured in ohms ($\Omega$), and can be thought of as a hill in the flow of electricity. The voltage drop across a resistor is the product of the current flowing through it and its resistance AKA Ohm's Law.

### Resistors in Series

$$
R_{eq} = \sum_{i=1}^{n} R_i = R_1 + R_2 + \ldots + R_n
$$

### Resistors in Parallel

$$
R_{eq} = (\sum_{i=1}^{n} \frac{1}{R_i})^{-1} = (\frac{1}{R_1} + \frac{1}{R_2} + \ldots + \frac{1}{R_n})^{-1}
$$

## Capacitors

Capacitors store energy in an electric field between two plates. They're measured in capacitance ($C$), which has units of farads (F). A capacitor will charge up to its maximum voltage when connected to a voltage source, and will discharge when the source is removed. Treating capacitors as a black box (even though they are relatively simple), we can describe their behavior in simple AC circuits using impedance:

$$
Z_C = \frac{1}{j\omega C} = \frac{-j}{\omega C}
$$

### Capacitors in Series

$$
C_{eq} = (\sum_{i=1}^{n} \frac{1}{C_i})^{-1} = (\frac{1}{C_1} + \frac{1}{C_2} + \ldots + \frac{1}{C_n})^{-1}
$$

### Capacitors in Parallel

$$
C_{eq} = \sum_{i=1}^{n} C_i = C_1 + C_2 + \ldots + C_n
$$

*Note: combining capacitors behaves opposite to resistors.*

## Inductors

Inductors store energy in a magnetic field created by a current flowing through a coil of wire. They're measured in inductance ($L$), which has units of henrys (H). An inductor will resist changes in current, and will generate a voltage to oppose changes in current. Treating inductors as a black box (even though they are also pretty simple), we can once again describe their behavior with impedance:

$$
Z_L = j\omega L
$$

### Inductors in Series

$$
L_{eq} = \sum_{i=1}^{n} L_i = L_1 + L_2 + \ldots + L_n
$$

### Inductors in Parallel

$$
L_{eq} = (\sum_{i=1}^{n} \frac{1}{L_i})^{-1} = (\frac{1}{L_1} + \frac{1}{L_2} + \ldots + \frac{1}{L_n})^{-1}
$$

*Note: just like resistors!*

## Diodes

Diodes are one way valves for current, built by sandwiching a p-n (positive-negative) junction between two  semiconductors. Diodes have a built in voltage drop ($\approx 0.7$ V), which can be thought of as a threshold voltage that must be overcome before current can flow through the diode. Diodes are often used to **rectify** AC signals, whereby the negative half of the signal is removed, and the positive half is preserved. There are 2 main regions of operation for a diode:

1. **Forward Bias**: The diode is conducting, meaning there is sufficient voltage across the diode to overcome the built in voltage drop. The diode will conduct current in the direction of the arrow on the diode symbol, and acts as a voltage source with a drop of $ \approx 0.7$ V.
2. **Reverse Bias**: The diode is not conducting due to a voltage applied in the opposite direction (can think about it as the current "trying" to flow through it). The diode acts as an open circuit, and no current will flow through it.
3. **Zero Bias**: The diode is not conducting, as there is no voltage across the diode. This is the same as reverse bias, but the voltage is 0 V.

## Bipolar Junction Transistors (BJTs)

BJTs are devices that allow you to control one voltage source with another (often) smaller voltage source. They are used in pretty much every electronic device, and are the building blocks of digital logic and amplifiers. They have 3 terminals: the base, collector, and emitter. They come in two flavors: NPN and PNP.

### Terminals

| Terminal | Description |
|----------|-------------|
| Base     | The control terminal, which allows a small current to control a larger current. |
| Collector| The terminal that collects the current from the emitter. |
| Emitter  | The terminal that emits the current to the collector. |

$$
I_E = I_C + I_B = \beta I_B + I_B = (\beta + 1)I_B
$$

Where $\beta$ is the current gain of the transistor, and is typically around $20$ to $100$.

### NPN

Current flows into the collector, and out of the emitter. The base current controls the collector current. If the base current is zero, the collector current is zero, and if the base current is at its maximum, the collector current is at its maximum.

```plaintext
       C
       |
      /
B --|<
      \
       |  | Ic
       E  v
```

$$
I_c = \beta I_b
$$

### PNP

The opposite of NPN. Current flows into the emitter, and out of the collector. The base current controls the collector current, such that if the base current is zero, the

```plaintext
       E
       |
      /
B --|<
      \
       |  | Ic
       C  v
```

## Metal Oxide Semiconductor Field Effect Transistors (MOSFETs)

Has 3 terminals: the gate, drain, and source. They are voltage controlled devices, and are used in pretty much every electronic device. They come in two flavors: N-channel and P-channel, or NMOS and PMOS. The high level function is the same as a BJT, but the way they work is different.

$$
I_D = k (V_{GS} - V_{th})^2
$$

Where $k$ is a constant for that specific MOSFET based on its geometry and material, $V_GS$ is the voltage between the gate and source, and $V_{th}$ is the threshold voltage, which is the voltage required to turn the MOSFET on.

### Terminals

| Terminal | Description |
|----------|-------------|
| Gate     | The control terminal, which allows a voltage to control the current between the drain and source. |
| Source | The input terminal for current. |
| Drain  | The output terminal for current. |


### NMOS

When the gate voltage is *high*, the MOSFET is on and current flows from the drain to the source. When the gate voltage is *low*, the MOSFET is off and no current flows.

### PMOS

When the gate voltage is *low*, the MOSFET is on and current flows from the drain to the source. When the gate voltage is *high*, the MOSFET is off and no current flows.

PMOS are drawn with a circle on the gate terminal to indicate that the gate voltage is inverted.

## Operational Amplifiers (Op-Amps)

Op-Amps are voltage amplifiers with 2 input pins and 1 output pin. They typically have very high gain, and can be used to increase the voltage or current of a signal. They often use feedback loops to control their gain, and can be used to perform a variety of operations on signals. They are often used in filters, amplifiers, and comparators, but can also be used to perform mathematical operations on signals (like addition, integration, and differentiation).

### Rules (ideal negative feedback networks)

Ideal Op-Amps have 3 terminals: the inverting input (-), the non-inverting input (+), and the output. Negative feedback is when the inverting input is connected to the output, and is an extremely common configuration. The difference between the two input terminal voltages is amplified, and the circuit behaves according to the following properties:

1. The Op-Amp behaves so as to make the voltage difference between the two input terminals zero. You can think of these two terminals as being shorted together (*virtual short*).
2. No current flows into either of the inputs

### Non-Ideal Op-Amps

In practice, real Op-Amps have two additional terminals for a positive supply and ground (or negative supply). The output voltage is limited to the range between the positive and negative supply voltages. The gain is limited by this maximum output voltage.