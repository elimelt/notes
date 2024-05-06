# Distributed Architectures with Paxos

## Overhead of Simple Architectures

Paxos can make progress so long as a majority of nodes are up. For a Paxos group of size $k$, requires a general overhead of $3(k-1) + 2$ messages.

Primary-backup (with a single backup) using a view server has an overhead of $4$ messages to forward requests. It can handle any one failure.

Using a single server has an overhead of $2$ messages to service a request, and cannot handle any failures.

The above demonstrates a clear tradeoff between the overhead of the system and the number of failures that can be tolerated.

## Paxos as a Lease Server

A lease is a time-limited right to do something. They rely on loosely synchronized clocks, and are used to avoid the overhead of Paxos for every operation. A typical lease term is around a few seconds, plus or minus some epsilon to account for clock drift. If a lease holder fails, the system just waits for the lease to expire.

The following workflow is used to implement leases:

1. The lease is granted to the primary
2. Primary serves requests until the lease expires, forwarding to the backup
3. If the primary doesn't renew the lease (i.e. fails), a lease is granted to the next primary

This design pattern is used in BigTable, Chubby, and ZooKeeper. It prevents split brain if the clock drift is within epsilon. We also only need to service reads on the primary, including logic for cache invalidation. Additionally, we can use write ahead logging, and instead of explicitly maintaining a backup, just replace the primary by executing the log on a new primary.






