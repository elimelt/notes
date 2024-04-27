# Distributed Mutual Exclusion

We want the same old mutual exclusion via locking, but in a distributed system. The trick is to keep a consistent ordering of locking events on every node in the system.

## Implementation

Each message carries a timestamp $T_m$, and a sequence number $s$.

There are three message types:

- `request` (broadcast)
- `release` (broadcast)
- `acknowledge` (on receipt)

Each node maintains:

- a `queue<request>` ordered by $T_m$
- a `map` of the last message received on each node in the system

On request receive:

- Record $T_m$
- Add request to queue

On receiving release:

- Record $T_m$
- Remove request from queue

On acknowledge receive:

- Record $T_m$

To acquire the lock:

- Broadcast `request` message
- Acquired once...
  - `request` at head of queue
  - Everyone else has sent a later-timestamped message
  - so `request` is the earliest in the queue