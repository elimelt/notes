# The Physical Layer

**Scope**: How signals are used to transfer bits over a link. i.e, how analog signals are converted to digital signals, and vise versa.

## Coding and Modulation

A modem (modulator-demodulator) converts digital signals to analog signals, and vise versa.

### A simple coding
A high positive voltage for 1, and a low negative voltage for 0. This is called **NRZ**(Non-Return-to-Zero). 


### Problems?
- TODO

There are many other practical coding schemes, all of which are driven by engineering considerations.

### Clock Recovery

Reciever needs requent signal transitions to decode bits. Several possible designs, including Manchester Coding and Scrambling.

A simple solution is to alternate between positive/negative, and zero voltages. This is return to zero (RZ) coding.

```txt
    0       1        1      1       0
+V |        ___     ___     ___
   |   |   |   |   |   |   |   |   |   |  
   |   |   |   |   |   |   |   |   |   |  
0  |   |___|   |___|   |___|   |___|   |
   |   |   |   |   |   |   |   |   |   |  
   |   |   |   |   |   |   |   |   |   |  
-V |___|   |   |   |   |   |   |   |___|  
```

### Modulation vs. Coding

With **coding**, signal is sent directly on a wire. This doesn't work well for wireless, so we use **modulation**. **Modulation** carries a signal by varying the frequency, amplitude, or phase of a carrier wave. *Baseband* is the original signal, and *passband* is the modulated signal. We can modulate a signal by varying the amplitude, frequency, or phase of a carrier wave.

### Key Points

- Everythign is analog, even digital signals.
- Digital signals are conceptually discrete, but are represented physically in a continuous medium.


## Simple Link Model

- **Rate** (bandwidth, capacity, speed): Number of bits per second
- **Delay**: Related to the time it takes to deliver a message
- **type of cast**: unicast, multicast, broadcast
- **error rate**

### Message Latency

**Latency** is the time it takes for a message to travel from one end of a link to the other. It is the sum of the **transmission delay** (time to put bits on wire) and the **propagation delay** (time for bits to travel from one end of the link to the other).

```txt
Transimission Delay:
T (delay) = L (message length) / R (rate) = L/R seconds

Propagation Delay:
P (delay) = D (distance) / S (speed) = D/(2/3 * C) = 3D/2C seconds

Total Latency:
L_t = T + P = L/R + 3D/2C
```

#### Example

```txt
Broadband cross-country link:
P = 50ms, R = 10Mbps, L = 1MB

L_t = 1MB/10MBps + 50ms = .1s + .05s = .15s
```
