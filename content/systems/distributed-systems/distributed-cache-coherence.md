---
title: Distributed Cache Coherence
aliases:
  - distributed-systems/distributed-cache-coherence
category: Distributed Systems
tags:
  - cache coherence
  - consistency-models
  - distributed-systems
  - leases
date: 2024-05-17
updated: 2026-07-30
status: evergreen
description: How leases give linearizable caching, why that approach scales poorly, and how NFS and DNS get away with weaker consistency instead.
sources:
  - title: "Leases: An Efficient Fault-Tolerant Mechanism for Distributed File Cache Consistency"
    url: https://dl.acm.org/doi/10.1145/74851.74870
    type: paper
  - title: Computer systems lecture notes
    type: lecture
---

## Purpose

This note covers keeping cached copies of mutable data consistent across nodes. Leases get you linearizable caching, and it is worth understanding exactly what they cost, because most large systems (NFS, DNS, most of the web) deliberately pay for less.

## Core idea

When linearizability matters, any duplication of mutable data across nodes must be kept consistent. That is cache coherence: every node sees the same view of the data. The mechanism below builds coherence out of leases, and the weaknesses of that mechanism explain why weaker consistency is so common.

## Distributed caching with leases

A **lease** is a time-limited right to do something. Here, holding a lease grants the right to cache some data.

Time-limiting is what makes leases fault tolerant. If a node holding a lease fails, everyone else just waits for the lease to expire. A live holder can renew its lease and keep caching.

### Cache reads

1. A cache obtains a lease along with the data.
2. Nobody can modify the data until the lease expires or is revoked, so the server must track who holds which data and until when.
3. Once the lease expires, the value can change. Nothing is cached at that point, so the only copy is at the server, and subsequent caches fetch the new data.

This is linearizable and fault tolerant, since a failed holder's lease eventually expires on its own. It scales poorly, because the server holds state for every cached item.

Clients can cache values too. The server forwards the lease along with the data to the client.

### Cache updates

Leases let the server get back to a single copy whether caches are up or not. The naive update path waits for every outstanding lease to time out before each write.

The optimized path uses callbacks, avoiding the wait when nothing has failed. On receiving an update for a cached value, the server sends an invalidation to every node holding a copy, waits for all of them to respond or for their leases to expire, then applies the update.

Either way, the requirement is the same. For linearizability there must be exactly one copy of the data while it is being updated.

### Lease timeouts

Using one timeout value for all leases means less state at the server and a shorter worst-case wait to reclaim every lease. Using varied timeouts staggers renewal requests, so the server doesn't get slammed by every cache renewing at once. Pick based on which failure mode you fear more.

## Weaknesses of linearizable caches

- Server state grows linearly with the number of cached items
- During an update nobody can read the item, and a failed cache stretches that window to the full lease time
- More copies means more chances some holder is down, so updates wait for lease expiry more often

## Caching widely shared data

For widely shared data, snapshot-read consistency is often fine: reads may return stale data. Much of the web works this way. The usual shape is many read-only caches plus a single writable copy, with updates propagating from the writable copy out to the caches.

## Examples

### Sun Network File System (NFS)

NFS is a protocol for accessing a remote shared file system that appears as a local directory (via mount in Unix). Open, close, read, and write are RPCs to a remote server. Reads and writes are block oriented rather than positional, so the server keeps no per-client state and every operation is idempotent.

The stateless server gives simple failure handling. If the server crashes, a client just waits for reboot and resends, with at-least-once RPC semantics, no callbacks, and no error handling needed in client applications.

Clients locally cache file data and metadata, and the caches are eventually consistent:

- Each cache entry has a TTL, and the local copy is revalidated on the next access after the TTL expires (3 to 30 seconds)
- Updates are sent back to the server after a similar delay
- Metadata such as directories and file status uses shorter TTLs, file data uses longer ones

This works well when resources aren't shared, meaning everyone works in their own directory. Concurrent sharing through NFS can serve stale data within the TTL window.

### Domain Name System (DNS)

DNS translates domain names to IP addresses. Servers are stateless, with at-least-once semantics for fetching records. Resolution is hierarchical so each domain manages its own names: ask the root for `com`, then `com` for `google.com`, then `google.com` for `www.google.com`.

DNS is eventually consistent. Clients cache at each level, updates go directly to the relevant name server, and clients only discover changes after the TTL expires. Domain owners set TTLs, which vary widely and can even be infinite. CDN records typically use short TTLs so traffic can move quickly when a server fails.

## Caching terminology

- **Write through**: the cache holds read-only data. Writes go to the store, and the store revokes outstanding copies. Exploits locality for reads.
- **Write back**: the cache holds read-write data, so updates happen client side too, as in NFS. The cache writes locally and asks the store to revoke other copies. Exploits locality for reads and writes.

### Write back cache coherence

On a write:

- Send invalidations to all caches
- Each cache invalidates and responds, possibly with updated data
- Wait for all invalidations, then return

Reads proceed whenever a local copy exists. The server must order concurrent requests to avoid deadlock.

Write back caching creates a durability problem, since a cache failure can lose writes that haven't reached the store. Two options:

- Periodic distributed checkpoints, restarting from the last checkpoint if any cache fails. Appropriate for long-running background computations.
- Send a log of changes to replicated storage. If a cache fails, read its log back from storage. This is how a backup takes over from a failed primary in [[systems/distributed-systems/primary-backup|primary-backup replication]], by replaying the log.

## Related notes

- [[systems/distributed-systems/consistency|consistency]]
- [[systems/distributed-systems/primary-backup|primary-backup replication]]
