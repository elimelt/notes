---
title: Primary Backup
category: distributed-systems
tags: primary backup, distributed systems, consistency, availability, view service, split brain
description: Explains the concept of primary backups in distributed systems, including state machine replication and the view service.
---

# Primary Backup

Consider a highly available stateful service. It is easy to maintain *consistency* within one node, simply by performing operations in some well-defined (**serializable**) order. However, providing both availability **and** consistency is more of a challenge. One must provide a notion of having a single system, even if a server within the system fails.

## Single Node KV Store

Consider an instance of redis with multiple clients reading and writing to it. You can think of this system more abstractly as a state machine, where each client applies an operation that changes the state of the system.

### State Machine Replication

Replicate state machines across multiple servers. If you apply the same set of operations to each server in the same order, their ending states **must** be in the same state. This holds so long as the effect of each operation is deterministic.

#### Example: Virtual Machine Replication

Take a single VM running a single application. Create $n$ copies of this VM, and feed each instance the exact same inputs (packets, interrupts, instructions). Then, all $n$ VMs will have the same behavior.

Any time you introduce randomness into a system, you need to ensure that the randomness is deterministic. This mechanism for VM replication assumes you are only using a single core, and all operations are deterministic.

### Two Servers (Primary-Backup)

At any given time, clients speak to only one server (the **primary**). Data is replicated on primary and backup servers, and if the primary fails, the backup is elected as the new primary.

The goals of doing this is to increase the availability and reliability of the system in the face of failures.

#### Basic Operations

- Clients send operations (`put`, `get`) to the primary.
- Primary decides the order of operations.
- Primary forwards operations to the backup.
- Backup applies operations in the same order as the primary (hot standby), or just saves a log of the operations (cold standby).
- After backup applies the operation, primary replies to the client.

#### Key Assumptions
- Every replica executes deterministically as a function of inputs.
- If randomness is used, it must be deterministic (use the same seed).
- Replicate single core servers.

#### Key Challenges

- There can only be one primary at a time.
    - Primary, backup, and clients all need to agree on who the primary is.
    - State at primary must be consistent with all previous operations.
- Needs to operate despite failures of primary or backup.
    - Must handle dropped/duplicated messages and arbitrary delays.

### The View Service

The **view service** is a server that provides a consistent view of the system. Clients ask the view service for the primary server's address in order to find out where to send operations. Even if the view server incorrectly identifies failure, the system will still be consistent.

The view server is the only authority on who the primary is. This makes it a single point of failure. The hard part is that we need to be able to guarantee only one primary at a time, while not needing to ping the view server on every operation.

This system needs to be able to tolerate any individual server failing, while still serving client requests.

#### Detecting Server Failures

- Each server periodically sends an RCP ping ot the view server.
- The view server is dead if its missed $n$ pings in a row, and alive if it has received a single ping.

When the view server detects a failure, a new **view** (state of the system sent in ping responses) is created.

#### Primary Failures

- View server detects failure through lack of pings (some sort of timeout after missing $n$ pings).
- View server declares new view with backup as new primary, and if any idle servers are available, a new backup as well.
    - Requests eventually time out and check in with view server.
- View server sends new view in all subsequent responses.
- New primary hears new view and sends state to new backup
- Backup initializes state and sends acknowledgment to new primary.
- New primary pings current view to view server (after receiving ack).
- Client hears about new view and starts sending operations to new primary. If any operations were lost, client resends them.


If primary dies with no idle servers available, then the backup becomes the primary and there is no backup.

#### Managing Servers

Keep a pool of idle servers that can be promoted to backup. If primary dies, create new view with old backup as primary and idle server as backup. If the backup dies, create a new view with idle server as new backup.:

### Split Brain

In the case where a primary appears to be offline, but is really just partitioned from the view server, the view server may elect a new primary. This leads to a **split brain** scenario, where two primaries are elected.

The important part is that two servers can **think** they are the primary, but it can **never** be the case that two servers **act** as the primary.

## Rules

1. Primary in view $i + 1$ must have been the backup, or the primary in view $i$ (besides the first view).
2. Primary must wait for backup to accept/execute each operation before replying to client (if there is one).
3. Backup must accept forwarded requests only if view is correct.
4. Non-primary must reject client requests.
5. Every operation must be before or after state transfers (not during).
