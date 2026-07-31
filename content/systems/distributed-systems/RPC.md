---
title: Remote Procedure Call (RPC)
aliases:
  - distributed-systems/RPC
category: Distributed Systems
tags:
  - distributed-systems
  - rpc
  - communication
  - fault-model
date: 2024-03-26
updated: 2026-07-30
status: draft
description: How RPC differs from a local call, the fault model it runs under, at-least-once versus at-most-once semantics, and why the two generals problem makes exactly-once hard.
sources:
  - title: Protocol Buffers documentation
    url: https://protobuf.dev
    type: docs
---

## Purpose

An RPC is a request from a client to execute a function on a server on a different machine. To the client it looks like a local function call. To the server it looks like an implementation of a function call. This note covers what that illusion hides. Underneath sit a fault model, delivery semantics that weaken when messages drop, and a hard limit on agreement over a lossy channel.

## Local procedure call

- The caller invokes a function by name with args.
    - Args pass in registers, extras push onto the stack.
    - The return program counter (%rip) pushes onto the stack.
    - Control jumps to the first instruction (entry point) of the callee.
- The callee executes the function and returns to the caller.
    - It reads params from registers and the stack.
    - It computes the function, possibly updating state.
    - It jumps back to the next instruction after the call.

The compiler defines the protocol for this call. Nothing gets lost between caller and callee.

## Remote procedure call

- On the client, a stub implements a function that looks like a local call.
    - Parameters are *marshalled* into a message (arbitrary types).
    - The message is sent to the server (possibly in multiple packets).
    - The client waits for a response.
- On the server, the real function runs.
    - The server *unmarshals* (parses) the message.
    - It computes the function, possibly updating state.
    - It *marshals* the return value into a message (possibly multiple packets).
    - It sends the message back to the client.

Client and server stubs are usually auto-generated from a procedure spec, as with Google's [Protocol Buffers](https://protobuf.dev).

## RPC vs. local procedure call

### Binding

- The client needs a connection to the server.
- The server must implement the required function.
- The server needs to run a compatible version of the function.

### Service discovery

A discovery service keeps track of all available services, including versions, schemas, and locations, so clients can find a server to bind to.

### Interface description language (IDL)

Serialization matters. An IDL like protobuf generates client and server serialization stubs automatically. Procedure args can be values or pointers, and they need to be assembled into a single linear message in a transportable format. That format is not always a string; protobuf uses a binary encoding.

### Failures

- Packets can be lost, reordered, or duplicated.
- The client or server can crash at any time, before, during, or after the call.
- The server or network can be slow, and the client can time out.

TCP mitigates some network issues, but sockets fail, and messages are not always transmitted over TCP anyway.

## Fault model

- **Asynchronous fail-stop nodes**
    - A computer may be arbitrarily slow while still working.
    - Nodes always fail by stopping, before transmitting garbage or forgetting state. This is a strong assumption. For arbitrarily behaving nodes, see *Byzantine fault tolerance*.
- **Network model**
    - Messages can be lost, delayed, reordered, or duplicated, and can be arbitrarily delayed while the network still works correctly.
    - Messages won't be corrupted (bit flips). Another strong assumption. See error detection and correction for working without it.
    - The network may partition nodes from each other, so nodes can end up in isolated groups with no connection between them.
    - The network is commutative and transitive: if A can talk to B, then B can talk to A, and if A can talk to B and B can talk to C, then A can talk to C.
- Clients make only one RPC request at a time, a very strong assumption.

## Naive RPC

- **Nodes**
    - Any number of stateless clients and servers.
    - Servers perform some computation when they receive a message, then reply.
- **Messages**
    - Client request and server response.
    - The client request contains the IP addresses of client and server, the procedure name, and the arguments.
    - The server response contains the IP addresses of client and server and the results of the procedure.

## Client timeout and retry

If a request or reply message drops, the client waits forever. A client timer with retransmission fixes this, where the client resends the request if no response arrives in time. Retransmission then causes duplication and reordering at the server.

Unique request IDs handle the duplication. Include a message ID in each request and reply, reuse the same ID on retransmit, and let the server ignore duplicates it has already processed.

### RPC semantics

- **At least once**
    - Client resends on timeout, server executes every copy of the request that arrives.
    - If the client gets a response, it knows the server executed the request at least once. Otherwise it doesn't know whether the server executed the request at all.
- **At most once**
    - The server executes only the first copy that arrives.
    - If the client gets a reply, it knows the server executed the request exactly once. Otherwise it doesn't know whether the server executed it, though it knows it ran at most once.
- **Exactly once**
    - The server executes the request exactly once.
    - Requires a unique request ID and a server that remembers the ID and the result of the request, along with unbounded retries.

#### At least once

The client should do a finite number of retries, eventually giving up and returning an error to the caller.

This only works if the operation is **idempotent**, meaning repeated execution has the same effect as a single one. All read-only operations are idempotent. Many writes are not: incrementing a counter is not idempotent, while setting the counter to a value is.

Does TCP solve this? Not really, despite being reliable. Most RPCs travel over TCP, which guarantees in-order delivery with retransmission and duplicate detection. It still cannot give exactly-once semantics. If the server crashes after processing the request and before sending the response, the client retransmits and the server executes the request again.

**End to end principle**: functionality should be implemented where it can be completely handled, rather than partially handled at each layer. Handling retries at the RPC layer rather than trusting TCP is an instance of this.

Examples of idempotent workloads:

| Example | Explanation |
|---|---|
| DNS lookup | Queries are read-only, so they are idempotent |
| MapReduce | The Map phase is a pure function, so it is idempotent |
| NFS | If the client maintains the offset, reading or writing a block is idempotent |

With multiple clients, operations like `Put(k, v)` stop being safely retryable in the read-modify-write sense, since the value of `k` can change between the time one client reads it and the time it writes it back.

## Two generals problem

A thought experiment that shows the hard limit on agreement over a lossy channel. Two generals coordinate an attack on a city. A valley separates them, and they communicate only by messenger. The city can capture the messenger, and the sender never learns whether the message arrived. The generals can only attack together, so they must agree on a time.

The problem is that after sending any message, the sender cannot know it was delivered. No number of confirmation round trips helps, because the last message sent could always have been the one that dropped. This limit shows up all over distributed systems, for example in the commit problem that [[systems/distributed-systems/two-phase-commit|two-phase commit]] addresses.

## To look into

- Remote Direct Memory Access (RDMA)
- Network File System (NFS)

## Related notes

- [[systems/distributed-systems/two-phase-commit|two-phase commit]]
- [[systems/distributed-systems/primary-backup|primary backup]]
