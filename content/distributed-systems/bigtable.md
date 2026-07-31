---
title: Bigtable, A Distributed Storage System for Structured Data
category: Distributed Systems
tags:
  - bigtable
  - distributed-storage
  - google
  - paper-notes
date: 2024-05-17
updated: 2026-07-30
status: evergreen
description: Paper notes on Bigtable (OSDI 2006) covering its data model, tablet architecture, use of GFS and Chubby, and the refinements that make reads and recovery fast.
sources:
  - title: "Bigtable: A Distributed Storage System for Structured Data (OSDI 2006)"
    url: https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf
    type: paper
---

## Purpose

Notes on the [Bigtable paper](https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf). I care about the data model, how tablets get located and assigned, and the list of refinements at the end, since those are the parts that keep showing up in later storage systems.

## Problem

Google needed one storage system that could serve workloads as different as throughput-oriented batch jobs and latency-sensitive user-facing products (Personalized Search, Google Earth, Google Analytics, all as of 2006), while scaling to petabytes across thousands of commodity machines. A full relational model was more than these applications needed, and existing databases did not scale this way.

## Main idea

Bigtable is a sparse, distributed, persistent, multi-dimensional sorted map. The map is indexed by a row key, a column key, and a timestamp. The value of each cell is an uninterpreted array of bytes:

```text
(row:string, column:string, time:int64) -> string
```

The model is deliberately simple. Clients get dynamic control over data layout and format, and because the system sorts by row key, schema design directly controls locality. Clients can reason about where their data lives, including whether it is served from memory or disk.

### Rows

Row keys are arbitrary strings up to 64KB. Every read or write of a single row is atomic, which makes concurrent updates to the same row easy to reason about.

Data is kept in lexicographic order by row key. The row range of a table is dynamically partitioned into ranges called *tablets*, the unit of distribution and load balancing. Reads over short row ranges therefore touch only a few machines. Users should exploit this. The paper's example is storing webpage content keyed by reversed domain name, so pages from the same domain sit adjacent and host-level analyses stay local.

### Column families

Column keys are grouped into sets called column *families*, written as `<family>:<qualifier>`. Both parts are strings, though family names must be printable. Data in the same family is usually the same type, though the system does not enforce that. A table can have an unbounded number of columns, but the number of families should stay small, in the hundreds at most, since families are the unit of access control and locality tuning.

### Timestamps

Each cell holds multiple versions of its data indexed by a 64-bit timestamp. Clients can assign timestamps themselves or let Bigtable assign real time in microseconds at execution. Versions are stored in decreasing timestamp order, so the most recent version is the cheapest to read.

Garbage collection is configurable per family: keep the last $n$ versions, or keep versions within a time window, and rules can be combined.

**Extension idea (mine, not the paper's)**: it would be nice to define rules that keep progressively sparser snapshots as records age, similar in spirit to level tiering in an LSM tree.

## API

The base API provides:

- Reads and writes of individual and multiple cells
- Reads and writes of a row, and reads over multiple rows
- Creating and deleting tables and column families
- Changing cluster, table, and column family metadata such as access control
- Single-row transactions (no multi-row transactions)
- Client-side batching of writes across row keys
- Cells used as integer counters
- Input source and output sink integration for MapReduce

## Building blocks

Bigtable stores log and data files in [[distributed-systems/google-file-system|GFS]]. On-disk data uses the *SSTable* format, a persistent, ordered, immutable map from byte-string keys to byte-string values. An SSTable supports point lookups and range iteration. Internally it is a sequence of blocks (64KB by default, configurable) with a block index at the end of the file. The index is loaded into memory when the SSTable is opened, so a lookup is a binary search in memory to find the block, then one disk seek to read and scan it. An SSTable can also be mapped fully into memory to avoid disk entirely.

Bigtable also depends on *Chubby*, Google's distributed lock service, which runs a five-node Paxos group with one leader serving requests. Chubby provides locks and small-file storage, and Bigtable uses it for:

- Master election
- Storing the bootstrap location of Bigtable data
- Discovering tablet servers and finalizing their deaths
- Storing schema information and access control metadata

## Mechanism

The implementation has three components: a client library, one master, and many tablet servers. The master assigns tablets to tablet servers, drives garbage collection, and handles schema changes. Tablet servers each manage a set of tablets, typically 10 to 1000 per server, and can be added or removed to match load. Clients rarely talk to the master since data moves through tablet servers directly, so the master stays lightly loaded and does not bottleneck the system.

A Bigtable *cluster* stores a number of tables, each made of tablets, each tablet holding all data for a row range. A table starts as one tablet and splits automatically as it grows, targeting 100 to 200 MB per tablet by default.

### Tablet location

Tablet locations live in a three-level hierarchy that behaves like a B+ tree. A Chubby file stores the location of the *root tablet*. The root tablet is the first tablet of a special `METADATA` table and is never split, so the hierarchy stays exactly three levels deep. Each `METADATA` row stores the location of one tablet, keyed by an encoding of that tablet's table identifier and end row. This scheme addresses $2^{34}$ tablets, which at 128 MB per tablet is $2^{61}$ bytes.

The client library caches tablet locations. On a miss it walks up the hierarchy, and with an empty cache location takes three network round trips including one Chubby read. The library also prefetches `METADATA` entries to cut down on misses. `METADATA` additionally carries secondary information such as an event log per tablet, used for debugging.

### Tablet assignment

Each tablet is assigned to one tablet server at a time. When a tablet is unassigned and a server has room, the master sends that server a *tablet load* request.

Chubby tracks tablet server liveness. On startup, a tablet server creates and acquires an exclusive lock on a uniquely named file in a *servers* directory in Chubby, and the master monitors that directory to discover servers. A tablet server serves as long as its file exists and it holds the lock; if the file disappears the server kills itself. When a server is removed deliberately during reconfiguration, it releases its lock gracefully so the master reassigns its tablets quickly.

The master periodically polls each server's lock status. If a server has lost its lock, the master checks Chubby itself for problems, and if Chubby is healthy the master deletes the server's file, which dooms the server, then reassigns its tablets.

When the cluster management system starts a master, it:

1. Acquires the unique *master* lock in Chubby, preventing concurrent masters
2. Scans the servers directory in Chubby
3. Asks every live tablet server for its current tablet assignments
4. Scans the `METADATA` table and marks any unknown tablets as unassigned

The set of tablets changes only on table creation or deletion, and on tablet splits and merges. The master initiates all of these except splits, which the tablet server commits by writing the new tablet's entry directly to `METADATA`.

The master kills itself if its Chubby session expires. This does not change tablet assignments, since assignment state is reconstructed by the next master.

### Tablet serving

Persistent tablet state lives in GFS. Updates go to a *commit log*; the most recent committed updates sit in an in-memory *memtable*, and older updates sit in a sequence of SSTables.

A read is checked for authorization against a Chubby file, then answered from a merged view over the memtable and the tablet's SSTables. A write is checked for authorization, appended to the commit log using group commit, then inserted into the memtable.

### Compactions

When the memtable reaches a threshold it is frozen, converted to an SSTable, written to GFS, and replaced by a fresh memtable. This *minor compaction* shrinks tablet server memory use and reduces how much commit log must be replayed during recovery. Periodically a *major compaction* merges all of a tablet's SSTables into one SSTable containing no deleted data.

## Refinements

### Locality groups

Clients can group column families into a *locality group*, and each locality group gets its own SSTables. Tuning knobs like serving from memory apply per locality group. The `METADATA` table uses the in-memory option for its location family.

### Compression

Clients choose whether and how SSTables for a locality group are compressed, applied per SSTable block. Many clients use a two-pass scheme, first Bentley and McIlroy's algorithm to compress long common strings across a large window, then a fast pass that finds repetitions in a 16 KB window. The scheme favors speed and still compresses well.

### Caching for read performance

Tablet servers keep two caches. The *scan cache* holds key-value pairs returned by the SSTable layer and helps repeated reads. The *block cache* holds SSTable blocks read from GFS and helps sequential and nearby reads.

### Bloom filters

Clients can request a Bloom filter per SSTable, held in tablet server memory. The filter answers whether an SSTable might contain data for a given row and column, so lookups for nonexistent rows skip disk entirely.

### Commit log implementation

Each tablet server writes a single commit log shared by all its tablets, avoiding concurrent writes to many GFS files. Recovery would normally force every new server to read the whole shared log to find its tablets' entries, so instead the log is sorted by key `(table, row name, log sequence number)` before replay. The sort is parallelized by partitioning the log into 64 MB segments sorted on different tablet servers, coordinated by the master.

To mitigate GFS write latency spikes, each server keeps two log-writing threads targeting two different files, only one active at a time. If the active one gets slow, writes switch to the other.

### Speeding up tablet recovery

Before the master moves a tablet, the source server does a minor compaction, stops serving the tablet, then does a second minor compaction to absorb any log state that arrived during the first. The tablet then loads on the target server with no log replay needed.

### Exploiting immutability

SSTables are immutable, so reads need no synchronization and concurrent row access is cheap. The memtable is the only mutable structure read concurrently, and it uses copy-on-write per row to allow parallel reads and writes. Deleted data is removed permanently by mark-and-sweep garbage collection over obsolete SSTables. Immutability also makes splits cheap, since child tablets can keep reading the parent's SSTables instead of rewriting them.

## Evidence

The paper's evaluation shows scaling that is real but far from linear. Going from 1 to 500 tablet servers increased random-read-from-disk throughput by only about 100x, because each random read transfers a 64KB block over the network and the network link saturates. Random reads from memory scaled better, around 300x over the same range.

## Applications

### Google Analytics

Google Analytics embeds a JavaScript snippet in pages, records per-visit information, and surfaces reports to site owners. Two of its Bigtable tables: a raw click table with a row per end-user session, and a summary table of predefined per-site summaries computed periodically by MapReduce over the raw click table. The click table's row keys make sessions for the same site contiguous and chronologically sorted. The paper reports the click table compressing to 14% of its original ~200 TB, and the summary table to 29% of its ~20 TB.

### Google Earth

Google Maps and Google Earth store part of their data in Bigtable, with one table for preprocessing and a set of tables for serving. The preprocessing table stores raw imagery with compression off, since the imagery is already compressed. Each row is one geographic segment, named so adjacent segments sit near each other, and the pipeline leans heavily on MapReduce over Bigtable. The serving system indexes data in GFS through a single table that is small, around 500 GB, but serves tens of thousands of queries per second, so it runs on hundreds of tablet servers with in-memory column families.

## Related notes

- [[distributed-systems/google-file-system|Google File System]]
- [[distributed-systems/sharding|sharding]]
