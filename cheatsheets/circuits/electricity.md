# Electricity Basics

## Flow of Electricity

Electricity, being the flow of electrons, is similar to many other types of flow. For prosperity, engineers use **conventional current**, a bad theory made long ago that positive charges flow from high potential to low potential. In reality, electrons are negatively charged and flow from low potentials to high potentials.

**Potential**? What's that? It's the energy per unit charge at a point in space. It's measured in volts, and is the driving force behind the flow of electricity. From this point on I'll refer to potential as voltage, like a true engineer. 

If you're smooth brained like me, it helps to think of it as similar to potential energy of balls on a track, but for electrons. A higher voltage means the electron has a long way to fall. This model only takes you so far, but it helps as a mental model for characterizing the behavior of electricity.

If potential is the driving factor behind the flow of electricity (like gravity), then **current** is the magnitude of the flow itself (like throughput). It's measured in amperes (A, Amp), which is a compound unit of charge per unit time. 

Finally, **resistance** is the opposition to the flow of electricity. It's measured in ohms ($\Omega$), and can be thought of as anything that drops the voltage (like a hill or friction for potential energy) when current flows through it.


## Short Circuit

A short circuit is just any path with negligible resistance, or ideally zero resistance. Connecting any two points in a circuit with a wire could be call "shorting" them together. Doing this to something like a battery is bad, because a theoretically limitless, but in practice problematic amount of current will flow through a short circuit with a forced voltage drop.

Just "shorting" two points together isn't bad, but they need to be points that are supposed to have the same voltage.

## Open Circuit

Open circuits are the opposite of short circuits. They're non-conducting paths, or ideally infinite resistance. No current can flow through an open circuit, and it is like a gap between two wires in a circuit.

A simple switch will be an open circuit in the off position, and is literally as simple as a gap in the wire that is closed when the switch is flipped.

## Ohm's Law

$$
V = IR
$$

Where $V$ is voltage, $I$ is current, and $R$ is resistance. The amount of voltage we lose *across* a resistor is the product of its resistance and the current flowing through it. This simple linear relationship holds, and can be used any time we need to solve for values directly, or the relationship between them.

## Power

$$
P = IV
$$

$$
P = I^2R
$$

$$
P = \frac{V^2}{R}
$$

Power is the rate at which energy is transferred. It's measured in watts (W), and is the product of voltage and current. It can also be expressed in terms of current and resistance, or voltage and resistance.

Power can either "sink" into a component, or "source" from it. When power is being dissipated, it's a sink. When power is being generated, it's a source. Typically, when current flows out of a component, it's a source, and when current flows into a component, it's a sink. We represent a source with a positive sign, and a sink with a negative sign.

## Kirchoff's Laws

### Kirchoff's Current Law (KCL)

The sum of currents entering a node is equal to the sum of currents leaving a node. Current has to go somewhere (it can't just disappear).

### Kirchoff's Voltage Law (KVL)

The sum of voltages around a loop is equal to zero. This is a consequence of conservation of energy. Easiest to start from **ground**, a reference point with zero voltage, and work your way around the loop right back to any other ground in the circuit to complete the loop.

*Any other ground?* Yes, any other ground. Ground is a reference point, and can be placed anywhere in the circuit. If it helps, you can think of all the grounds as a reference to the same point in space, and the circuit as a series of loops around that point (only for the purpose of KVL analysis).

## Impedance

Impedence ($Z$) is measured in Ohms ($\Omega$), and is basically a generalization of resistance to AC circuits. It is similarly a measure of opposition to flow of electricity, but can be a complex number which results in a phase shift between the voltage and current.

It is convinient to transform sinusoidal AC signals into phasors so you don't need to solve a differential equation. Instead of worrying about the real and imaginary parts of the signal seperately as time varies, we instead transform the signal into a vector rotating with the same angular frequency $\omega$, so we only need to worry about the relative offsets and magnitudes for systems oscillating at a single frequency. The following formulas come in handy:

#### Euler's formula:

$$e^{j\theta} = \cos(\theta) + j\sin(\theta)$$

#### Phasor representation:

$$V(t) = V_m \cos(\omega t + \phi) = V_m \cos(\phi) + jV_m \sin(\phi)$$

$$ = V_m \angle \phi = V_m e^{j\phi}$$

## Series vs. Parallel 

### Series

Connected end to end, so that the current flowing out of one flow into the other. Voltage drops accumulate across each component, and the current is the same through each component.

```plaintext
+---O---O---O---+
```

### Parallel

Connected side by side, on two branches that originate from the same point. The current is split between the two branches.

```plaintext
   +---O---+
   |       |
---+       +---
   |       |
   +---O---+
```