---
title: Clock Synchronization for Distributed Systems
category: Distributed Systems
tags: Distributed Systems, Clock Synchronization, Physical Clocks
description: This response provides a solution to the problem of clock synchronization in distributed systems using physical clocks. It explains the concept of unpredictable delays and how to synchronize clocks in the forward direction.
---

# Time, Clocks, and the Ordering of Events in a Distributed System
[reading](https://amturing.acm.org/p558-lamport.pdf)

## Introduction

It would be convenient if we could order events in a distributed system, but it is impossible to do so in a way that is consistent with the order in which they actually occurred. However, we can define a partial ordering of events that is consistent with the order in which they occurred, and can extend this to a total ordering of events that is consistent with the partial ordering.

A partial ordering of objects is a relation that is reflexive, antisymmetric, and transitive. Conversely, a total ordering is a partial ordering that is also connexive, i.e. for any two objects $a$ and $b$, either $a \leq b$ or $b \leq a$.

## Notation

- $a \rightarrow b$: Event $a$ happened before event $b$.
  - $\to$ is an irreflexive, transitive relation that defines a partial order of events in a distributed system.
  - if $a$ is the sending of a message and $b$ is the receipt of that message, then $a \rightarrow b$.
  - if $a \rightarrow b$ and $b \rightarrow c$, then $a \rightarrow c$.
  - $a \nrightarrow a$.
- $a \nrightarrow b$: Event $a$ did not happen before event $b$.
- $a \Rightarrow b$: Event $a$ happened before or concurrently with event $b$.
  - if $a$ is an event in process $P_i$ and $b$ is an event in process $P_j$, then $a \Rightarrow b \iff a \rightarrow C_i\langle a \rangle < C_j\langle b \rangle \lor (C_j\langle b \rangle = C_i\langle a \rangle \land P_i \prec P_j)$, where $\prec$ is an arbitrary total order of processes (e.g. lexicographic order of process identifiers)
  - $a \Rightarrow b \implies a \to b$.
- $a \nRightarrow b$: Event $a$ did not happen before or concurrently with event $b$.
- $C_i\langle a \rangle$: The clock value of process $P_i$ when event $a$ occurs.
  - $C_i\langle a \rangle < C_j\langle b \rangle$: Event $a$ happened before event $b$.
  - $(a \to b) \implies (C_i\langle a \rangle < C_j\langle b \rangle)$.

## Clock Condition

If $a$ and $b$ are events in process $P_i$ and $a \to b$, then $C_i\langle a \rangle < C_i\langle b \rangle$.

If $a$ is the sending of a message and $b$ is the receipt of that message, then $a \to b$ and $C_i\langle a \rangle < C_j\langle b \rangle$.

To meet the clock condition, we must always increment the clock value of the process when an event occurs. Furthermore, if event $a$ is the sending of a message $m$ containing the clock value $T_m = C_i\langle a \rangle$, then upon receipt of $m$, the receiving process must set its clock value $C_j\langle b \rangle$ to a value greater than $T_m$.

## Synchronized Access to a Shared Resource

We wish to find an algorithm for granting the resource to a process which satisfies the following three conditions:

- (I) A process which has been granted the resource must release it before it can be granted to another process.
- (II) Different requests for the resource must be granted in the order in which they are made.
- (III) If every process which is granted the resource eventually releases it, then every request is eventually granted.

### Assumptions

For any two processes $P_i$ and $P_j$, messages sent by $P_i$ are received in the order they were sent by $P_i$. This can be achieved using stop-and-wait or sliding window protocols.

Further, we assume that all messages are received within a bounded time, i.e. all messages will eventually be received.

Also note that this protocol requires active participation from all processes. If any one process fails, then the entire system stops, because the algorithm requires all processes to respond to a request before the resource can be granted.

### Algorithm

1. To request the resource, a process $P_i$ sends a message $T_m:P_i$ *request* to all other processes, and puts that message on its request queue, where $T_m$ is the current clock value of $P_i$.
2. When process $P_j$ receives $T_m:P_i$ *request*, it places it on its request queue and sends a *reply* message to $P_i$ with its current clock value.
3.  To release the resource, $P_i$ removes $T_m:P_i$ *request* from its request queue and sends a *release* message with its current clock value to all other processes.
4. When process $P_j$ receives a $P_i$ *release* message, it removes $T_m:P_i$ *request* from its request queue.
5. $P_i$ is granted the resource when the following conditions are met:
   - There is a $T_m:P_i$ *request* message in its queue ordered by $\Rightarrow$ before any other *request* messages.
   - $P_i$ has received a *reply* message from all other processes with a clock value greater than $T_m$.

### State Machine Perspective

The algorithm can be viewed as a state machine consisting of $C$, the set of commands and $S$, the set of states. The state machine is defined by the following function:

$$
e: C \times S \to S
$$

Where $e(c, s) = s'$ means that executing the command $c$ in state $s$ results in a transition to state $s'$. In this algorithm, we have state $S$ corresponding to the queue of requests, and commands $C$ corresponding to the request and release messages for any given process.

$$
C = \{ P_i \text{ request}, P_i \text{ release} \}
$$

Executing $P_i \text{ request}$ in state $s$ results in a transition to state $s'$ where $s'$ is the state with the request message added to the queue. Executing $P_i \text{ release}$ in state $s$ results in a transition to state $s'$ where $s'$ is the state with the request message removed from the queue. Each process $P_i$ is its own state machine, and a process can execute a command time-stamped $T$ only if it has received all messages with time-stamps less than or equal to $T$.

## Anomalous Behavior of Total Ordering

Consider a nationwide system of nodes. A person issues a request $a$ at node $A$, and after doing so, calls their friend in a different city at node $B$ to issue a request $b$. It is possible with the total ordering of events that $b \to a$, even though $a$ was issued before $b$. This is because the total ordering of events is not consistent with the order in which they actually occurred, but rather with the order in which they were observed. The message that would be able to establish the the actual ordering of events (the call) is external to the system.

More concretely, let $\mathscr{L}$ be the set of all events, and $L$ be the set of all events in our system.

$$L \subseteq \mathscr{L}$$

In the above scenario, we had $a \to_{\mathscr{L}} b$, but $b \nrightarrow_{L} a$. No algorithm based soley on the events in $L$, without knowledge more generally of $\mathscr{L}$ can order $a$ before $b$.

There are two approaches to fixing this issue:

1. Users must manually specify restraints on timestamps, ie the person at $A$ must tell the person at $B$ that $T_a < T_b$. This is not a great solution.
2. Construct a system of clocks that satisfy the following condition: if $a \to_{\mathscr{L}} b$, then $C\langle a \rangle < C\langle b \rangle$.

## Physical Clocks

Let $C_i(t)$ be the value clock $C_i$ at time $t$. Assume that $C_i(t)$ is a continuous and differentiable function of $t$, except for isolated points where it jumps when the clock is reset. Note that a discrete clock can be modeled as a continuous clock with an error of up to $\epsilon = \frac{1}{2} \text{ tick}$.

Then $\frac{dC_i(t)}{dt}$ is the rate at which the clock is running at time $t$. If $\frac{dC_i(t)}{dt} = 1$, then the clock is running at the correct rate. We assume that the following holds:

$$
\exists \kappa \ll 1 \text{ such that } \forall i, t: |\frac{dC_i(t)}{dt} - 1| < \kappa
$$

And in fact, for typical quartz oscillator clocks, $\kappa \le 10^{-6}$.

This however isn't enough. For an effective clock system, we also want our clocks to be synchronized such that...

$$
\forall i, j, t: |C_i(t) - C_j(t)| < \epsilon
$$

...where $\epsilon$ is the maximum error in the clocks. Since physical clocks will never run at **exactly** the same rate, they will tend to drift apart over time. To correct for this, we can use a synchronization algorithm to periodically reset the clocks to a common time.

Letting $\mu$ be a number such that if event $a$ occurs at physical time $t$, and event $b$ is an event in another process that satisfies $a \to b$, then $b$ occurs later than physical time $t + \mu$. So $\mu$ is the maximum time it takes for a message to be sent from one process to another.

To avoid anomalies, we must ensure...

$$
\forall i, j, t: C_i(t) < C_j(t + \mu), \text{ or, equivalently, } C_i(t + \mu) - C_j(t) > 0
$$

And relating this to $\kappa$...

$$
\forall i, j, t: C_i(t + \mu) - C_j(t) > (1 - \kappa)\mu
$$

And calculating the maximum error in the clocks...

$$
\frac{\epsilon}{1 - \kappa} \le \mu
$$

### Clock Synchronization Algorithm

Importantly, one must always synchronize clocks in the forward direction, i.e. $C_i(t) < C_j(t + \mu)$. If $C_i(t) > C_j(t + \mu)$, then $C_i(t + \mu) - C_j(t) < 0$, which is not allowed.

Let $m$ be a message sent at time $t$, and received at time $t'$. Let $v_m = t' - t$ be the **total delay** of the message. Although the delay of a message is not known by any given process, we assume the receiver has some lower bound on the delay, $\mu_m$. Define $\zeta_m = v_m - \mu_m$ to be the **unpredictable delay** of the message.

Now, define the following rules for our physical clocks:

1. $\forall i$ if $P_i$ does not receive a message at physical time $t$, then $C_i$ is differentiable at $t$ and $\frac{dC_i(t)}{dt} > 0$.
2. If $P_i$ sends a message $,$ at physical time $t$, then $m$ contains a timestamp $T_m = C_i(t)$. Upon receiving a message $m$ at physical time $t'$, $P_j$ sets $C_j(t') = \max(\lim_{\delta \to 0} C_j(t' - \delta), T_m + \mu_m)$.