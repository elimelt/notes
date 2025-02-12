---
title: Bigtable, A Distributed Storage System for Structured Data
category: distributed-systems
tags: Bigtable, Distributed Storage, Google
description: A highly scalable, reliable, and fault-tolerant distributed storage system designed for structured data. Built by Google, it uses a combination of commodity hardware and software to provide low-latency, high-throughput access to large amounts of data.
---

# Bigtable: A Distributed Storage System for Structured Data

[Bigtable Paper](https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf)


## Introduction

Bigtable is a widely applicable, scalable, highly performant, and highly available database that is used by many of Google's services including Personalized Search, Google Earth, Google Analytics, and more (as of 2006). It is able to handle various workloads, ranging from throughput-oriented batch processing jobs, to latency sensitive end user applications, and it is able to scale up to petabytes of data across thousands of commodity machines.

Bigtable supports a simple data model that supports dynamic control over data layout and format, allowing clients to reason about the locality of their data in the underlying storage. It indexes data by row and column names which are arbitrary strings, and data is stored as uninterpreted strings. Clients are able to control the locality and storage location (in memory or from disk) via their schema design.

## Data Model

Under the hood, Bigtable is a sparse, distributed, persistent multi-dimensional sorted map. The map is indexed by a row key, column key, and a timestamp; each cell in the map is indexed by these three keys. The row key is a string, the column key is a pair of strings (column family and column qualifier), and the timestamp is a 64-bit integer. The value of the cell is an uninterpreted array of bytes.

`(row:string, column:string, time:int64) -> string`

### Rows

Row keys are arbitrary strings up to 64KB in size. Every read/write of a single row key is atomic, making it easier to reason about concurrent updates to the same row.

Bigtable maintains data in lexicographic order by row key. The row range for a table is dynamically partitioned, each range being called a *tablet*, which is the unit of distribution/load balancing. This makes reads over short row ranges efficient, usually only requiring communication with a small number of machines to complete. This property can and should be exploited by users to make their regular access patterns more efficient. For instance, storing webpage content indexed via reversed domain groups all shared subdomains closer together, making host and domain analyses more efficient.

### Column Families

Column *keys* are grouped into sets called column *families*. All data stored in the same family is usually of the same type, although this isn't constrained by the system. Whereas tables can have an unbounded number of columns, the number of column families should remain relatively small (in the hundreds at most).

Column keys are defined as `<family>:<qualifier>`, both of which are strings, although family names must be printable.

### Timestamps

Each cell maintains multiple versions of your data indexed by timestamp. You can either assign timestamps yourself, or let Bigtable do it at execution time, in which case they represent "real time" in microseconds. Versions are stored in decreasing order, such that you always have the most recent version as the highest locality version.

You can also specify garbage collection conditions, like only keeping the last `n` versions of a cell, or only keeping versions within a certain time range. Furthermore, you can intersect, union, and nest garbage collection rulesets.

**Extension**: it would be nice if you could define rules for keeping progressively sparser "snapshots" as records get older, similar to an LSM tree.

## API

Applications can interact with Bigtable through a wide variety of client libraries, but the base API  provides functions for...

- Reading and writing individual and multiple cells
- Reading and writing a row
- Reading multiple rows
- Creating and deleting tables and column families
- Changing cluster, table, and column family metadata (like access control rights)
- Single row transactions (no multi-row transactions)
- Batching writes across row keys at the client
- Cells as integer counters
- Input source and output sink for MapReduce jobs

## Building Blocks

Bigtable uses Google's distributed filesystem, *GFS*, for storing log and data files. The *SSTable* file format is used for storing data on disk, which provides a persistent, ordered immutable map from keys to values, where both keys and values are arbitrary byte strings. You can look up a specific key, as well as iterate over all kv pairs in a specified key range. Internally, each SSTable contains a sequence of blocks (typically 64KB in size, but configurable), with indices stored at the end of the table and loaded into memory when the SSTable is opened. After loading the index, lookups can be done with a single disk seek, or the table can optionally be loaded entirely into memory to avoid needing to go to disk at all. First, the block containing the key is found by binary search, then the block is read and scanned linearly for the key.

Additionally, Bigtable uses *Chubby*, Google's distributed lock service, which is running a 5 active node paxos group under the hood, one of which is leader and serves requests. Chubby provides a simple API for creating and managing locks, and for storing small files. It uses Chubby for a wide variety of tasks, including...

- Master election
- Storing bootstrap location of Bigtable data
- Discover and reconfigure/finalize deaths of tablet servers
- Store schema information and access control metadata

## Implementation

Made up of three major components:

- A client library
- One master server, responsible for assigning tablets to tablet servers, garbage collection, schema changes, etc.
- Many tablet servers, which manage a set of tablets (typically 10-1000/server), and can be added and removed dynamically to cope with changing load

Most clients rarely ever communicate with the master since their data is accessed through tablet servers, so it is under relatively small load, and doesn't become a bottleneck.

A Bigtable *cluster* stores a number of tables, each consisting of a set of tablets, each tablet containing all the data associated with a row range. Initially, each table is just one tablet, but it grows, automatically splitting and load balancing to each tablet being ~100-200 MB by default.

### Tablet Location

Bigtable uses a three-level hierarchy similar to a B+ tree to store tablet location information. The *root tablet* is the first level, and its location is stored in a Chubby file. The root tablet stores the location of all tablets in a special `METADATA` table, and each `METADATA` tablet contains the location of a set of user tablets. The root tablet is really just the first tablet in the `METADATA` table, and it is treated specially to never be split so there are only ever three levels of indirection.

The next level of indirection in the hierarchy is the rest of the `METADATA` table, which stores the location of an end tablet under a row key which encodes the tablet's table identifier and end row.

This scheme is sufficient to store $2^{34}$ tablets, or $2^{61}$ bytes in 128 MB tablets.

The client library caches tablet locations, and on cache miss recursively moves up the tablet location hierarchy searching for said tablet. If the cache is empty, the location algorithm requires three network round trips, including a read to Chubby. Additionally, the client library prefetches entries from the `METADATA` table to try and reduce the number of cache misses.

Finally, the `METADATA` table contains secondary information, including a log of all events pertaining to each tablet.

### Tablet Assignment

Each tablet is assigned to a single tablet server at a time, and the master manages the assignment of tablets to servers. When there is an unassigned tablet and a tablet server with adequate room, the master assigns the tablet by sending a *tablet load* request to the server.

Bigtable uses Chubby to keep track of tablet servers. On tablet server startup it creates and acquires an exclusive lock on a uniquely named file in Chubby in the *servers* directory. The master monitors this directory to discover new tablet servers. Tablet servers use Chubby sessions, and continue to function until the file no longer exists, at which point they kill themselves. When tablet servers are manually removed in reconfiguration, the server will attempt to release its lock gracefully so the master reassigns its tablets more quickly.

The master periodically polls the tablet servers' lock status, and if it detects any issues it reassigns the offending server's tablets. At this point, the master also checks Chubby to see if there are any issues apart from the tablet server itself, and if not then the master deletes the tablet server's file, effectively dooming it.

When the master is started by the cluster management system, it does the following:

1. Acquires the unique *master* lock in Chubby, which prevents multiple master instantiations
2. Scans the servers directory in Chubby
3. Communicates with every live tablet server to discover the current tablet assignments
4. Scans the `METADATA` table and adds any not previously learned tablets to the unassigned set

The set of tablets only ever changes when one is created or deleted, or when they are merged or split. The leader does all but merges, and merges are handled by the tablet server writing directly to the `METADATA` table.

Also, the master kills itself if its session with Chubby ever expires, but this doesn't change the assignment of tablets to tablet servers.

### Tablet Serving

The persistent state of each tablet is stored in GFS. Updates are stored in a *commit log*, with the most recently committed updates being stored in-memory in a *memtable*, and older updates being stored in a sequence of SSTables.

On a read operation, the authorization is checked via a Chubby file, and then the SSTables for the tablet are scanned and merged to form the result of the read. Write operations are first checked for authorization, and then get added to the commit log using *group commit*, after which the contents are inserted into the memtable.

### Compactions

The memtable grows on each write operation until a certain threshold, at which point the memtable is frozen and converted to an SSTable and written to GFS, being replaced by a new memtable. This *minor compaction* process both shrinks memory usage of tablet servers, and reduces the amount of data needed to be read from the commit log during recovery.

Periodically, *major compaction* takes place, where all SSTables are merged into a single SSTable containing no deleted data.

## Refinements

### Locality Groups

Clients can group multiple column families into a *locality group*, each of which get their own SSTable. Tuning characteristics like loading SSTables into memory can be specified for locality groups, which is a feature used on the `METADATA` table.

### Compression

Clients can control whether or not, and if so how SSTables for locality groups are compressed. Compression schemes are applied to each SSTable block. Many clients use a two pass approach, which first uses *Bentley and McIlroy's* scheme, compressing long common strings across a large window. In the second pass, repetitions in a small window (16 KB) are searched for and compressed. This compression scheme prioritizes speed over size, although it does well at both metrics.

### Caching for read performance

Tablet servers use two levels of caching:

- Scan cache
  - Caches kv pairs returned by the SSTable
  - Useful for repeated reads
- Block cache
  - Caches SSTable blocks read from GFS
  - Useful for locality/sequential reads

### Bloom filters

Clients can specify that SSTables be created with a bloom filter in the tablet server's memory, reducing the number of disk accesses required for read operations by preventing many lookups for non-existent rows

### Commit-log implementation

The commit logs for different tablets are all actually a single commit log on the tablet server, preventing us from needing to concurrently write to many different files in GFS.

On recovery, instead of reading the entire log to find only the tablets assigned to you, the log is sorted by keys `(table, row name, log sequence number)`. This sorting is parallelized by partitioning the log file into 64 MB segments which are each sorted in parallel on different tablet servers, being coordinated by the master.

To mitigate GFS writing latency spikes, two separate threads are maintained, writing to two different files. If one is performing badly, the other one starts, but only one writes at a time.

### Speeding up tablet recovery

Before the master moves a tablet, the source tablet server does an initial minor compaction on the tablet, after which it stops serving the tablet, performing one more minor compaction to eliminate any state in the log that came in after the first compaction, and then the tablet is unloaded on this server and loaded onto the other server.

### Exploiting immutability

Since SSTables are immutable, no synchronization needs to be done when reading from SSTables, and concurrent row accesses can be implemented efficiently. The only mutable concurrently accessed data structure is the memtable, which is optimized with row copy-on-write, allowing parallel reads and writes.

To permanently remove deleted data, the table is  mark and sweep garbage collected.

Additionally, since SSTables are immutable, when splitting tablets the children can continue to rely on the parent's SSTable, not needing to create two new SSTables.

## Performance Evaluation

Although scaling relatively well, it is not perfectly linear with the number of servers in the cluster. In particular, for random reads from disk, increasing the number of servers from 1 to 500 only increased the throughput by a factor of ~100. For random reads in particular, transferring 64KB blocks over the network for every read ends up saturating the network link, becoming a bottleneck. Random reads from memory on the other had saw a ~300 times increase in throughput.

## Real Applications

### Google Analytics

*Google Analytics* (analytics.google.com) is a service that helps analyze traffic patterns to websites. To enable the service, a small JavaScript program is embedded in a web page, which is invoked whenever the page is visited. It records various information like a user identifier, information about the page, etc., and the data is made available in Google Analytics to the website owner.

Two of the tables stored in Bigtable used by this service are the raw click table, which maintains a row for each end-user session, and the summary table, containing various predefined summaries for each website. The summary table is periodically computed via a Map-Reduce job over the raw click table. The click table's schema is designed so that sessions that visit the same website are contiguous and sorted chronologically, and the table is able to be compressed to 14% its original size (~200 TB). The summary table is able to be compressed to 29% of its original size (~20 TB).

### Google Earth

The data used by both Google Maps (maps.google.com) and Google Earth (earth.google.com) are partially stored in Bigtable. The system uses one table to preprocess data, and another set of tables for serving client data.

The preprocessing pipeline uses one table to store raw image data (with compression turned off since it is handled manually). During preprocessing, the images are cleaned and consolidated into the final serving data. Each row in the preprocessing table corresponds to a single geographic segment, and rows are named so that adjacent geographic segments are stored near eachother. This preprocessing pipeline relies heavily on MapReduce over Bigtable.

The serving system uses a single table to index data stored in GFS. Although its relatively small (500 GB), it serves tens of thousands of queries per second, so it is hosted on hundreds of tablet servers to load balance, each containing in-memory column families.
