---
title: Two Phase Commit
category: distributed-systems
tags: two-phase commit, distributed transactions, atomicity, durability, consistency, isolation, deadlock prevention, distributed systems
description: Explains the concept of two phase commit in distributed systems and its implications.
---

# Two Phase Commit

## ACID

For updates that span multiple keys, or even multiple updates across different storage systems, we need all-or-nothing semantics so errors can be properly handled. Two-phase commit (2PC) is a protocol that ensures **distributed transactions**, i.e. groups of operations, are atomic, consistent, isolated, and durable (ACID). 

| Term | Description |
|--------|--------------------------------|
| Atomic | operations appear to either happen as a group, or not at all |
| Durable | Operations that complete stay completed |
| Isolation | Other transactions don't see the results until of earlier transactions unless they were already committed
| Consistency | linearizability (or some other consistency model) |


## Two Phase Locking (2PL) - Consistency and Isolation


In **2PL**, locks are acquired on all structures touched during the transaction, and are only released upon commit or abort. This provides isolation and consistency for multi-key transactions.

```plaintext
- start transaction -
Phase 1: acquire locks
- commit or abort -
Phase 2: release locks
```

## Redo Logging - Atomicity and Durability

Log all changes to disk, followed by a log commit. If there is a crash before the log commit, abandon the transaction. If it was committed in the log, we can just redo the changes.


## Deadlock

Deadlock is when two or more transactions are waiting for locks held by each other in a cycle. To solve this you can stop one of the transactions to break the cycle.

Deadlock prevention is generally a better idea, and you can achieve it by always ordering lock acquisition consistently.

## Distributed Transactions

From the *two generals problem*, it is theoretically impossible to agree on performing some action at the same time. Instead, we agree in **virtual time** when an operation happens.

### Atomic Commit Protocol (ACP)

- Every node arrives at the same decision
- Once a node decides, it never changes
- Transaction is committed only if all nodes vote yes
- If all processes vote yes the transaction is usually committed
- If all failures are eventually repaired, the transaction is eventually either committed or aborted

## 2PC in Detail

**2PC** is a blocking protocol, meaning that it makes no progress if some participants are unavailable. It has fault tolerance, but is not highly available, which is a fundamental limit of the protocol.

- For a given transaction a central coordinator sends a prepare
- Participants commit to commit
  - Acquires locks, prevent/delay conflicting operations
  - Abort if deadlock or if any of the operations cannot be completed
- Central coordinator decides and tells everyone, then releases all locks

### Handling Failures

#### Participant Fails Before Sending Response

You can maintain a timer on the coordinator to retry prepares. If some threshold is reached, just log a no and abort

If the participant then comes back online, they will need to ask the coordinator for the decision, at which point the coordinator sends an abort to the participant

#### Participant Fails Before After Sending Vote

If the participant crashes immediately after sending their response. Then either they come back online before the commit is sent, at which point the protocol continues, or they will need to check their log and request the decision from the coordinator, which will resent the commit and the protocol continues.

#### Coordinator Fails Before Sending Prepare

They would have logged the prepare request, so when they come back online and execute the transaction.

#### Coordinator Fails After Sending Prepare

If the coordinator fails after sending prepares, but before receiving responses, they must have logged the prepared already, and they need to be resent.

### Roles

- Participants: Nodes that must update data relevant to the transaction
- Coordinator: node responsible for executing the protocol (might also be a participant)

### Messages

- Prepare: Can you commit the transaction?
- Commit: commit the transaction
- Abort: abort the transaction
