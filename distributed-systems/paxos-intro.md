# Paxos Introduction

## FLP Impossibility Result

It's impossible for a deterministic protocol to guarantee consensus in bounded time in an asynchronous distributed system. The progress and safety of a system are at odds with each other.

Paxos makes the decision to always be safe, and is able to make progress and avoid blocking as long as the majority of nodes are up and there aren't further failures.

## State Machine Replication

Order events/operations into an append-only log. Consensus is easy if only one client request is handled at a time.

Select a leader for clients to send requests to, and define the ordering at that leader. If any leader fails or is slow, elect a new leader (can keep doing this repeatedly). Then, each leader proposes a value that all nodes should agree on.

Leader election is where Paxos comes in.

## Paxos, the algorithm

```plaintext
Proposer:
  Prepare(n) -> Promise(n, n', v')
  Accept(n, v) -> Accepted(n, v)

Acceptor:
  Promise(n, n', v') -> Prepare(n)
  Accepted(n, v) -> Accept(n, v)
```

### Phase 1: Prepare

- Proposer selects a proposal number $n$ and sends `Prepare(n)` to all (or a majority) of acceptors.
- Acceptors respond with `Promise(n, n', v')` where $n'$ is the highest proposal number it has accepted, and $v'$ is the value associated with that proposal number.
  - If $n > n'$, the acceptor promises not to accept any proposal with a number less than $n$.
  - Proposer must wait for a majority of responses before proceeding.

### Phase 2: Accept

- If the proposer receives a majority of promises, it sends `Accept(n_max, v_max)` to all acceptors (the maximal value received in reply).
- Each acceptor that is able to accept the proposal responds with `Accepted(n_max, v_max)`.
- If a majority of acceptors respond, the proposal is chosen.

