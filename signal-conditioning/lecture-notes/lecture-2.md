# Lecture 2

*Reminders*: 

- Lab 1 - Tuesday room 137 (pick up kit @ EE store window 3:30)

- HW 1 posted on canvas Monday


## Electricity

```
+-------------+------+----------+
|1.5 V Battery|      |Light Bulb|
+-------------+------+----------+
        current: I ->
```

Current is the amount of water flowing through the pipe, and Voltage is like the water pressure through the pipe.

If the "pressure" was 0, then the "flow" would be 0, and the same for the electrons. Battery is essentially using its chemical potential energy to push the electrons through the circuit to create a current.

#### Current (I) 

- Rate of flow of electrons. 
 
- Unit Amperes (A) (amps) - the rate of flow of 1 Coulomb of electrons/sec

#### Coulomb

- The unit of *charge* (how many electrons) **Q**

- 1 Coulomb is 6.24 * 10^17 electrons
#### Energy 

- Energy in circuit is the charge multiplied by the voltage, ie

Energy = Q * V -> Joules (J)

#### Power

The rate of change of energy, measured in Joules/sec -> Watts (W)

Or the work done by the circuit


### Units

10^3 -> kilo K
10^6 -> mega M
10^9 -> giga G

10^-3 -> milli m
10^-6 -> micro \mu
10^-9 -> nano n
10^-12 -> pico p


### Constant vs. Time Varying Circuits

**Direct Current** (DC): Voltages & Currents are constant, e.g. 1.5 V

**Alternating Current** (AC): Voltages and Currents are changing with time. e.g. Home power

```txt
General formula:
v(t) - 5 * cos(w * t)
w = 2 * pi * f

AC Line Voltage (wall power): 
V(t) = 120 * cos(2 * pi * 60 Hz * t)
```


Can use nodal analysis to break down and black box circuits. Mathematically represent each node in a circuit, and then use abstraction to model complicated circuits.


## Problems

(1.a) An iPhone contains a Lithium Battery with a voltage of 3.8 V, and a capacity of 2900 mAH (milli-Amp-hours). How much energy is stored in the battery? In Joules, and Watt-Hours.


2900 mAH * 3.8 V = 11,020 mWH = 11.02 WH

11.02 WH * 3600 sec/H = 39.67 kJ

(1.b) Apple claims that an iPhone lasts 16 days on standby mode. What is the average power consumed by the device in standby?

2900 mAH * 3600 sec/H = 10.4 * 10^6 mAsec

16 days = 1.4 * 10^6 sec

I = (10.4 * 10^6 mAsec)/(1.4 * 10^6 sec) = 7.552 mA

Power = 3.8 V * 7.552 mA = 28.7 mW


(2.a) A Tesla Model S has a battery capacity of 100 kWH. How many Joules of energy are stored in the battery?

100 kWH * 3600 sec/H = 360,000,000 J = 360 MJ


(2.b) Bright sunlight has a power density of roughly 1 kW/m^2. A solar panel has 20% efficiency in converting sunlight to energy. How long would it take to fully recharge the car if it were covered in solar panels with a surface area of 10 m^2?

1 kW/m^2 * 10 m^2 * .2 = 2 kW = 2 kJ/sec = 2000 J/sec

360,000,000 / 2000 J/sec = 180,000 sec = 50 hours






