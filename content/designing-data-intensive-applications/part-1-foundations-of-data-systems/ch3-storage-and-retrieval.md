---
title: Storage and Retrieval Techniques for Database Systems
category: Database Systems
tags:
  - data-structures
  - indexing
  - oltp-vs-olap
  - column-oriented-storage
date: 2023-12-20
updated: 2026-07-30
status: evergreen
description: Reading notes on chapter 3 of Designing Data-Intensive Applications. Covers log-structured storage, hash indexes, LSM-trees versus B-trees, OLTP versus OLAP, and column-oriented storage.
sources:
  - title: Designing Data-Intensive Applications, Martin Kleppmann
    url: https://dataintensive.net/
    type: book
---

## Purpose

Reading notes on chapter 3 of [Designing Data-Intensive Applications](https://dataintensive.net/) by Martin Kleppmann. The chapter builds storage engines up from an append-only log, then contrasts the index structures behind OLTP systems with the column-oriented layouts behind analytics.

## The simplest possible database

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

Because the storage is a log, writes are $O(1)$ appends and reads are $O(n)$ scans. That trade already makes log-structured storage a good fit for append-only workloads such as event sourcing. To make reads faster we add an index, an additional structure derived from the primary data. Every index trades write performance for read performance, since writes now have to update the index as well as the primary data.

## Hash indexes

A hash index maps keys to byte offsets in the data file. Lookups by exact key are fast; range queries are not, since adjacent keys land in unrelated buckets. Store the log-structured key-value data in a binary format and use the in-memory hash table to find each key's offset. Deletes work by writing a tombstone record, and periodic compaction rewrites segments without the dead keys.

Crash recovery has a few options:

- Reread the log from beginning to end, rebuilding the hash table in memory. Slow, but needs no extra storage.
- Snapshot the hash table to disk periodically. Faster recovery at the cost of extra storage.
- Add checksums so partially written records can be detected and discarded.

For concurrency, keep a single write thread and multiple read threads. Writes serialize, reads parallelize.

## SSTables and LSM-trees

A Sorted String Table (SSTable) stores key-value pairs sorted by key. Segments are organized by time: reads search from the most recent segment backwards, and a background process merges older segments. Because segments are sorted, merging works like mergesort, keeping only the most recent value for each key, and range queries are fast. A sparse in-memory index of byte offsets is enough, since sorted order lets you scan from the nearest indexed key.

A Log-Structured Merge Tree (LSM-tree) is the combination of an in-memory balanced tree with on-disk SSTables. The simplified algorithm used by LevelDB, and similarly by Cassandra and HBase (both inspired by Bigtable):

- When a write comes in, add it to an in-memory balanced tree (the memtable).
- When the memtable exceeds some threshold, typically a few megabytes, write it out to disk as an SSTable file. Writes continue to a fresh memtable meanwhile.
- On a read, check the memtable first, then the most recent on-disk segment, then progressively older segments.
- Periodically merge and compact segment files in the background.

Lucene, the index engine behind Elasticsearch and Solr, uses a similar scheme for its term dictionary. Words are the keys and the values are posting lists, the ids of documents containing each word. The term dictionary lives in SSTable-like files that are merged periodically.

### Performance optimizations

A Bloom filter is a memory-efficient structure that approximates set membership, giving false positives but never false negatives. LSM-tree reads consult one per segment to skip SSTables that cannot contain the key, which protects the read path for missing keys.

Compaction strategy also matters. Size-tiered compaction merges segments once they reach a certain size. Leveled compaction keeps key ranges split across smaller per-level SSTables. Either way, keeping writes append-only keeps write throughput high.

## B-trees vs. LSM-trees

B-trees trade write speed for read speed. A B-tree is an n-ary tree with sorted keys in every node, updated in place a page at a time. A high branching factor keeps the tree shallow, which minimizes disk seeks.

LSM-trees trade read speed for write speed. Writes are sequential appends; reads may touch several segments. Write amplification, meaning multiple physical writes to disk per logical database write, affects both structures, but LSM-trees usually sustain higher write throughput.

Compaction can hurt LSM-tree read performance, especially at high percentiles of read latency, since compaction competes with foreground requests for disk bandwidth. Keeping few SSTables per level mitigates this. With high enough write throughput you also have to monitor disk space, because compaction can fall behind incoming writes and leave unmerged segments accumulating.

## Secondary indexes

A secondary index is an index on something other than the primary key, so values are not necessarily unique. It can be built from a hash index (still bad for range queries) or a B-tree or LSM-tree (good for range queries, slower writes). As in full-text search, the value for each key can be a list of matching records, which is exactly an inverted index.

### What lives inside the index

You choose between storing a reference to the row or storing the row itself in the index. A heap file holds the actual rows, and indexes point into it. Updates can happen in place when the new value fits in the old slot; otherwise the row moves and either the index or a forwarding pointer at the old location gets updated, which adds a level of indirection to reads.

A clustered index stores row data directly in the index, which suits read-heavy workloads at the cost of space and slower updates. InnoDB, the MySQL storage engine, clusters the table on the primary key, and secondary indexes point at the primary key rather than a heap location. SQL Server allows one clustered index per table.

B-trees handle one-dimensional keys well but do poorly on multi-dimensional queries. R-trees handle multi-dimensional indexing at the cost of complexity. Fuzzy indexes handle approximate matches in full-text search: Lucene keeps an in-memory finite state automaton over the characters of each key, similar to a trie, which supports matching within a given edit distance.

## Keeping everything in memory

As RAM gets cheaper, keeping the whole dataset in memory becomes viable. In-memory databases offer low latency and high throughput, and their real advantage is avoiding the overhead of encoding data structures for disk rather than avoiding disk reads, since a disk-based engine with a large cache rarely touches disk on reads anyway. Crash recovery is the hard part. A write-ahead log makes recovery possible but slows writes. Redis offers weak durability by writing to disk asynchronously. Some in-memory databases can exceed available RAM by evicting cold values to disk, cache-style.

## Transaction processing or analytics?

OLTP (online transaction processing) serves real-time stateful workloads where low latency and high availability matter. An enterprise typically runs several OLTP systems side by side, with ACID transactions, concurrency control, and the index structures above.

OLAP (online analytics processing) serves batch analysis: a read-only copy of the data, loaded and queried in bulk for business intelligence, reporting, and data mining. Availability matters less, and a single query is allowed to hog resources. Data warehouses are the OLAP counterpart to the OLTP indexes above, and they use different schemas and storage layouts.

### Star and snowflake schemas

A star schema has a single fact table containing the events you want to query and multiple dimension tables holding the attributes you want to filter and group by. The fact table carries foreign keys into the dimension tables. A snowflake schema further normalizes the dimension tables into sub-tables, which saves space and complicates queries.

Warehouses get huge, petabytes in some cases, because facts are events kept long term. Fact tables are also wide, often hundreds of columns.

## Column-oriented storage

```sql
SELECT
 dim_date.weekday, dim_product.category,
 SUM(fact_sales.quantity) AS quantity_sold
FROM fact_sales
 JOIN dim_date ON fact_sales.date_key = dim_date.date_key
 JOIN dim_product ON fact_sales.product_sk = dim_product.product_sk
WHERE
 dim_date.year = 2013 AND
 dim_product.category IN ('Fresh fruit', 'Candy')
GROUP BY
 dim_date.weekday, dim_product.category;
```

Transactional databases store data row-oriented, so answering the query above loads entire rows even though it touches a handful of columns. Column-oriented storage lays out each column contiguously, so a query reads only the columns it uses, which saves enormous I/O on wide tables. Values within a column are similar to each other, so columns also compress well, with bitmap encoding plus run-length encoding as the standard tricks. Compressed columns additionally suit vectorized processing, where SIMD instructions operate on many values at once ([C++ SIMD example from UW CSE 333](https://courses.cs.washington.edu/courses/cse333/23au/lectures/27/code/cpp_simd_example.tar.gz)).

### Sort order in column storage

Rows can be kept ordered by a chosen sort key, with secondary sort keys breaking ties. Sorting enables fast range queries on the sort key, improves compression (long runs of duplicates run-length encode well), and gives sequential reads better locality. A store can even maintain the same data redundantly in several different sort orders and pick the best one per query, which C-Store did and Vertica productized.

### Writing to column-oriented storage

All these read optimizations make in-place writes slow. The fix is the LSM-tree approach again: buffer writes in memory, then periodically merge them into the compressed column files.

### Aggregation: data cubes and materialized views

A materialized view is a precomputed, stored query result, usually a join or aggregation. It speeds up the queries it covers and costs write overhead to maintain, which is acceptable in a read-heavy warehouse. A data cube takes this further by precomputing aggregates along every combination of several dimensions, essentially a multi-dimensional array of totals. Cubes are expensive to maintain and inflexible for queries they do not cover. Often the better path is to store raw data, find the slow queries by measuring, and only then precompute aggregates for those queries.

## Sources

- [Designing Data-Intensive Applications](https://dataintensive.net/), Martin Kleppmann, chapter 3

## Related notes

- [[designing-data-intensive-applications/part-1-foundations-of-data-systems/ch2-data-models-and-query-languages|data models]]
- [[designing-data-intensive-applications/part-2-distributed-data/ch5-replication|replication]]
