---
title: Paxos Made Simple
category: Distributed Systems
tags:
  - paxos
  - consensus
  - distributed-systems
  - paper-notes
date: 2024-04-24
updated: 2026-07-30
status: evergreen
description: Notes on Lamport's Paxos Made Simple. Follows the paper's derivation of the protocol from its safety requirements, then covers learners, progress, and the multi-instance state machine construction.
sources:
  - title: Paxos Made Simple (Lamport, 2001)
    url: https://lamport.azurewebsites.net/pubs/paxos-simple.pdf
    type: paper
---

## Purpose

Notes on [Paxos Made Simple](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf). The paper derives Paxos by starting from the safety requirements of consensus and strengthening constraints until an algorithm falls out. These notes follow that derivation, since the chain of constraints is what makes the protocol make sense.

## The problem

Consider a set of processes that can propose values. A consensus algorithm ensures that a single value is chosen and agreed upon. For safety, we must have:

- Only proposed values are chosen
- Only a single value is chosen
- Processes only learn values that are actually chosen

The setting is an asynchronous, non-Byzantine network in which nodes are fail-stop: they may crash and restart, and messages may be lost or duplicated, but nothing lies.

## Choosing a value

Paxos has three agent roles, and a single process can play several at once:

- *proposers*
- *acceptors*
- *learners*

A value is chosen when a majority of acceptors accept a proposal with that value. Any two majorities intersect, which is the fact everything below leans on.

### P1: An acceptor must accept the first proposal it receives

This guarantees some value gets accepted whenever anyone proposes, but with multiple proposers it allows splits where no single proposal reaches a majority. So proposals get unique numbers, acceptors may accept more than one proposal, and we track proposals as (number, value) pairs.

### P2: If a proposal with value $v$ is chosen, then every higher-numbered proposal that is chosen has value $v$

This is exactly the single-value guarantee, restated to allow multiple proposals to be chosen so long as they all carry the same value. The rest of the derivation strengthens P2 into something implementable.

#### P2a: If a proposal with value $v$ is chosen, then every higher-numbered proposal accepted by any acceptor has value $v$

A proposal is chosen only if it is accepted, so P2a implies P2. But P2a conflicts with P1. Suppose an acceptor that has been asleep the whole time wakes up having accepted nothing, and a proposer that never heard of the chosen value issues a higher-numbered proposal with a different value. P1 forces the sleepy acceptor to accept it, which violates P2a. So push the burden onto the proposers instead:

#### P2b: If a proposal with value $v$ is chosen, then every higher-numbered proposal issued by any proposer has value $v$

Proposers now have to remember and stay consistent with the chosen value before issuing anything. We have:

$$
\text{P2b} \implies \text{P2a} \implies \text{P2}
$$

To implement P2b, constrain how a proposer picks its value:

#### P2c: For any $v$ and $n$, if a proposal with value $v$ and number $n$ is issued, there is a set $S$ consisting of a majority of acceptors such that either (a) no acceptor in $S$ has accepted any proposal numbered less than $n$, or (b) $v$ is the value of the highest-numbered proposal among all proposals numbered less than $n$ accepted by the acceptors in $S$

Maintaining P2c as an invariant satisfies P2b. To keep the invariant, a proposer issuing proposal $n$ must learn the highest-numbered accepted proposal below $n$ from some majority, and propose that value if one exists. Learning about the past is easy; the trick is preventing the future from invalidating what you learned, which is what the promise in the prepare phase does.

### Proposition algorithm

1. A proposer chooses a new proposal number $n$ and sends a *prepare* request to each member of some set of acceptors, awaiting a response containing:
    - A promise that this acceptor will never accept a proposal numbered less than $n$
    - The highest-numbered proposal below $n$ that it has accepted, if any
2. If the proposer receives responses from a majority of acceptors, it issues an *accept* request with number $n$ and value $v$, where $v$ is the value of the highest-numbered proposal among the responses, or a value of the proposer's choice if the responses reported no proposals.

### Acceptor behavior

Acceptors receive only *prepare* and *accept* requests, and can ignore any request without compromising safety (at the cost of liveness). An acceptor needs one rule:

#### P1a: An acceptor can accept a proposal numbered $n$ iff it has not responded to a *prepare* request numbered greater than $n$

P1a implies P1.

### The two phases

#### Phase 1

- (a) A proposer selects a proposal number $n$ and sends a *prepare* request with number $n$ to a majority of acceptors.
- (b) If an acceptor receives a *prepare* request with number $n$ greater than any it has seen, it responds with a promise not to accept any proposal numbered less than $n$, along with the highest-numbered proposal (and value) it has accepted.

#### Phase 2

- (a) If the proposer receives responses from a majority of acceptors, it sends an *accept* request to each acceptor with number $n$ and value $v$, where $v$ is the value of the highest-numbered proposal among the responses, or a value of its choosing if no proposals were reported.
- (b) If an acceptor receives an *accept* request numbered $n$, it accepts the proposal unless it has already responded to a *prepare* request with a number greater than $n$.

As a performance tweak, an acceptor that ignores a request because it has promised a higher number can send the proposer a *reject* so the proposer stops retrying. Correctness does not depend on this.

## Learning a chosen value

One option is for each acceptor to notify every learner whenever it accepts a proposal, which costs a lot of messages. The alternative is a set of *distinguished* learners that hear from the acceptors and relay majority acceptances to the other learners. A larger distinguished set tolerates more failures and costs more communication.

Because messages can be dropped, a value can be chosen without any learner finding out. A learner that wants to know can force the issue by having a proposer run the protocol again, since any new proposal must surface the chosen value.

## Progress

Two proposers can one-up each other forever, each new prepare invalidating the other's pending accept, so no proposal ever completes. The remedy is a single *distinguished* proposer, the only one allowed to issue proposals, with a new one elected if it fails. By [FLP](https://groups.csail.mit.edu/tds/papers/Lynch/jacm85.pdf), any such election mechanism must rely on randomness or on real time (timeouts) to guarantee progress.

## Implementing a state machine

Consider clients issuing commands to a cluster of single-threaded application servers. Each server is a deterministic state machine, so the servers end in the same state exactly when they execute the same commands in the same order.

Run a separate instance of Paxos for each log slot: the value chosen by instance $i$ is the $i$th command every server executes. During normal operation one server is elected leader and acts as the distinguished proposer. Clients send requests to the leader, which assigns them to slots. Any individual instance can fail or stall, but no instance can ever choose two different commands for the same slot.

When a new leader takes over, some slots may be undecided. The new leader runs phase 1 for all such instances at once, including the infinitely many slots beyond the current log (one prepare message can cover them all, since phase 1 does not depend on the value). Where phase 1 surfaces an accepted value, the leader proposes it. Slots that remain unconstrained below the highest accepted command get filled with no-op proposals, and the leader must decide them before executing any command that comes after those slots.

Afterwards the leader proposes further client commands with phase 2 alone, which the paper notes is the minimal message cost achievable for consensus once phase 1 is out of the way. The leader may propose command $i + \alpha$ before knowing the outcome of command $i$, so it can run up to $\alpha - 1$ commands ahead in the worst case where everything in between was dropped.

If a single leader fails to emerge, safety still holds. Only progress suffers.

## Sources

- [Paxos Made Simple](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf)
- [Impossibility of Distributed Consensus with One Faulty Process](https://groups.csail.mit.edu/tds/papers/Lynch/jacm85.pdf)

## Related notes

- [[distributed-systems/paxos-intro|Paxos introduction]]
- [[distributed-systems/paxos-architecture|Paxos architecture]]
