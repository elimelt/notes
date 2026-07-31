---
title: Electricity
category: Hardware
tags:
  - electricity
  - current
  - voltage
  - power
  - alternating current
  - direct current
  - coulomb
date: 2024-01-05
updated: 2026-07-30
status: evergreen
description: Lecture 2 notes defining current, charge, energy, and power, with unit prefixes, the AC/DC distinction, and worked problems on battery energy and average power.
sources:
  - title: Signal conditioning course, lecture 2
    type: lecture
---

## Purpose

The basic electrical quantities from lecture 2, plus worked problems that turn battery specs into energy and average power.

## The water analogy

A battery driving a light bulb behaves like a pump pushing water through a pipe:

```txt
+-------------+------+----------+
|1.5 V Battery|      |Light Bulb|
+-------------+------+----------+
        current: I ->
```

Current is the amount of water flowing through the pipe, and voltage is the water pressure. If the "pressure" were 0, the "flow" would be 0, and the same holds for electrons. The battery uses its chemical potential energy to push electrons through the circuit, creating a current.

## Definitions

**Current** ($I$) is the rate of flow of electrons, measured in Amperes (A). One amp is a flow of 1 Coulomb of charge per second.

The **Coulomb** is the unit of charge $Q$. One Coulomb is about $6.24 \times 10^{18}$ electrons, which follows from the elementary charge of $1.602 \times 10^{-19}$ C per electron.

**Energy** in a circuit is charge times voltage, measured in Joules (J):

$$E = QV$$

**Power** is the rate of change of energy, in Joules per second, i.e. Watts (W). It is the work done by the circuit per unit time. Combined with Ohm's law it takes three equivalent forms:

$$P = VI = I^2R = V^2/R$$

## Unit prefixes

| Prefix | Factor |
|--------|--------|
| kilo (k) | $10^3$ |
| mega (M) | $10^6$ |
| giga (G) | $10^9$ |
| milli (m) | $10^{-3}$ |
| micro ($\mu$) | $10^{-6}$ |
| nano (n) | $10^{-9}$ |
| pico (p) | $10^{-12}$ |

## Constant vs. time-varying circuits

**Direct current** (DC) means voltages and currents are constant, like a 1.5 V battery.

**Alternating current** (AC) means voltages and currents change with time, like home wall power. The general form is

$$v(t) = A\cos(\omega t), \qquad \omega = 2\pi f$$

The lecture wrote US wall power as $V(t) = 120\cos(2\pi \cdot 60\,\text{Hz} \cdot t)$. Note that 120 V is the nominal RMS figure; the true peak of a 120 V RMS line is $120\sqrt{2} \approx 170$ V.

Nodal analysis lets you break circuits down and black-box them. You represent each node mathematically, then use that abstraction to model complicated circuits.

## Worked problems

**iPhone battery energy.** An iPhone contains a lithium battery with a voltage of 3.8 V and a capacity of 2900 mAh. Energy stored, in Watt-hours and Joules:

$$2900\,\text{mAh} \times 3.8\,\text{V} = 11{,}020\,\text{mWh} = 11.02\,\text{Wh}$$

$$11.02\,\text{Wh} \times 3600\,\text{s/h} = 39.67\,\text{kJ}$$

**Standby power.** Apple claims an iPhone lasts 16 days on standby. Average power consumed in standby:

$$2900\,\text{mAh} \times 3600\,\text{s/h} = 10.4 \times 10^6\,\text{mA·s}$$

$$16\,\text{days} = 1.4 \times 10^6\,\text{s}$$

$$I = \frac{10.4 \times 10^6\,\text{mA·s}}{1.4 \times 10^6\,\text{s}} = 7.55\,\text{mA}$$

$$P = 3.8\,\text{V} \times 7.55\,\text{mA} = 28.7\,\text{mW}$$

**Tesla battery.** A Tesla Model S has a battery capacity of 100 kWh. In Joules:

$$100\,\text{kWh} \times 3600\,\text{s/h} = 360 \times 10^6\,\text{J} = 360\,\text{MJ}$$

**Solar recharge time.** Bright sunlight has a power density of roughly 1 kW/m^2, and a solar panel converts sunlight to electricity at 20% efficiency. Covering the car in 10 m^2 of panels:

$$1\,\text{kW/m}^2 \times 10\,\text{m}^2 \times 0.2 = 2\,\text{kW} = 2000\,\text{J/s}$$

$$\frac{360 \times 10^6\,\text{J}}{2000\,\text{J/s}} = 180{,}000\,\text{s} = 50\,\text{hours}$$

## Related

- [[signal-conditioning/lecture-notes/lecture-3|Resistance]]
- [[cheatsheets/circuits/electricity|Electric Circuit Analysis]]
