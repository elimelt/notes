---
title: Consistent Global State in Distributed Systems
category: distributed-systems
tags: consistent global state, distributed systems, global predicate evaluation, asynchronous distributed systems
description: Explains the concept of maintaining a consistent global state in distributed systems and its implications.
---

# Consistent Global State in Distributed Systems

[reading](https://courses.cs.washington.edu/courses/csep552/18wi/papers/chapt4.pdf)

## Introduction

Many problems in distributed computing boil down to being able to maintain a consistent global state, and to run predicates on that state in order to trigger events. The true state of a distributed system is the union of all node's states. However, since nodes don't share memory, the actual state must be meaningful when inferred solely based on messages passed among nodes.

A global state is said to be *inconsistent* if it never could have been constructed by an ideal external observer. This paper formalizes this concept into the context of a **Global Predicate Evaluation (GPE)**, which determines if the system satisfies some predicate $\Phi$.

## Asynchronous Distributed Systems

Define a distributed system as a set $P$ of *sequential* processes $p_1, p_2, \ldots, p_n$, and a network consisting of *channels* in which unidirectional communication is possible in the space of $P^2$. The network is assumed to be reliable, but may deliver messages out of order, and is taken to be *strongly connected*, but not necessarily *fully connected* (i.e. communication may require intermediate message passing).

It is useful to reason about distributed systems with the weakest possible assumptions, such that results hold for arbitrary systems.

## Distributed Computations

A distributed computation is the execution of a distributed program over a collection of processes, each of which sequentially process a stream of *events*. Particularly, for two nodes to communicate, a message $m$ is enqueued on a channel via $send(m)$, and the message is dequeued via $receive(m)$. There is an obvious relationship between the happening of event $send(m)$ at process $p$, and the happening of event $receive(m)$ at process $q$, such that we can be sure $send(m)$ happened before $receive(m)$.

