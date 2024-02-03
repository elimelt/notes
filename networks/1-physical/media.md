# Media

*Media* propagates signals that carry information.

## Wires

### Twisted Pair

- Very common in LANs and phone lines. 
- Two insulated copper wires twisted together to reduce radiation/crosstalk, leading to less interference.

EX: Ethernet, DSL

### Coaxial Cable

- Copper core, surrounded by insulating material, surrounded by braided metal shield, surrounded by protective outer layer of plastic.
- Support higher data rates than twisted pair.
- Longer distances and better shielding.
- More expensive and harder to install than twisted pair. They are pretty inflexible.

EX: Cable TV, Internet

### Fiber

- Long, thin, pure glass strands that carry modulated light.
- Very high data rates and long distances.
- Immune to electromagnetic interference.
- Expensive and hard to install.
- Muli-mode vs. single-mode fiber is just a matter of multiple or single paths for light to travel.

EX: Internet backbone

## Wireless

Sends signals in all directions through a region of space. Nearby signals can **interfere** with each other, especially if they are on the same frequency; must coordinate use over time and frequency.

Wifi largely uses unlicensed spectrum, which is free to use but can be crowded. Interference can be a big problem. For example, turning on your microwave can interfere with your wifi.

Signals can take multiple paths (**multipath**), and are affected by physical barriers. The higher the frequency, the more easily it is absorbed by walls and other obstacles (this is why 5G sucks).

### Channel Properties

- **Bandwidth (Hz)**: The range of frequencies that the channel can carry. Note that bandwidth in this context is not the same as the *data-rate* of a link.
- **Signal Power (Watts)**: The strength of the signal.
- **Noise Power (Watts)**: The strength of the noise.

### Nyquist Limit

The max **symbol-rate** (rate at which symbols are sent) is twice the bandwidth. This would mean maintaining a maximum frequency, and sending a signal for each peak or trough of the wave.

If there are $V$ signal levels, ignoring noise, the max data rate is $2B \log_2(V)$ bits/sec.

### Shannon Capacity

The number of levels we can distinguish is limited by the ratio of signal power to noise power. The signal-to-noise ratio (SNR) is the ratio of the signal power to the noise power, and the higher the SNR, the more levels we can distinguish. Usually measured in decibels (dB).

$$
SNR_{dB} = 10 \log_{10} \left( \frac{S}{N} \right)
$$

Capacity (C) is the max **lossless** data rate over a channel. Don't ask me how to derive this...

$$
C = B \log_2 \left( 1 + \frac{S}{N} \right)
$$

Note that increasing bandwidth increases the capacity linearly, but increasing SNR increases the capacity logarithmically.