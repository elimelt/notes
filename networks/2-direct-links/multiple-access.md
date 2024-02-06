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

