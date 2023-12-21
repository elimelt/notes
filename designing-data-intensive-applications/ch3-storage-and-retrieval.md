# Chapter 3
## Storage and Retrieval

```bash
#!/bin/bash

# instant database
db_set () {
 echo "$1,$2" >> database
}
db_get () {
 grep "^$1," database | sed -e "s/^$1,//" | tail -n 1
}
```

The fact that it is a log makes this...sort of performant. Writes are fast O(1), and reads are slow O(n). The log-structured storage engine is a good fit for append-only workloads, such as event sourcing.

To make reads faster, we can use an **index**. An index is an additional structure that is derived from the primary data. This is a trade-off between write performance and read performance, since writes now have to update the index as well as the primary data.

### Hash Indexes

Map keys to offsets in the data file. This is fast for equality queries, but not for range queries. Store log-structured key-value data like above in binary format, and use a hash index to find the offset of the key in the data file. **Delete** by marking the key as deleted in the data file (sometimes with a "tombstone"), and periodically reindexing the data file to remove the deleted keys.

For **crash recovery**:
- reread log file from beginning to end, building hash table indicies in memory (slow, but no additional storage)
- store snapshots of the hash table indicies to disk periodically (fast, but requires additional storage)
- use checksums to detect partial corruption of the hash table indicies (fast, but requires additional storage)

For concurrency, maintain a single write thread, and multiple read threads. Writes are serialized, but reads can be parallelized.

### SSTables and LSM-Trees

**Sorted String Tables** (SSTables) are a way to store key-value data in sorted order. Keep data sectioned based on time range, and search from most to least recent, periodically merging previous sections of data. Should store key value pairs, as well as byte offset metadata. Range queries are fast, and merge operations can be optimized by keeping most recent record and merging ranges at a time. However, both reading and writing are slower than hash indexes.

Can use B-Trees to store SSTables on disk, or various balanced binary trees (e.g. AVL, red-black, etc.). These are called **Log-Structured Merge Trees** (LSM-Trees).

Below is a simplified version of the algorithm used by LevelDB, which is similar to the one used by Cassandra and HBase (which were inspired by Bigtable):

- When a write comes in, add it to an in-memory balanced tree data structure (memtable).
- When the memtable gets bigger than some threshold, typically a few megabytes, write it out to disk as an SSTable file. While the SSTable is being written out to disk, writes can continue to a new memtable instance.
- On read request, first try memtable, then in the most recent on-disk segment, then in the next-older segment, etc.
- Periodically merge and coalesce segment files.

**Lucene** (used by Elasticsearch and Solr) uses a similar algorithm for its term-dictionary indexes that support full-text search. It uses a **log-structured merge (LSM) tree** to merge segments of the term dictionary. Here, words are the keys, and the values are the list of documents that contain the word (in a "Posting List"). This is kept in SSTables, and merged periodically.

### Performance Optimizations

**Bloom filters** are a way to avoid reading SSTables that don't contain a key. They are a memory-efficient data structure for approximating the contents of a set. Give false positives, but no false negatives. Can be used to avoid reading SSTables that don't contain a key.

**Merge strategies** such as size-tiered, where segments are merged when they reach a certain size, or leveled, where segments are kept in subranges.

Keeping things append-only is a good way to keep throughput for writes high.

### B-Trees vs LSM-Trees

B-trees trade off write speed for read speed. N-ary tree with sorted keys in every node. Increase branch factor for maximal locality and minimal disk seeks.

LSM-trees trade off read speed for write speed. Writes are sequential, but reads are not. Writes are batched, and reads are parallelized. **Write amplifacation** (multiple writes to disk for a single DB write) can be a problem on both B-trees and LSM-trees. However, LSM-trees often still have a higher write throughput.

Compaction can impact LSM-tree read performance, but can be mitigated by keeping a small number of SSTables per level, and by using a merge strategy that does not require reading all SSTables. Still, it can impact high percentiles of read latency.

With high enough write throughput, it is also important to monitor disk space usage, since compaction can be slow enough that it doesn't keep up with the incoming writes.

### Secondary Indexes

**Secondary indexes** are indexes on non-primary keys. They can be implemented with hash indicies (still bad for range-queries), or with B-trees (good for range queries, but slower writes). They can also be implemented with LSM-trees. Similar to the setup for full-text search (Posting Lists), can use a list of matching records as a value in an index (**inverted index**).

### Storing Indexes

Must choose between storing references, or data directly in the index. Storing references is more space efficient update-friendly, but requires more disk seeks. Storing data directly in the index is more read friendly, but requires more disk space, and makes updates slower.

**Heap files** let you store data referenced in your index and update in place when the new data fits in the space of the old data. Otherwise, you have to move the data to a new location, and update the index (or heap file with redirect pointer). However, this extra indirection can slow down reads.

Directly storing data in the index **(clustered index)** is good for read-heavy workloads, and storing references is good for write-heavy workloads. InnoDB (MySQL storage engine) uses a clustered index for primary keys, and a secondary index point directly to the primary key (instead of a heap file). SQLServer let you specify one clustered index per table.

B-trees are good for one-dimensional indexes, but not for **multi-dimensional indexes**. **R-trees** are a good alternative for multi-dimensional indexes, but are more complex.

**Fuzzy indexes** are often used in full-text search. They are good for matching similar words, but not for exact matches. Lucene keeps an in-memory finite state automaton over characters in each key that is similar to a trie, allowing for fuzzy matching to a certain "edit distance".

### Keeping everything in memory

As RAM gets cheaper, it makes more sense to keep data in memory. **In-memory databases** are good for applications that need low latency and high throughput, but make crash recovery more difficult. **Write-ahead logs** are a good way to make crash recovery easier, but can slow down writes. Some databases (e.g. Redis) let you choose between durability and performance, and have "weak durability" by asyncronously writing to disk. Some in-memory databases can even exceed the amount of RAM available by using an eviction policy similar to a cache.


### Transaction Processing or Analytics?

