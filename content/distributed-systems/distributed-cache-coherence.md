---
title: Linearizable Caches
category: Distributed Systems
tags: Cache Coherence, Consistency Models, Distributed Systems
description: A linearizable cache is a cache that provides strong consistency guarantees for reads and writes. It is a type of cache coherence protocol that ensures all copies of data are consistent with each other, even in the presence of failures or network partitions.
---

# Distributed Cache Coherence

When linearizability is a concern, any duplication of mutable data across multiple nodes must be kept consistent. This is the problem of cache coherence: ensuring that all nodes in a distributed system have the same view of the data.

## Distributed Caching with Leases

A **lease** is a time-limited right to do something. In the context of distributed caching, our lease gives us a right to cache some data.

If a node holding the lease fails, we just wait for the lease to expire. Leases can be renewed by the holder, so long as the node is still up.

### Cache Reads

1. Cache obtains a lease containing the data
2. No one can modify the data until the lease either expires or is revoked. Thus, a server/service needs to track who has which data and for how long
3. Once the lease expires, the value can then change. The items is no longer cached by anyone, so it can only be copied at the server. All subsequent caches can refetch the new data.

This approach is both linearizable and fault tolerant, since the lease will eventually expire if the node holding it fails, allowing another node to take over. However, this approach is not very scalable, since the server needs to maintain state for every cached item.

Clients are also able to cache values, and you can do this by forwarding the lease along with the data to the client.


### Cache Updates

Leases allow the server to reclaim a single copy, regardless of whether caches are up or not. A naive approach would be to wait for all copies to timeout any time you want to update.

An optimized version would be to use a callback, preventing the need for timeouts if no error occurs. When the server receives an update for a cached value, it forwards an invalidation/revoke to all nodes with a copy of the data, and waits for a response from all (or for the lease to timeout), after which it can proceed with the update.

The key insight however is that in order for your system to be linearizable, you **must** have only one copy of the data while updating.

### Lease Timeouts

If we use the same timeout value for all leases, then we need to track less state at our server, and this also reduces the total time needed to reclaim all leases. On the other hand, if we use different timeouts, then caches will all ask for a new lease at staggered times, preventing an overwhelming number of requests at once.

## Weaknesses of Linearizable Caches

- We need to keep track of a ton of state at a single server, growing linearly with the number of cached items
- While data is updated, nobody can read anything, which can potentially be for a long time leading to high latency
- With more copies, the likelihood of failure, and thus needing to wait for the whole lease time to pass for updates grows

## Caching Widely Shared Data

It's often okay to use snapshot read consistency, allowing for reads to return stale data. Much of the web follows this model.

Usually this would look like having many read only caches and a single copy that is writable, for which updates are propagated from to the caches.

## Examples

### Sun Network File System (NFS)

- Protocol for accessing remote shared file system
- Appears like a local directory (via mount in Unix)
- Open, close, read, write are RPCs to a remote server
  - Instead of maintaining some implicit state about the position in the file, reads/writes are block oriented such that no state needs to be maintained and the operation is idempotent
- Entirely stateless server, such that if the server crashes, a client just needs to wait until it reboots, after which the operation is resent
  - At least once RPC semantics
  - No callbacks
  - Client applications don't need error handling
- Locally caches file metadata and data, which is eventually consistent
- Each cache entry has a TTL
  - Revalidate local copy on next access when TTL expires (3-30 sec)
  - Updates sent back to remote file system after delay (3-30 sec)
- Metadata (e.g. directories, file status) uses shorter TTL
- File data uses longer TTL
- This works well when resources aren't shared, i.e. when everyone works in their own directory

### Domain Name System (DNS)

- Protocol for translating domain names to IP addresses
- Servers are stateless; at least once semantics to fetch data from name servers
- Hierarchical name resolution
  - Allow each domain to manage its own names
  - Ask root: what is the IP address of `com`, then `google.com`, then `www.google.com`
- Eventually consistent in that updates are propagated among servers
  - Clients cache at each level, and updates go directly to the relevant name server.
  - Clients only discover changes after TTL expires
  - TTLs are set by the domain owner (can vary widely, even allowing infinite TTL)
  - CDN servers typically have short TTLs so that they can be updated quickly in the event of a server failure


### Caching Terminology

- **Write Through**:  Cache holds read-only data
  - Write sent to store, and store revokes copies
  - Exploits locality for reads
- **Write Back**: Cache holds read-write data, i.e. updates happen client side too (like NFS)
  - Writes to cache, and cache asks store to revoke copies
  - Exploits locality for reads and writes

#### Write Back Cache Coherence

- On write:
  - Send invalidations to all caches
  - Each cache invalidates, responds (possibly with updated data)
  - Wait for all invalidations
  - Return
- Reads can proceed when there is a local copy
- Requests at server need to be ordered to avoid deadlock

However, with write back caching, durability becomes an issue since a failure might lose writes.

- Option 1: period distributed checkpoint, restart from checkpoint if any cache fails
  - appropriate for long running/background computations
- Option 2: send log of changes to replicated storage
  - if cache fails, read its log from storage
  - e.g. if primary fails, backup can take over by replaying log
