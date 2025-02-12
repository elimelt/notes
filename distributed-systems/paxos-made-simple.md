---
title: Paxos Protocol
category: distributed-systems
tags: Consensus Algorithm, Distributed Systems, Fault-Tolerant Systems
description: A protocol for achieving consensus in distributed systems
---

# Paxos Made Simple

[reading](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf)

## The Consensus Algorithm

### The Problem

Consider a set of processes that can propose values. A consensus algorithm ensures that a single value is chosen and agreed upon. For safety, we must have...

- Only proposed values are chosen
- Only a single value is chosen
- Processes only learn values that are actually chosen

And it assumes an asynchronous, non-byzantine network in which nodes are fail-stop.

### Choosing a Value

In paxos there are 3 types of agents

- *proposers*
- *acceptors*
- *learners*

#### P1: An acceptor must accept the first proposal it receives

This guarantees that some value is accepted by each node that is proposed to, but it doesn't prevent situations where no proposal is accepted by a majority of acceptors.

#### P2: If a proposal with value $v$ is chosen, then every higher-numbered proposal accepted by any acceptor has value $v$

This guarantees that only a single value is chosen, since unique proposal numbers can be used to decide between accepted values.

##### P2a: If a proposal with value $v$ is chosen, then every higher-numbered proposal accepted by any acceptor has value $v$

This is a stronger version of P2 that ensures previous values are not forgotten/overridden.

However, P2a contradicts P1, since if a proposer "wakes up" after having been out of commission, it must accept whatever value is proposed first. We thus strengthen even further to...

##### P2b: If a proposal with value $v$ is chosen, then every higher-numbered proposal issues by any proposer has value $v$

This shifts the burden of remembering and staying consistent with the chosen value to the proposers instead of the acceptors. We then have...

$$
\text{P2b} \to \text{P2a} \to \text{P2}
$$

In order to implement P2b, we must further constrain our algorithm's behavior to...

##### P2c: For any $v$ and $n$, if a proposal with value $v$ and number $n$ is issued, there is a set $S$ consisting of a majority of acceptors such that either (a) no acceptor in $S$ has accepted any proposal numbered less than $n$, or (b) $v$ is the value of the highest-numbered proposal among all proposals numbered less than $n$ accepted by the acceptors in $S$

To satisfy P2b, we must maintain P2c as an invariant. To make sure this invariant holds, proposers proposing a proposal numbered $n$ must learn the highest-numbered proposal with a number less than $n$ that has been accepted by a majority of acceptors, and propose that value if it exists.

#### Proposition Algorithm

1. A proposer chooses a new proposal number $n$ and sends a *prepare* request to each member of some set of acceptors, awaiting a response containing:
    - A guarantee that this acceptor will never accept a proposal numbered less than $n$
    - The proposal with the highest number less than $n$ that it has accepted, if any.
2. If the proposer receives the requested responses from a majority of acceptors, it issues an *accept* request, which is a proposal with number $n$ and value $v$, where $v$ is the value of the highest-numbered proposal among the responses, or a value of the proposer's choice if no proposals in the responses were received.

#### Acceptor Behavior

Acceptors can only receive *prepare* and *accept* requests, and can ignore any request without compromising safety (but certainly still sacrificing liveness).

##### P1a: An acceptor can accept a proposal numbered $n$ iff it has not responded to a *prepare* request numbered greater than $n$

which implies P1

### Phases

#### Phase 1

- (a) A proposer selects a proposal number $n$ and sends a *prepare* request with number $n$ to a majority of acceptors.
- (b) If an acceptor receives a *prepare* request with number $n$ greater than any it has seen, it responds with a promise not to accept any proposal numbered less than $n$ and the highest-numbered proposal (and corresponding value) it has accepted.

#### Phase 2

- (a) If the proposer receives responses from a majority of acceptors, it sends an *accept* request to each acceptor with the proposal number $n$ and the value $v$ of the highest-numbered proposal among the responses, or a value of its choosing if no proposals were received.
- (b) If an acceptor receives an *accept* request with number $n$ greater than any it has seen, it accepts the proposal and responds to the proposer, unless it has already responded to a *prepare* request with a number greater than $n$.

Note that to increase performance, if an acceptor ignores a *prepare* or *accept* request because it has already received a *prepare* request with a higher number, it should notify the proposer with a *reject* message. This however doesn't change the correctness, and is thus optional.

## Learning a Chosen Value

One option would be for each acceptor to send a message upon accepting a value to all learners, but this requires a whole lot of message passing. Another option is to maintain a set of *distinguished* learners, which after hearing of a majority acceptance, notify all other learners of the accepted value. The larger this set of distinguished learners, the more fault-tolerant the system, but also the more communication required.

Since messages can be dropped, a value can be chosen without any learner finding out. In this case, learners will find out the chosen value only after a new proposal is chosen. Learners can thus determine whether a value was chosen by following the same protocol to issue a new proposal as above.

## Progress

It is entirely possible with the above protocol that multiple proposers indefinitely one-up each other between sending their *propose* and *accept* requests, such that all proposals are ignored. To prevent this, choose and maintain a single *distinguished* proposer, which is the only proposer allowed to issue proposals. If the distinguished proposer fails, a new one can be elected by the acceptors.

By **FLP**, any such leader election system must rely either on randomness, or real-time (i.e. timeouts).

## Implementing a State Machine

Consider a system of clients that issue requests to execute commands on a cluster of single-threaded application servers. Each application server can be thought of as a deterministic state machine, where the ordering of requests to each server **must** be consistent for them to end up in the same state.

To guarantee consistent ordering of commands executed within our cluster, we implement a separate instance of Paxos, where the $i$th instance's chosen value determines the $i$th command executed on all application servers.

During normal operation, a single server is elected to be leader, which acts as the *distinguished* proposer, and is the only server allowed to issue proposals. Clients then send their requests to this leader, which decides the sequence of commands globally. Any given instance of the protocol might fail, but regardless only one command can ever be chosen as the $i$th command to be executed.

For cases where some subsequence of commands are not yet determined, i.e. not chosen yet when a new leader takes over, the new leader issues phase 1 for all such instances (including the infinitely many commands greater than the largest command in our current sequence). Any values received in response are then proposed, but if an instance remains unconstrained (i.e. no value has been accepted), the leader can propose no-ops for the gaps in the sequence of commands before the last accepted command. It must do this before ever executing commands that come after these unconstrained slots.

After doing so, the leader can continue proposing any further commands requested by clients. The leader is allowed to propose command $i + \alpha$ before knowing the chosen command for $i$, meaning it can get up to $\alpha - 1$ commands ahead of itself (in the case where all commands less than $i + \alpha$ were dropped).

Once a leader has finished phase 1 for all commands thus far and afterwards, it only needs to complete phase 2 for each subsequent command requested, which is known to be the minimal algorithm for reaching consensus after phase 1.

To reiterate what was stated previously, in the case where a single leader is not elected, progress is not guaranteed, but safety is.
