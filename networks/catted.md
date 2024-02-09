# Network Components

## Parts of a network

**Application** (app, user) - The application is the program that is running on the computer. It is the program that is using the network to communicate with other computers. Examples of applications are web browsers, email clients etc.

**Host** (end system, edge device, node) - The host is the computer that is running the application. It is the computer that is using the network to communicate with other computers. Examples of hosts are desktop computers, laptops, mobile phones etc.

**Router** (switch, node, hub) - Device used to relay messages between links. Connects networks together. Examples of routers are home routers/access points, cabel/DSL modems etc.

**Link** (channel) - A connection between nodes. Examples of links are Ethernet cables, fiber optic cables, wireless connections etc.

### Types of links

- **Full-duplex** - Both nodes can send and receive at the same time. *Bidirectional*. Ex: ethernet
- **Half-duplex** - Only one node can send at a time. *Bidirectional*. Ex: WiFi
- **Simplex** - Only one node can send at a time. *Unidirectional*. Ex: 

### Wireless Links

Messages are **broadcast**. All nodes in range recieve the message. Often, in graph depictions of a network, only the logical (but not all possible) links are shown.

## Network Names by Scale

**Personal Area Network** (PAN) - A network that is available in a single person's vicinity.

*Examples*: Bluetooth, USB, FireWire etc.

**Local Area Network** (LAN) - A network that is available in a single building.

*Examples*: Ethernet, WiFi etc.

**Metropolitan Area Network** (MAN) - A network that is available in a city.

*Examples*: cable TV, DSL etc.

**Wide Area Network** (WAN) - A network that is available in a country or geographic location.

*Examples*: a large ISP, 3G/4G wireless networks etc.

**Internet** - A network that is available globally.

*Examples*: the Internet.


When you connect multiple networks, you get an **internetwork**, or **internet**. The Internet (capital I) is the internet we all know and love.

#### Switched Network

**Switched networks** forward messages from node-to-node, until they reach their destination. The two most common switched networks are **circuit-switched** (phones) and **packet-switched** (most computer networks) networks.

```txt
    +-- (Host)      --+
    |                 |
(Link)                |
    |                 |  logical
    +-- (Host)        |    link
    |                 |
(Link)                |
    |                 |
    +-- (Host)      --+
```

Packet switched networks (PSN) send data in discrete chunks, called **packets**, or messages. PSNs typically use **store-and-forward** switching, where the entire packet is received and loaded into memory, then forwarded to the next node. This is opposed to a circuit switched network, where a stream of data is sent over a maintained connection.

Networks use an _address_ to identify the destination of a packet. Packets can be sent from node to node (_unicast_), but also to all other nodes _(broadcast_), or to a subset of nodes (_multicast_).



## Network Boundaries

```
(Router) --- (Host) --- client
   |
(Link)
   |
(Router) --- (Host) --- server
```

#### What part is the network?

Everything that isn't the application level. Some people do and don't include the host, but in this course we do.

#### Can think of "the cloud" as a generic network...

```
   +-- (Host) --- client
   |
(Cloud)
   |
   +-- (Host) --- server
```

## Key Interfaces

The network is designed to be modular, and there are clearly defined interfaces betweem (1) apps and the network, and (2) the network components themselves.

This is achieved through **protocols** and **layering**.

- Each instance of a protocol communicates to its peer through the same protocol.
- Each instance of a protocol uses only the services of the layer below it.

*"Protocols are horrizontal, and layers are vertical."*

```
# define protocols X, Y,
# where Y is a lower below X


   (comm using X)
X <---------------> X  <- (peers)
^                   ^
| <- (Y service) -> |
|                   |
Y <---------------> Y  <- (peers)
    (comm using Y)
```

#### Examples of protocols:
TCP, UDP, HTTP, FTP, SMTP, POP3, IMAP, DNS, DHCP, ARP, ICMP, IP, Ethernet, WiFi, Bluetooth, USB, FireWire, DSL, cable TV, 3G/4G, etc.

#### Example of a stack
```
 (browser)
    ||
+--------+
| HTTP   |
+--------+
| TCP    |
+--------+
| IP     |
+--------+
| 802.11 |
+--------+
    ||
    ++==>
```


### Encapsulation

Protocol layering is built upon literal encapsulation of data. Each lower level protocol wraps the higher level protocol's data in its own format with extra information. Similar to putting a letter in an envelope, and then sending it to someone in the mail.

The message "on the wire" for the above stack might look like...

```
                    +------+
                    | HTTP |
                    +------+
              +-----+------+
              | TCP | HTTP |
              +-----+------+
         +----+-----+------+
         | IP | TCP | HTTP |
         +----+-----+------+
+--------+----+-----+------+
| 802.11 | IP | TCP | HTTP |
+--------+----+-----+------+
```

When two nodes communicate, the sender builds up these layers until the data is ready to be transported over the physical medium. Then, once the data is recieved, the reciever peels back the layers until it reaches the application layer.

It is more involved that this diagram in practice. Trailers and headers of each request segment are needed, and the content is often encrypted or compressed. Furthermore, segmentation and reassembly happens when nodes communicate as well.

### Demultiplexing

When a message is recieved, it needs to be passed through exactly the protocols that use it. This is done using **demultiplexing keys** found in the headers of each protocol. Ex: IP protocol field, TCP port number, etc.

### Advantages of Layering

- **Modularity** - Each layer can be changed without affecting the other layers, so long as the interface remains the same.
- **Abstraction** - Each layer can be thought of as a black box. Information hiding can be used to connect different systems that rely on different protocols under the hood.
- **Standardization** - Each layer can be standardized, and then implemented by many different vendors.

For example, when a person submits a request on their home wifi, the router strips the WiFi header and adds an ethernet header to send it to the server.


### Disadvantages of Layering

- **Inefficiency** - Each layer adds overhead to the message. This is especially true for small messages, since the amount of overhead relative to the message size is large.
- **Hides information** - Each layer hides information from the layer above it. This can make debugging difficult, and limits some applications of the network (like an app that wants to know the network latency, or a network that needs to know about app priorities like QoS).

## OSI Layers


### Application Layer

Services that are used with end user applications. Examples: HTTP, FTP, SMTP, POP3, IMAP, DNS, DHCP, etc.

### Presentation Layer

Formats the data so it can be understood by the application layer. Also handles encryption and compression. Examples: JPEG, MPEG, ASCII, etc.

### Session Layer

Manages the connection between two nodes. Examples: NetBIOS, PPTP, etc.

### Transport Layer

Responsible for the transport protocol and error handling. Examples: TCP, UDP, etc.

### Network Layer

Responsible for routing and addressing. Reads the IP address from a packet. Examples: Routers, Layer 3 switches, etc.

### Data Link Layer

Responsible for the physical addressing. Reads the MAC address from a data packet/frame. Examples: Switches, bridges, etc.

### Physical Layer

Transfer data on a physical medium. Examples: Hubs, NICS, Cables, etc.


## The actual Internet Protocol Stack

```
+-------------+---------------+
| Application | SMTP, HTTP,   |
|             | RTP, DNS      |
+-------------+---------------+
| Transport   | TCP, UDP      |
+-------------+---------------+
| Internet    | IP            |
+-------------+---------------+
| Link        | Ethernet, DSL,|
|             | 3G/4G, WiFi,  |
+-------------+---------------+
```

## Course Reference Model

- **Application**: Programs that use network services
- **Transport**: Provides end-to-end data delivery
- **Network**: Provides data delivery across multiple networks
- **Link**: Sends frames over one or more links
- **Physical**: Sends bits using physical signals
# The Physical Layer

**Scope**: How signals are used to transfer bits over a link. i.e, how analog signals are converted to digital signals, and vise versa.

## Coding and Modulation

A modem (modulator-demodulator) converts digital signals to analog signals, and vise versa.

### A simple coding

A high positive voltage for 1, and a low negative voltage for 0. This is called **NRZ**(Non-Return-to-Zero). Each time interval (**symbol**) is like a sample point.

### Problems?

Only 1 bit/symbol. Can use more than just 2 voltage levels to get more bits/symbol. To get N bits/symbol, need 2^n voltage levels. There is a tradeoff between encoding efficiency and the sensitivity to noise.

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

#### Better Solution

-  Can map arbitrary bit patterns to eachother (as long as you don't decrease the number of bits to decode). Design encoding such that long runs of zero can't happen
-  Can even use xor and a psuedorandom bit pattern to encode and decode to make the encoded data random looking as well, getting rid of most long runs of zero.

### Modulation vs. Coding

In order to agree on the timing of data streams, AKA the start and end of a symbol being transmitted, you need to have a common clock between the two systems that are communicating.

With **coding**, signal is sent directly on a wire. This doesn't work well for wireless, so we use **modulation**. **Modulation** carries a signal by varying the frequency, amplitude, or phase of a carrier wave. *Baseband* is the original signal, and *passband* is the modulated signal. We can modulate a signal by varying the amplitude, frequency, or phase of a carrier wave.

#### Some examples:
- NRZ signal of bits
- Amplitude shift keying (zigbee)
- Frequency shift keying (bluetooth)
- Phase shift keying

WiFi for example goes all in and listens on an entire band of frequencies instead of just the binary 2 frequencies.Modern WiFi uses 256 frequency levels.

### Key Points

- Everythign is analog, even digital signals.
- Digital signals are conceptually discrete, but are represented physically in a continuous medium.
- Modulating and demodulating a signal is converting between analog to digital, and vise versa.
- A coding is an agreed upon "language" for your data.

## Simple Link Model

Two main parameters:

- **Rate** (bandwidth, capacity, speed): Number of bits per second
- **Delay**: Related to the time it takes to deliver a message

Additional info:

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


### Cut Through Routing








# Performance


Measured in **bandwidth** (or *throughput*) and **latency** (or *delay*).

**Bandwidth:** the number of bits per second
## Key Channel Properties

- **Bandwidth (B)**: The range of frequencies that can be transmitted over a channel.
- **Signal (S)**: The signal is the information that is being transmitted over the channel.
- **Noise (N)**: The noise is the unwanted information that is being transmitted over the channel.

## Nyquist Limit

Maximum *symbol* rate is 2B symbols/sec.

If there are V signal levels, max bit rate is:

R = 2B log_2(V) bits/sec

## Shannon Capacity

**Capacity (C)** limit is the maximum **lossless** information carrying rate of a channel.

C = B log_2(1 + S/N) bits/sec

- There is some rate at which we can transmit information over a channel without error.
- Assuming noise is fixed, we can increase the bandwidth to increase the capacity, albeit with diminishing returns.
- Increasing bandwidth increases capacity linearly

**Can't beat the Shannon limit**


## Wired/Wireless Perspecitive

# Coding and Modulation

*How information sent over a link?*

## Coding

### None-return-to-zero (NRZ)

1 is represented by a high voltage and a 0 is represented by a low voltage. This can however lead to problems with long runs of 1s or 0s.

- **Long runs of 1s**: The receiver might lose track of the clock, and the signal might be corrupted.
- **baseline wander**: The receiver keeps an average of the signal to determine the threshold for 1s and 0s. If there are long runs of 1s or 0s, the average might drift, and the receiver might start to misinterpret the signal.

### Clock Recovery

It is difficult to recover the clock from a NRZ signal that doesn't transition often. This is because the receiver doesn't know when to sample the signal. Several techniques are used to solve this problem, including manchester and scrambling. 

### Return-to-Zero (RZ)

After each bit, the signal returns to zero. This makes it easier to recover the clock, since the receiver can sample the signal after each return to zero.

### Designing Codes

One can design codes that are more robust to noise, or that have better clock recovery properties. In general, you map one set of bits to another set of bits, and then send the new bits over the link.

For example, in 4b/5b, we let $S$ be the set of all possible 4-bit sequences, and let $C$ be the set of all possible 5-bit sequences. Then we can define a code $f: S \to C$:

$$
f(0000) = 11110 \\
f(0001) = 01001 \\
f(0010) = 10100 \\
\vdots
$$

One can then choose a set $C$ such that there aren't long runs of 1s or 0s, or such that the clock can be recovered easily. Since there are left over symbols in $C$, we can use them to represent control information, such as the start of a frame.

## Modulation

**Modulation** transmits a digital signal over an analog channel by modulating a carrier. **Baseband** is the original signal, and **passband** is the modulated signal. **Keying** is the digital form of modulation (equivalent to coding, but using modulation instead).

### Amplitude Shift Keying (ASK)

In ASK, the amplitude of the carrier is changed to represent the digital signal. For example, a 1 might be represented by a high amplitude, and a 0 by a low amplitude. This faces the same problem as NRZ, in that it is difficult to recover the clock.

### Frequency Shift Keying (FSK)

In FSK, the frequency of the carrier is changed to represent the digital signal. For example, a 1 might be represented by a high frequency, and a 0 by a low frequency. This is more robust to noise than ASK.

### Phase Shift Keying (PSK)

In PSK, the phase of the carrier is changed to represent the digital signal. For example, a 1 might be represented by a phase of 0 degrees, and a 0 by a phase of 180 degrees. PSK can support more bits per symbol than ASK or FSK, leading to higher data rates.

## Link Model

- **Transmitter**: Converts digital signal to analog signal.
- **Channel**: The medium over which the signal is sent.
- **Receiver**: Converts analog signal to digital signal.

### Properties of the Channel

- **Rate** (or bandwidth): The number of bits per second that can be sent over the channel.
- **Delay**: The time it takes for a signal to travel from the transmitter to the receiver. Usually, the delay is proportional to the distance between the transmitter and the receiver.

### Latency

The delay in sending a signal from the transmitter to the receiver. This is the sum of the **propagation delay** and the **transmission delay**.

- **Propagation delay**: The time it takes for a signal to travel from the transmitter to the receiver.
- **Transmission delay**: The time it takes to put an $M$-bit frame on the link.

$$
D_{\text{transmission}} = \frac{\text{message size}}{\text{transmission rate}} = \frac{M}{R}
$$

where $R$ is the rate of the link in bits/sec and $M$ is the size of the frame in bits.

$$
D_{\text{propagation}} = \frac{\text{distance}}{\text{speed of the medium}} = \frac{d}{.66c}
$$

where $d$ is the distance between the transmitter and the receiver, and $c$ is the speed of light.

Overall, we can calulate the latency as:

$$
L = \frac{M}{R} + D_{\text{propagation}}
$$

### Bandwidth-Delay Product

Messages take up space on the wire, and the wire can only hold so many bits at a time. The **bandwidth-delay product** is the maximum number of bits that can be in transit at any time.

$$
\text{Bandwidth-Delay Product} = BD = R \cdot D_{\text{propagation}}
$$

Usually, either the bandwidth or the delay is the bottleneck. The BD gives us a sense of the overall capacity of the link# Media

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

Note that increasing bandwidth increases the capacity linearly, but increasing SNR increases the capacity logarithmically.# Error Detection and Correction

Some bits will inevitably be recieved in error. Noise may flip the bits recieved over the network. We need to be able to...

- detect errors
- retransmit
- correct errors

## Approach: Add Redundancy

- In error detection codes, add *check bits* to the message bits.
- In error correction codes, add **more** *check bits* to let some errors be corrected.
- Key issue is to design codes to detect as many errors as possible without having too much redundancy or computation required.

Generally, a **codeword** is a $D$-bit message with $R$ check bits added to it. The sender computes the check bits and appends them to the message. The reciever then verifies the check bits by recomputing them and comparing them to the recieved check bits.


### Example Code:

$$
1 \to 11\\
0 \to 00\\
x \to xx\\
$$

For example:
$$
101110 \to 101110101110
$$

Can detect errors with this code up to 1 bit. However, no guarantee if more bits are flipped. Also cannot correct errors. This sucks.

## Intuition

Let $S$ be the set of all possible $n$-bit sequences, and let $C$ be the set of all $n$-bit code words with $D$ data bits and $R$ check bits. We have $C \subset S$, and we want to choose $C$ such that the probability of a random $D$-bit sequence being in $C$ is low.

Consider a random $n$-bit sequence $x \in S$...

$$
\mathbb{P}(x \in C) = \frac{|C|}{|S|} = \frac{2^R}{2^n} = 2^{-D}
$$

Error correction/detection is hard because even the check bits can be corrupted. Given $d$ errors, we can detect and correct $d$ errors if the distance between any two code words is $2d + 1$.

## Hamming Distance

Distance: The number of bit flips needed to change from one valid code word to another. The distance of a code is the minimum distance between any two code words. Letting $C$ be the set of all code words, the distance is:

$$
\min_{x, y \in C, x \neq y} d(x, y)
$$

- For a coding of distance $d + 1$, we can detect $d$ errors
- For a coding of distance $2d + 1$, we can correct $d$ errors by mapping to the closest code word.


## Internet Checksum

Sum up chunks of data and append the sum to the end of the data. If the sum is 0 on the recieving end, then the data is valid.

This code has a distance of 2, so it can detect 1 bit errors, and can correct 0 bit errors (since it can't correct any errors)

### Internet Checksum Algorithm

#### sender

1. Split up data into 4 byte chunks.
2. Sum up all the 4 byte chunks, wrapping around for carry beyond 4 bytes.
3. netgate append the checksum to the end of the data.

#### reciever

1. Split up data into 4 byte chunks.
2. Sum up all the 4 byte chunks, wrapping around for carry beyond 4 bytes.
3. netgate append the checksum to the end of the data.
4. If the sum is 0, then the data is valid.

```python
def internet_checksum(data):
    checksum = 0
    for i in range(0, len(data), 4):
        chunk = data[i:i+4]
        checksum += int.from_bytes(chunk, 'big')
    return checksum.to_bytes(4, 'big')
```

## Cyclical Redundancy Check (CRC)

Given a generator polynomial $C$ and a message of $n$ bits, generate $k$ bits such that the $n + k$ bit message is divisible by $C$. Works with binary values that operate over the field $\mathbb{Z}_2$ (mod 2 arithmetic).

### CRC Algorithm

#### sender

1. create binary representation of polynomial as divisor
2. append 0s to the end of the data to be sent, equal to the degree of the polynomial
3. divide the data by the polynomial, using XOR
4. change redundant bits to remainder

#### reciever

1. create binary representation of polynomial as divisor
2. divide the data by the polynomial, using XOR
3. if the remainder is 0, then the data is valid

### Notes:

x + 1 as a generating polynomial is just a parity bit!

## Hamming Code

A code with distance 3. Can detect 2 bit errors and correct 1 bit errors.

Uses $n = 2^k - k - 1$. Put check bits in positions that are powers of 2, and fill in the rest with data bits. Check bits are calculated by checking the bits in the ith position for all data bits whose ith bit is 1.

```python
def hamming_encode(data):
    n = len(data)
    k, acc = 0, 1
    while acc < n + k + 1:
        k += 1
        acc *= 2

    code = [0] * (n + k)
    j = 0
    for i in range(1, n + k + 1):
        if i & (i - 1) == 0:
            code[i - 1] = 0
        else:
            code[i - 1] = data[j]
            j += 1
    for i in range(k):
        j = 2 ** i
        for l in range(j, n + k + 1):
            if l & j:
                code[j - 1] ^= code[l - 1]
    return code
```

### Algorithm

#### Send
1. Put all parity bits in positions that are powers of 2 (1, 2, 4, 8, 16, etc.)
2. Fill in all other positions with data bits.
3. calculate parity bits for each of the ith check bits. (check the bits in ith position for all data bits whose ith bit is 1)

#### Recieve
1. calculate parity bits for each of the ith check bits. (check the bits in ith position for all data bits whose ith bit is 1 of its index is a power of 2)
2. If the parity bits are all 0, then the data is valid (remove check bits from data bits)
3. If the parity bits are not all 0, then the data is invalid. The syndrome (concat and reverse the parity bits) is the index of the bit that is wrong. Flip that bit.


## Detection vs. Correction

- Error detection is easier than error correction. There is less overhead and computation required.
- Which is better depends on the pattern of errors. In general, error correction should be used when errors are detected and retransmission is expensive. Error detection should be used when errors are rare/unrecoverable, or when retransmission is cheap. Also used in application layer for physical storage (Reed-Solomon codes for CDs, DVDs, etc).

Error correction is heavily used in the physical layer. Low Density Parity Check (LDPC) codes are used in 802.11, DVB, WiMAX etc, and convolutional codes are used a lot in practice. On the other hand, detection combined with retranmission is used in the data link layer and above for residual errors.# Byte Oriented Protocols, Point-to-point protocol (PPP)

## Byte-Oriented Framing

- Oldest approach, viewing frames as collections of bytes.
- Examples: BISYNC by IBM, DDCMP in DECNET, PPP.

## Length Field Approach

- Include frame byte count in header (DDCMP approach).
- Risk: Transmission error corrupting count field; framing error.

## Sentinel-based Approach/Byte Stuffing

- Use special characters (SYN, STX, ETX) to indicate frame boundaries.
- Challenge: Special characters in data; overcome by character stuffing or escape sequences similar to C.

## PPP Frame Format

- Used for IP packet transmission over point-to-point links.
- Start-of-text character (Flag field: 01111110).
- Negotiable field sizes, CRC used for checksum.

## LCP Protocol and Negotiation

- Link Control Protocol (LCP) negotiates field sizes in PPP.
- Controls encapsulated in PPP frames.
- Involvement in link establishment between peers.

# Bit Oriented Protocols (HDLC)

## Bit-Oriented Framing

- Views frames as a bit stream, not concerned with byte boundaries.
- Examples: SDLC developed by IBM, standardized as HDLC by ISO.

## HDLC Frame Format

- Denotes frame start and end with bit sequence 01111110.
- Uses sentinel approach, similar to byte-oriented protocols.
- Bit stuffing employed to handle the sequence within the frame.

### Bit Stuffing in HDLC

- Inserts 0 after five consecutive 1s during transmission.
- Receiver removes stuffed 0 based on the next bit.
- Distinguishes between end-of-frame marker and errors.

## Frame Size Dependency

- Frame size depends on payload data; not all frames can be the same size.
- Challenges with ensuring consistent frame size discussed in the next subsection.


# Clock-Based Protocols (SONET)

## Clock-Based Framing in SONET

- Exemplified by Synchronous Optical Network (SONET) standard.
- Addresses framing, encoding, and multiplexing for data over optical fiber.

## SONET Frame Structure

- SONET frame has special information for start and end.
- No bit stuffing used; frame length independent of data.
- Special bit pattern in STS-1 frame helps receiver locate frame boundaries.

## Overhead and Payload

- SONET complexity due to overhead bytes and network-level considerations.
- Payload bytes scrambled for clock recovery.
- SONET supports multiplexing of low-speed links.

## Multiplexing in SONET

- SONET links run at rates ranging from STS-1 to STS-768.
- A single SONET frame can contain subframes for multiple lower-rate channels.
- STS-N frame consists of N interleaved STS-1 frames.

## Concatenation in SONET

- STS-N signal used to multiplex N STS-1 frames; payload may be concatenated.
- Denoted as STS-Nc for concatenated links.
- Simplifies clock synchronization across carriers' networks.
# Multiple Access

## Multiplexing

**Multiplexing** is the networking concept of sharing a resource among multiple clients. Network traffic is generally bursty, to the point that two concurrent users each using 1 Mbps of bandwidth might only need 1.5 Mbps of bandwidth to share. Multiplexing allows for this sharing.

### Time Division Multiplexing (TDM)

Users take turns on a fixed schedule, often being scheduled in a round-robin fashion.

### Frequency Division Multiplexing (FDM)

Users are assigned different frequency bands, and can transmit at the same time, interfering minimally with each other.

### TDM vs. FDM

In TDM, users send at a high rate for a short time, while in FDM, users send at a low rate contantly. For a fixed number of users, TDM might be better if the users are bursty, while FDM might be better if the users are constant.

Ex: TV and radio use FDM, while GSM (2G cellular) uses TDM within FDM.

## Controlling Access

Two classes: **centralized** and **distributed**.

### Centralized

Uses a privileged "Scheduler" to allocate resources/coordinate access. This usually scales well vertically and has low overhead, but is a single point of failure and doesn't hold up with the demands of the modern internet.

- Ex: Cellular networks, where the base station schedules access to the channel.


### Distributed

All of the participants "figure it out" themselves. Scaling this is really hard, but it operates well under low load, is easy to set up, and is very fault-tolerant (not to mention the benefits of being decentralized).

- Ex: Wifi, Ethernet, and the internet.

### Distributed (Random) Access

Assumes noone is in charge, and that everyone is trying to access the channel at the same time.

- **ALOHA Protocol**: Send whenever you want, and if there's a collision (no ACK), wait a random amount of time and try again. This is very simple, but has a high collision rate. At most 18% of the channel's capacity can be used. Quantization can be used to improve this to 36%.

### Carrier Sense Multiple Access (CSMA)

Another distributed access protocol. The sender listens to the channel (only really works for wired) before sending, and if it's busy, waits. This is better than ALOHA, but still has a high collision rate due to delay. Only a good idea for small BD-product links.

#### CSMA/CD (with Collision Detection):

Used in Ethernet. If a collision is detected, the sender stops sending and waits a random amount of time before trying again. Complicated because everyone involved in collision must be able to detect it.

Nodes have $2 \cdot D_{\text{propagation}}$ time to detect a collision. One can thus impose a minimum frame length of $2D# secones so that nodes can't finish sending a frame before the collision is detected. This is why Ethernet has a minimum frame size of $64$ bytes, and a maximum network length of $500$ m for Coaxial Ethernet, and $100$ m for Twisted Pair Ethernet.

#### CSMA "Persistence"

Cannot simply wait until the channel is free, as nodes might just continue to queue up until the channel becomes free and they collide. Instead, design such that heuristically, given $N$ queued senders, the probability of any given node sending is $1/N$.

### Binary Exponential Backoff

Given some discrete base quantity of time $q$, after collision $i$, sender waits $t_{i} = q \cdot \text{rand}(0, 2^i - 1)$.

```python
Q = 1 # seconds
def send(frame):
    t = 1
    while not send_frame(frame):
        time.sleep(Q * randint(0, t))
        t *= 2
```

#### Math behind Binary Exponential Backoff

- Let $k$ be the number of retransmission attempts.
- Let $W_k$ be the waiting time for the k-th retransmission attempt.
- Let $q$ be a fixed discrete time interval.

$W_k = q \cdot \text{randchoice}([0, 2^k - 1])$

Now, calculate the expected value $E[W_k]$:

$E[W_k] = \sum_{i=0}^{2^k - 1} i \cdot q \cdot P(W_k = i \cdot q)$

Since $P(W_k = i \cdot q)$ is uniform $\forall i \in [0, 2^k - 1]$, it is equal to $2^{-k}$.

$E[W_k] = q \cdot 2^{-k} \cdot \sum_{i=0}^{2^k - 1} i$

$ \sum_{i=0}^{2^k - 1} i = (2^k - 1) \cdot \frac{2^k}{2}$ (sum of first $n$ natural numbers)

$E[W_k] = q \cdot 2^{-k} \cdot ( (2^k - 1) \cdot 2^{k - 1} )$

Simplify further:

$E[W_k] = q \cdot ( (2^k - 1) / 4 )$

Therefore, the expected value of the binary exponential backoff for a fixed discrete time interval $q$ is $E[W_k] = \frac{q}{4} \cdot (2^k - 1)$.

### Ethernet

Classis Ethernet (IEEE 802.3), popular in the 80s and 90s. 10 Mbpd over shared coaxial cable. Multiple Access with 1-peristence CSMA/CD with BEB". Modern ethernet is based on switches, avoiding the need for CSMA/CD.

#### Ethernet Frames

- Addresses to identify sender and receiver.
- CRC-32 checksum to detect errors. No ACK or retransmission.
- Start of frame identified with phys layer preamble.

```plaintext
+----------------+
| Preamble (8B)  |
|                |
+----------------+
| Destination    |
| Address (6B)   |
+----------------+
| Source Address |
| (6B)           |
+----------------+
| Type (2B)      |
+----------------+
| Data (0-1500B) | --->
|                | ---> network layer (IP packet)
|      ...       | --->
+----------------+
| Padding (0-46B)|
+----------------+
| Checksum (4B)  |
+----------------+
```

# Retransmission

Reliability is a key feature of a network, and there are measures in place accross the entire stack to ensure it.

## Automatic Repeat reQuest (ARQ)

Often used when errors are common or must be corrected (e.g. wireless links). Receiver automatically acknowledges correct frames, and sender retransmits frames that are not acknowledged by a certain timeout.

- **Stop and Wait ARQ**: Sender sends one frame, waits for an ACK, and then sends the next frame.
- **Sliding Window ARQ**: Sender can send multiple frames before waiting for an ACK. For a window size of $n$, the sender can send $n$ frames per RTT.
- **Go-Back-N ARQ**: Sender can send multiple frames before waiting for an ACK, but if a frame is lost, the sender must retransmit all frames from the lost frame onwards.

### Timeouts

They need to be not too long (link is idle), but also not too short (link is busy). Timeouts are easy to set in a LAN, but harder over the internet where latency can vary greatly.

### Sequence Numbers

Both frames and ACKs are numbered, so that the sender knows which frames are acknowledged. In **stop and wait ARQ**, the sequence number is 0 or 1. In **go-back-N ARQ** and **sliding-window ARQ**, the sequence number is a number modulo $2^k$.


### Limitations of Stop and Wait ARQ

- Allows for only a single frame to be outstanding at a time.
- Good for LAN, but bad for networks with high BD product (*bandwidth-delay product*).


### Examples

(These are just pseudocode examples)

```python
# Stop and Wait ARQ
def sender():
    while True:
        frame = create_frame()
        send_frame(frame)

        ack_received = wait_for_ack()

        if ack_received:
            break

def receiver():
    while True:
        frame = receive_frame()
        process_frame(frame)

        send_ack()

```

```python
# Sliding Window ARQ
def sender():
    window_size = 3
    frames = [create_frame() for _ in range(window_size)]
    send_frames(frames)

    acknowledged_frames = wait_for_acknowledgment()

    # Move window forward
    frames = frames[len(acknowledged_frames):] + [create_frame()]
    send_frames(frames)

def receiver():
    while True:
        frames = receive_frames()
        process_frames(frames)

        send_acknowledgment()
```

```python
# Go-Back-N ARQ
def sender():
    window_size = 3
    frames = [create_frame() for _ in range(window_size)]
    send_frames(frames)

    while True:
        acknowledged_frames = wait_for_acknowledgment()

        if not acknowledged_frames:
            resend_frames(frames)

def receiver():
    expected_frame = 0

    while True:
        frames = receive_frames()

        for frame in frames:
            if frame.sequence_number == expected_frame:
                process_frame(frame)
                expected_frame += 1

        send_acknowledgment()
```# Switching

## Switched Ethernet

Hosts are wired to Ethernet switches using twisted pair cables. Switches serve to connect hosts together, and are able to forward frames to the correct destination.# Wireless

Wireless media is infinite, and therefore cannot carrier sense. Futhermore, nodes cannot hear the network while sending

## Hidden Terminal Problem

Two nodes are out of range of each other, but in range of a third node. The third node can hear both nodes, but the two nodes cannot hear each other. This can cause collisions at the node in the middle.

## Exposed Terminal Problem

Two nodes are in range of each other, but are sending to different nodes out of each other's range. The two nodes can hear each other, but are not in each other's way. The two nodes should be able to send at the same time, but this might be prevented by some protocols.

## Multiple Access with Collision Avoidance (MACA)

Uses short handshake instead of CSMA. Collisions are still possible, but less likely.

1. **Request to Send (RTS)**: Sender sends a request to send to the receiver.
2. **Clear to Send (CTS)**: Receiver sends a clear to send to the sender, including the frame size.
3. **Data**: Sender sends the frame while nodes that heard the CTS stay silent.


## 802.11 (WiFi)

Clients connect to the network through an **access point (AP)**.

## Physical Layer
- Uses 20/40 MHz channels on ISM (unlicensed) bands
  - 802.11b/g/n on 2.4 GHz
  - 802.11 a/n on 5 GHz
- OFDM modulation (except legacy 802.11b)
  - Different amplitudes/phases for varying SNRs
  - Rates from 6 to 54 Mbps plus error correction
  - 802.11n uses multiple antennas

## Link Layer
- Multiple access uses CSMA/CA; RTS/CTS optional
- Frames are ACKed and retransmitted with ARQ
- Three addresses due to AP
- Errors are detected with a 32-bit CRC
- Features like encryption, power save

## Centralized MAC: Cellular

Usually on a very limited spectrum because there are more regulations on non-ISM bands. The base station coordinates the transmissions of the mobiles, and is able to provide more strict control over the network to provide things like QoS and robustness.

GSM MAC uses FDMA/TDMA, and BEB for random access. One channel for coordination, and other channels for traffic. There is also a dedicated channel for QoS.