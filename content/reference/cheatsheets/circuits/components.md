---
title: Electronic Components
aliases:
  - cheatsheets/circuits/components
category: Reference
tags:
  - transistors
  - op-amps
  - diodes
  - passive-components
  - amplifiers
date: 2024-03-11
updated: 2026-07-30
status: evergreen
description: Reference for common circuit components, covering sources, resistors, capacitors, inductors, diodes, transistors, and op-amps with their governing equations.
---

Reference for the components that show up in basic circuits, with the equations and mental models I use for each. The analysis techniques live in [[reference/cheatsheets/circuits/electricity|Electric Circuit Analysis]].

## DC Sources

Direct current sources provide a constant voltage or current. Batteries are a common example of a DC voltage source. If you graph the voltage over time, it's a flat line.

Voltage sources supply the required current to maintain a constant voltage, and current sources supply the required voltage to maintain a constant current.

## AC Sources

Alternating current sources provide an oscillating voltage or current over time. The signal oscillates between two peak values, and the distance between them is the **peak-to-peak** voltage ($V_{pp}$) or current ($I_{pp}$). The frequency of oscillation ($f$) is the number of oscillations per second, measured in hertz (Hz), and can also be expressed in radians per second ($\omega$). The average value, or midpoint between the two peaks, is the **DC offset** ($V_{dc}$). The phase shift ($\phi$) offsets the waveform in time relative to a reference.

$$
V(t) = \frac{V_{pp}}{2} \sin(\omega t + \phi) + V_{dc}
$$

$$
I(t) = \frac{I_{pp}}{2} \sin(\omega t + \phi) + I_{dc}
$$

$$
\omega = 2\pi f
$$

## Resistors

Resistors drop the voltage of a circuit branch as current flows through them. Their **resistance** is measured in ohms ($\Omega$), and can be thought of as a hill in the flow of electricity. The voltage drop across a resistor is the product of the current flowing through it and its resistance, which is Ohm's Law.

### Resistors in Series

$$
R_{eq} = \sum_{i=1}^{n} R_i = R_1 + R_2 + \ldots + R_n
$$

### Resistors in Parallel

$$
R_{eq} = (\sum_{i=1}^{n} \frac{1}{R_i})^{-1} = (\frac{1}{R_1} + \frac{1}{R_2} + \ldots + \frac{1}{R_n})^{-1}
$$

## Capacitors

Capacitors store energy in an electric field between two plates. Their **capacitance** ($C$) has units of farads (F). A capacitor charges up to its maximum voltage when connected to a voltage source, and discharges when the source is removed. Treating capacitors as a black box, we can describe their behavior in simple AC circuits using impedance:

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

Inductors store energy in a magnetic field created by a current flowing through a coil of wire. Their **inductance** ($L$) has units of henrys (H). An inductor resists changes in current, and generates a voltage to oppose those changes. Like capacitors, their behavior in AC circuits comes down to impedance:

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

Diodes are one way valves for current, built from a p-n (positive-negative) junction of semiconductor material. Silicon diodes have a built in voltage drop of roughly $0.7$ V, which acts as a threshold that must be overcome before current can flow. Diodes are often used to **rectify** AC signals, removing the negative half of the signal and keeping the positive half. A diode has three regions of operation:

1. **Forward Bias**: The diode is conducting, meaning there is sufficient voltage across the diode to overcome the built in voltage drop. The diode conducts current in the direction of the arrow on its symbol, and acts as a voltage source with a drop of roughly $0.7$ V.
2. **Reverse Bias**: The diode is not conducting because the applied voltage points the opposite direction. The diode acts as an open circuit, and no current flows through it.
3. **Zero Bias**: The diode is not conducting, as there is no voltage across it. This behaves the same as reverse bias with 0 V applied.

## Bipolar Junction Transistors (BJTs)

BJTs let you control one voltage source with another, often smaller, voltage source. They show up in pretty much every electronic device, and are the building blocks of digital logic and amplifiers. They have 3 terminals: the base, collector, and emitter. They come in two flavors: NPN and PNP.

### Terminals

| Terminal | Description |
|----------|-------------|
| Base     | The control terminal, which allows a small current to control a larger current. |
| Collector| The terminal that collects the current from the emitter. |
| Emitter  | The terminal that emits the current to the collector. |

$$
I_E = I_C + I_B = \beta I_B + I_B = (\beta + 1)I_B
$$

Where $\beta$ is the current gain of the transistor. It varies widely between parts, so check the datasheet.

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

The opposite of NPN. Current flows into the emitter, and out of the collector. The base current still controls the collector current, and the transistor conducts when current flows out of the base, which happens when the base sits at a lower voltage than the emitter.

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

MOSFETs have 3 terminals: the gate, drain, and source. They are voltage controlled devices, and like BJTs they appear in pretty much every electronic device. They come in two flavors: N-channel and P-channel, or NMOS and PMOS. The high level function matches a BJT, though the physics underneath differs.

$$
I_D = k (V_{GS} - V_{th})^2
$$

Where $k$ is a constant for that specific MOSFET based on its geometry and material, $V_{GS}$ is the voltage between the gate and source, and $V_{th}$ is the threshold voltage required to turn the MOSFET on. This square law describes the saturation region, the usual operating region for amplification.

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

Op-Amps are voltage amplifiers with 2 input pins and 1 output pin. They have very high gain, and can increase the voltage or current of a signal. They usually rely on feedback loops to control their gain. Op-amps show up in filters, amplifiers, and comparators, and can also perform mathematical operations on signals like addition, integration, and differentiation.

### Rules (ideal negative feedback networks)

Ideal Op-Amps have 3 terminals: the inverting input (-), the non-inverting input (+), and the output. Negative feedback means the inverting input connects to the output, and it's an extremely common configuration. The difference between the two input terminal voltages is amplified, and the circuit behaves according to the following properties:

1. The Op-Amp behaves so as to make the voltage difference between the two input terminals zero. You can think of these two terminals as being shorted together (*virtual short*).
2. No current flows into either of the inputs.

### Non-Ideal Op-Amps

In practice, real Op-Amps have two additional terminals for a positive supply and ground (or negative supply). The output voltage is limited to the range between the positive and negative supply voltages, which also caps the usable gain.

## Related

- [[reference/cheatsheets/circuits/electricity|Electric Circuit Analysis]]
