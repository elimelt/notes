# Google File System (GFS)

[reading](https://static.googleusercontent.com/media/research.google.com/en//archive/gfs-sosp2003.pdf)


## Introduction

GFS differs from more traditional file systems in a lot of ways. Particularly...

- Fault tolerance/expecting failures as the common case, since it runs on commodity hardware
- Huge (multi-GB) files are the norm
- Read/Append access patterns are common, while updates and random writes are rare. Particularly, the system is optimized for large streaming (sequential) reads and appends.

## Design Overview

### Assumptions

- Built with commodity hardware, and is thus failure prone and needs to constantly monitor, detect, and tolerate failures
- Typically storing a modest number of large files. Anywhere from a few million ~100 MB files, to multi-GB files. The system should be optimized for working with these large files.
- Two types of workloads:
  - large streaming reads spanning > 1 MB
  - smaller random reads (which are often batched)
- Well defined semantics and easy concurrency control for concurrent appends are essential. A common application of GFS is to be used as a producer-consumer queue
- High sustained bandwidth takes precedence over latency

### Interface

Although familiar, GFS is not POSIX compliant. Files are organized hierarchically in directories and identified by path names, supporting *create, delete, open, close, read,* and *write*. Additionally, supports *snapshot* and *record append*. Snapshot creates a copy of a file or directory tree. Record append allows multiple clients to append data to the same file concurrently while guaranteeing the atomicity of each individual record.

### Architecture

A GFS cluster is composed of a single *master*, and multiple *chunkservers*, and is accessed by multiple *clients*. Each component is typically run on a commodity Linux machine running a user-level server process, and it isn't uncommon to run both a client and chunkserver on the same machine (although this comes at a reliability cost).

Files are made of fixed-size *chunks*, identified by an immutable and globally unique 64 bit *chunk handle* which is assigned by the master at the time of creation. Chunkservers store chunks as Linux files on local disk, and read/write to specified chunk handle and byte ranges. Each chunk is replicated on multiple chunkservers (by default with three replicas, but is configurable).

The master maintains all filesystem metadata, including the namespace, access control information, file to chunk and chunk to server mappings, etc. The master communicates with chunkservers through a *HeartBeat*, which is a two-way message that allows the master to monitor and instruct the chunkservers and chunkservers to report their status.

GFS client libraries are linked in each application. All metadata updates go through the master, but simple data-bearing communication goes directly to the respective chunkserver.There is no need to go through something like the Linux vnode layer, which is a major benefit of not supporting POSIX.

Neither clients nor chunkservers cache file data, but clients will typically cache metadata. Technically, chunkservers do cache file data in that they use Linux files, and thus have a buffer cache for frequently accessed data in memory, but this is transparent to GFS.

### Single Master

Using a single master architecture vastly simplifies things, since we can use global knowledge of the filesystem at the master for replication and chunk placement. To help this scale, the master's level of involvement in reads/writes needs to be minimized.

#### Common Case Read

1. Client translates file name and byte offset to chunk index locally
2. Requests chunk handle and replica locations from master
3. Client caches the result with the file name and byte offset
4. Client chooses replica (often the closest) and reads/writes while their cache entry is still valid

Note that for almost no extra cost, steps 1 and 2 can be batched for many files/chunks.

### Chunk Size

GFS uses 64 MB lazily allocated (to mitigate internal fragmentation) chunks, each of which are stored as a plain Linux file. Using such large chunks has many benefits, including allowing clients to cache plenty of metadata, reducing network overhead/load of metadata acquisition, and allows for in-memory metadata at the master.

Large chunk sizes also have their disadvantages, including leading to hotspots for chunkservers with many smaller files. One such example is when you have an executable stored in GFS that you want to concurrently read and execute across many hundreds of machines, this leads to a temporary overload of those chunk servers. This was fixed by using a higher replication factor, and staggering starting times. **Extension**: peer to peer sharing (between clients) is a possible solution to hotspots.

### Metadata

There are three main types of metadata, all of which is stored in-memory in the master.

- File and chunk namespaces
- File to chunk mappings
- Location of each chunk's replicas

The first two are also persisted in an *operation log* stored on the master's local disk. The last however, is not persisted, and instead on startup/when a new chunkserver joins the cluster, the master requests metadata about the chunks stored locally.

#### In-Memory Data Structures

The master stores metadata in memory and goes fast! Additionally, this allows it to quickly scan through its entire state, making things like garbage collection, re-replication on failures, and migration for load balancing possible.

"b-b-bbbut that's nOt sCaLabLE" - someone right now probably

In reality, if the metadata were a limiting factor for your system, you would have a MASSIVE amount of data, and would need to be using a very under-specced machine as the master. Each 64 MB chunk only requires ~64 bytes of metadata, and namespace metadata is compressed using prefix compression (which is very effective for filesystems). Therefore, adding even an extra few GB of memory to your master would allow you to store a huge amount of additional metadata.

#### Chunk Locations

As stated previously, the master doesn't persist the location of chunks, instead opting to poll chunkservers on startup. This design choice simplifies things greatly, and is a general approach to fault tolerance, in that it would have been an uphill battle trying to maintain a globally consistent and persistent view of the system, since chunkservers can partially fail, and they ultimately know best which chunks they have.

#### Operation Log

The operation log is not only the sole persistent metadata in the system, but also defines the order in which concurrent operations are executed. The log is replicated remotely, and changes are batched and flushed to disk. The log is replayed on startup, but is also kept small by being checkpointed with a memory-serializable compact B-tree structure, making recovery faster. The master can create a checkpoint in a separate background thread, allowing concurrent operations to be executed. Once created, the checkpoint is written to disk both locally and remotely.

### Consistency Model

#### Guarantees by GFS

File namespace mutations are atomic through being done exclusively at the master with locking. File mutations have looser guarantees, particularly at the level of defined, and undefined regions

- Defined:
  - After a data mutation, the file is in a consistent state and the mutation was universally applied without being interrupted
- Undefined:
  - All clients will see the same data, but the data may not be consistent with any single mutation (i.e. interleaved)
  - Successful concurrent mutations leave a region consistent but undefined, whereas failed concurrent mutations leave it undefined and inconsistent.

After a sequence of successful mutations, the file is guaranteed to be defined and to contain the data written by the last mutation. GFS achieves this by...

- Applying mutations to chunks in a consistent order across replicas
- Using chunk version numbers to detect stale replicas (due to missed mutations)

Once a chunk becomes stale, it is no longer returned to the client, and is garbage collected ASAP. Since clients cache chunk metadata, there is a window of time in which a client will read from stale chunks, but this typically presents as reading a premature end of chunk (in the case of append workloads).

Component failures can lead to corrupted or destroyed data, but this is mitigated by checksumming files. Once a problem is detected, the data is restored from a valid replica if possible. In the (uncommon) case where all replicas are lost before the master can react, the data is unavailable, but corrupted data is never returned.

#### Implications for Applications

Long story short, you should always prefer appends over random writes. Note that GFS has "append at least once" semantics, and can also insert arbitrary padding between appends. It is thus important to use techniques like structuring your data and using unique identifiers for non-idempotent log entries.

## System Interactions

### Lease and Mutation Order

A mutation is any change to the contents of a chunk. Each mutation is performed at all replicas. Mutations are carried out as follows:

1. Master grants a *lease* (~60 sec) to one of the replicas, making it the *primary*
2. The primary chooses a serial order for all mutations to the chunk
3. All replicas execute the mutations in the order defined by the primary

Leases can be extended, and the extensions are piggybacked through HeartBeat messages. The master can also revoke a lease, although if it loses communication with the primary it only needs to wait for the lease to expire.

A write can be carried out through the following:

1. The client asks the master which chunkserver holds the current lease, and the locations of other replicas. If no lease is held, the master grants one to a replica of its choice
2. The master replies with the identity of the primary and location of replicas (secondaries), which is cached by the client
3. The client pushes data to all replicas, which is stored by an LRU buffer cache until the data is used or expires
4. Once all replicas have acknowledged receiving the data, the client sends a write request to the primary, which identifies the data that the client just pushed. The primary assigns consecutive sequence numbers to all mutations it receives (possibly from other clients as well), and then applies the mutations locally
5. The primary forwards the write request to all secondary replica, and the replicas apply the mutations in the same order defined by the primary.
6. The secondaries ack that they completed the operation
7. The primary replies to the client, and any errors are reported to the client. Errors leave the region in an inconsistent state, but the failed mutation is usually retried multiple times, until eventually falling back to redoing the entire write.