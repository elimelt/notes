---
title: Transmission Control Protocol (TCP)
category: Networks
tags: connection establishment, three-way handshake, connection release, time_wait state, adaptive timeout, rtt, initial sequence number
description: The document covers the Transmission Control Protocol (TCP), a fundamental networking protocol that enables reliable data transfer between computers. It describes the key aspects of TCP, including the connection establishment process (three-way handshake), connection release, and the TIME_WAIT state. The document also discusses TCP's mechanisms for handling network congestion, such as Slow Start, Tahoe, Reno, and Explicit Congestion Notification (ECN), as well as fairness considerations in bandwidth allocation.
---

# Transmission Control Protocol (TCP)

## Connection Establishment

Both sender and receiver must be ready to transfer data, and they need to agree on parameters like max segment size.


### Three-Way Handshake

Opens up connection between client and server. Each side probes the other with a fresh **Initial Sequence Number (ISN)**. Sends on a SYNchronize segment, and echos on ACKnowledge segment. This gives us robustness, but requires extra overhead.

- Client sends SYN(x)
- Server replies with SYN(y)ACK(x+1)
- Client replies with ACK(y+1)
- SYNs are retransmitted if lost


### Connection Release

TCP requires a two-way close. Client and server both finish sending all their data and send a FIN segment. Each FIN closes one direction of the connection.

- Active sends FIN(x), passive ACKs
- Passive sends FIN(y), active ACKs
- FINs are retransmitted if lost

### TIME_WAIT State

Wait a long time afer sending all segments before actually closing (2 x max segment lifetime). This is because the final ACK may be lost, and we need to make sure the other side has received it. Otherwise it might interfere with a new connection.

### Timeout Problem

If you set it too small, you will retransmit too often. If you set it too large, you will wait too long to detect a failure. Setting the timeout of TCP is a difficult problem because RTT varies widely (due to queueing, routing, etc).

TCP uses **adaptive timeout**. It smooths the estimates and variance of the RTT using a moving average.

$$SRTT_{N + 1} = (1 - \alpha) \cdot SRTT_N + \alpha \cdot RTT_{N + 1}$$

$$Svar_{N + 1} = (1 - \beta) \cdot Svar_N + \beta \cdot |RTT_{N + 1} - SRTT_{N + 1}|$$

Set the timeout to be a multiple of the smoothed RTT, plus a margin for error. Adaptive timeout works well in practice, but it's not perfect. It can be thrown off by a sudden change in RTT, and it can be exploited by an attacker to cause a DoS attack.

## Network Congestion

Think about a "traffic jam" in the network. The network is temporarily overloaded and can't handle all the traffic. This can lead to packet loss, increased latency, and decreased throughput. Want to push as close to being congested as possible without actually being congested, which is a high level function of TCP.

Switches and routers have *internal buffers* to store packets, which essentially act like a queue for each port. When working normally, queues are able to absorb bursts of traffic. However, if the input rate is persistently higher than the output rate, the queue will eventually fill up and packets will be dropped.

Congestion is a function of traffic patterns, and it can even occur even when the network isn't at full capacity. We would like it if the throughput increased linearly, or even logarithmically towards the capacity of the network as you increase the load on a system. In practice, there is a sharp dropoff in throughput past a certain point of load where congestion collapse occurs.

Connection collapse is when packets are dropped/time out, and so the sender retransmits the packets, which only makes the problem worse. This is a positive feedback loop that can lead to a complete breakdown of the network.

## TCP Tahoe/Reno

Has the following extensions/features:

- AIMD
- Fair queuing
- Slow start
- Fast retransmit
- Fast recovery

### Bandwidth Allocation


#### Fairness

Kind of a weird problem. Just think about it like scheduling threads and processes. You want to give each process a fair share of the CPU, but simply allocating bandwidth equally to each thread in the process is not fair. You want to allocate bandwidth to each connection fairly, but you also want to allocate bandwidth to each user fairly, and you also want to allocate bandwidth to each application fairly.

#### Equal per Flow Fairness

The **bottleneck** for a flow of traffic is the link that limits its bandwidth. TCP tries to allocate bandwidth fairly to each flow by sharing the bottleneck bandwidth equally among the flows that traverse it.

#### Max-Min Fairness

Intuitively, flows bottlenecked on a link get an equal share of that link. A max-min fair allocation is one that maximizes the minimum bandwidth allocated to any flow. To find it given a network, you can imagine "pouring water" into the network and seeing how much each flow gets. You can then adjust the flow rates to maximize the minimum flow rate.

When flows start and stop, need to rerun the algorithm to find new allocation.


TCP needs to allocate bandwidth of a network fairly and efficiently (which are conflicting goals). The network witnesses congestion and provides direct feedback to the transport layer. Then, the transport layer can decrease its sending rate to avoid congestion.

This is a hard problem. The number of senders is almost never constant, and each customer's load is constantly changing. Also, senders often lack capacity in certain parts of the network, and no one entity has a complete view of the network.

This is solved by having the senders continuously probe the network and adapt their sending rate based on feedback from the network.

- **Open loop**: reverse bandwidth before use
- **Closed loop**: measure bandwidth and adjust as you go
- Host vs. network support: who sets and enforces allocations.
- Window vs. rate: allocation based on window size or rate of sending.

TCP uses closed-loop, host-driven, window-based allocation. The network sends *packet-dropped* messages as feedback. Note that there is nothing stopping a sender from implementing a more "aggressive" or "greedy" algorithm, but it would be against the spirit of the protocol. There are also different implementations of TCP that have different congestion control algorithms.

| Signal | Protocol | Pros/Cons |
| ------ | -------- | ---------- |
| Packet Loss | TCP NewReno/Cubic (linux) | Simple, but there is some latency |
| Packet delay | TCP BBR (YouTube) | Early notifacation, but need to infer congestion |
| Explicit congestion notification via router | TCPs with explicity congestion notification | Fast, but requires router support |


#### Additive Increase, Multiplicative Decrease (AIMD)

A control law hosts use to reach a good allocation. Hosts additively increase rate while network isn't congested, and multiplicitively decrease rate when congestion is detected.

Let $x$ be the allocated bandwidth to H1, and $y$ be the allocated bandwidth to H2. Assumming a capacity $1$, a fair allocation would be $x = y$, but an efficient allocation would be $x + y = 1$.

On the plot of x and y, the algorithn is as follows:

- When the network is not congested, increase the rate by a small amount parallel to the "fair" line, (ie increase x and y by an equal amount).
- When the network is congested, decrease the rate by a large amount, corresponding to the line from the current allocation point to the origin.

This guarantees that the allocation converges to the intersection of the "fair" line and the "efficient" line. Also creates a "sawtooth" pattern of sending rate over time.


### Slow Start with TCP (Additive Increase)

Sender uses **congestion window (cwnd)** to set its rate (cwnd/RTT), and packet loss as a signal.

You want to quickly converge to the ideal window size, but you also don't want to cause congestion. Solution is to increase exponentially until you hit a packet loss, then set the window size to half of the current window size. Then, switch to additive increase.

- **Slow Start Doubling**: First send one packet. Then, on ACK, send two packets. Then, on two ACKs, send four packets. Keep this doubling until you hit a packet loss.

- **Additive Increase**: After slow start, increase the window size by one packet per RTT/ACK.

### TCP Tahoe

- Initial slow-start phase
    - Start with cwnd = 1 (or another small val)
    - cwnd += 1 for each ACK
- After packet loss, additively increase cwnd
    - cwnd += 1/cwnd for each ACK
    - roughly add 1 packet per RTT
- Switching threshold
    - Switch to AI when cwnd > ssthresh
    - set ssthresh = cwnd / 2 on packet loss
    - begin slow start again

Need to go back to cwnd = 1 on packet loss because we lost the ack clock. This is conservative but not very efficient.

### Fast Recovery

#### Infering Packet Loss

Reciever sends duplicate ACKs when it receives out-of-order packets. The sender can infer that the packet was lost and retransmit it. If the reciever is stuck on an out of order packet, the subsequently sent packets will still be buffered, but the duplicate ack indicates where to retransmit on the client side.

Need to be able to infer loss of packets before timeout actually occurs. TCP uses a **cumulative ACK**, which carries the highest in-order sequence number received. If you receive three duplicate ACKs, you can infer that the packet was lost and retransmit it.

Sender decreases cwnd by half on packet loss, but it can also retransmit the lost packet immediately. This is called **fast retransmit**.

#### Inferring Non-Loss from ACKs

Each duplicate ACK indicates that a packet was received, but not in order. This means that the network is still capable of transmitting packets, and so the sender can increase its sending rate. This is called **fast recovery**.

If multiple packets are lost in a row, this will not work and the sender will go back to slow start cwnd = 1.

### TCP Reno, NewReno, SACK

- Reno can repair one loss per RTT. Multiple losses cause timeout
- NewReno repairs multiple losses without timeout
- Selective ACKs (SACK) sends ACK ranges so that sender can retransmit multiple packets at once

### Explicit Congestion Notification (ECN)

- Commonly used in data centers
- Routers deliver clear signal to hosts when congestion occurs
- Congestion is detected early to prevent packet loss
- Hosts can react to congestion without packet loss, and no retransmission or timeout is needed
- Routers need to support ECN, and they have more work to do.
- Hosts need to support ECN, and they have more work to do.
### Random Early Detection (RED)

Instead of marking pakets, just randomly drop packets to throttle senders. The probablity of dropping a packet increases as the queue fills up.