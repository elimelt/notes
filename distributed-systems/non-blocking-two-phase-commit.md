# Non-Blocking Two Phase Commit

Regular 2PC is blocking because we need to wait for **all** nodes to agree that an operation is commit-able. There are massive performance implications to read-only transactions (could fix with snapshot reads) and lock contention. We can fix this by relying on Paxos.

We make the coordinator as well as each participant a Paxos group with its own shard, and then we can just wait until all groups agree to an operation.

## 2PC on Paxos

1. Client requests multi-key operation at coordinator
2. Coordinator logs request
3. Coordinator sends prepare
4. Participants decide to commit/abort, and log result
5. Coordinator sends a commit/abort
6. Participants record results

## Multi-Key Transactions in a KV Store

Assuming reader-writer locking scheme, and that the application code runs on the client:

- RPCs to storage layer to start/end transactions, and read/write values
- KV store acquires/releases locks and does read/write operations
- Keep KV store simple so application logic is easy to change
- Server can abandon transaction and release locks if needed (e.g. if the client fails)

The basic approach is to:

- Read and write objects during execution
  - Contact the appropriate paxos group leader and acquire any locks
- Client decides to commit and notifies coordinator
  - Coordinator contacts all shards and sends `prepare` message
  - Prepare log entry is replicated throughout group
  - Group votes to either send `ok` or `abort`
- If all contacted shards vote `ok`, coordinator sends `commit` message
  - Each shard replicates `commit` entry in log
  - Leader released locks

## Caution: Deadlocks

Deadlocks are very easy to trigger when performing operations across shards. A general solution is to always kill things that need to wait. For instance, with a checking/savings account at a bank:

- Two clients execute the same exact transaction concurrently
  - Both get read locks on accounts, so neither can acquire write locks and the transaction stalls
- Two clients, one moves from savings to checking, and the other from checking to savings
  - Each gets read lock, neither can get write lock, so transaction stalls

Deadlocks can be an issue in sharded systems when moving shards across groups.

## Google's Bigtable in Retrospect

Jeff Dean of Google said that not supporting distributed transactions was the biggest mistake in the the design of Bigtable. Incremental updates make it a very important feature, so users really wanted them and often tried to implement it themselves on top of Bigtable

Spanner, Google's multi-datacenter KV store uses 2PC over Paxos, and is one of the backbones of Google's ad service.
