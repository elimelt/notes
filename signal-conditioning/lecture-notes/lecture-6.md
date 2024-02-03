## Capacitors

Stores energy in electric field between two plates.

Passes AC, blocks DC. "High pass filter"

Capacitance is the ratio of charge to voltage, measured in Farads.
$$
C = \frac{Q}{V}
$$

The energy stored in a capacitor is
$$
E = \frac{1}{2}CV^2
$$

$$
\frac{d}{dt}Q = \frac{d}{dt}CV
$$

$$
I_C = C\frac{dV}{dt}
$$

## Inductors

Stores energy in magnetic field around a coil of wire due to current flowing through it. Units are Henrys (H).

Passes DC, blocks AC. "Low pass filter"

Energy stored in an inductor is
$$
E = \frac{1}{2}LI^2
$$

$$
V_L = L\frac{dI}{dt}
$$


## Complex Numbers Review

$$e = 2.71828...$$

$$
j \cdot j = -1 \to j = \sqrt{-1}
$$

$$
e^{jq} = \cos(q) + j\sin(q)
$$

## Complex Numbers for AC Signals

- Pretend signals are complex during analysis, then take real part at the end.
- Multiplying by real number is scaling (magnitude/amplitude)
- Multiplying by imaginary number is phase shift
- Multiplying by complex number is scaling and phase shift

EX:

$$
cos(2\pi ft + \phi) = e^{j\phi}e^{j2\pi ft}
$$

## Impedance

The AC version of resistance.

$$
Z_{cap} = \frac{1}{j\omega C}
$$

$$
Z_{ind} = j\omega L
$$

$$
Z_{res} = R
$$



