---
title: Distributed Computing for Data Mining
category: Distributed Systems
tags:
  - data mining
  - distributed file systems
  - commodity hardware
  - MapReduce
  - Hadoop
  - Spark
date: 2024-03-26
updated: 2026-07-30
status: evergreen
description: How MapReduce and Spark RDDs process datasets too large for one machine, covering distributed file systems, the word count example, and the tradeoffs between Spark and Hadoop MapReduce.
sources:
  - title: Dean & Ghemawat (2004), MapReduce - Simplified Data Processing on Large Clusters
    url: https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf
    type: paper
  - title: Zaharia et al. (2012), Resilient Distributed Datasets - A Fault-Tolerant Abstraction for In-Memory Cluster Computing
    url: https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia
    type: paper
  - title: HDFS Architecture
    url: https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html
    type: docs
---

## Purpose

Explains the infrastructure for mining very large datasets. Storage comes from a distributed file system, and computation comes from a programming model (MapReduce, then Spark) that moves work to where the data already lives. These primitives are the data-processing foundation under large [[recc-sys/reccomender-systems|recommender systems]].

## The setting

Data mining is the process of extracting actionable information from (usually) very large datasets. Descriptive methods find human-interpretable patterns in data, like clustering. Predictive methods use patterns to predict future data, like recommendation systems.

The data lives on networks of commodity hardware (cheap, off-the-shelf machines) in data centers, and at that scale machine failure is routine. If a server lasts about 1000 days on average, a cluster of 1000 machines loses about one per day, and a fleet of a million machines loses about a thousand per day. The system has to treat failure as normal operation.

Replicating data across machines handles durability, but shipping large datasets over the network is slow and expensive. So the standard move is to run the computation on the machines that already hold the data. Hadoop and Spark are built around this idea, split into two layers:

- **Storage Infrastructure**: a distributed file system, like HDFS (Hadoop Distributed File System)
- **Computation Infrastructure**: a computation engine, like Spark

A distributed file system gives you a global namespace. Typical usage patterns are huge files (100s of GBs to TBs), no updates in place (append-only logs), and large streaming reads, and HDFS is optimized for exactly these patterns ([HDFS Architecture](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)).

- **Chunk Servers**: files are split into large contiguous blocks (HDFS defaults to 128 MB). Each block is replicated across 2-3 servers, ideally in different racks, which gives both parallel reads and fault tolerance. Chunk servers often double as compute nodes, which is what makes "move computation to the data" possible.
- **Master Node**: called the name node in HDFS. Stores metadata about where files are stored, and may itself be replicated.
- **Client Libraries**: talk to the master node to locate data, then read and write it.

## MapReduce

**MapReduce** ([Dean & Ghemawat 2004](https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf)) is a style of programming designed for:

- Easy parallelization
- Invisible management of hardware/software failures
- Easy management of very large datasets
- Very little required memory (since data is read from and written to disk)

Hadoop is the best-known open-source implementation, and Spark supports the same pattern.

- **Map**: apply a user-written function to each element of a list, producing a new list. A **mapper** applies the map function to a single element, and many mappers are grouped into a **Map task**, the main unit of parallelism.
- **Group by key**: sort and shuffle the output of the mappers so that all values for a given key end up together. The output is a list of key to list-of-values pairs.
- **Reduce**: apply a user-written function to each key and its associated list of values, producing a new list.

The keys coming out of the map function should be spread semi-uniformly. Skew in the keys becomes skew in the workload of the reducers that own those keys.

### Example: Word Count

You have a huge text document and want to count the number of times each word appears (say, when analyzing a log file).

**Map**: for each word in the document, output a key-value pair where the key is the word and the value is 1.

```python
def map(doc):
    for word in doc.split():
        yield (word, 1)
```

**Group by key**: sort and shuffle the mapper output so all values for a given key are grouped together.

```python
def group_by_key(pairs):
    pairs.sort()
    for key, group in itertools.groupby(pairs, key=lambda x: x[0]):
        yield (key, [x[1] for x in group])
```

**Reduce**: for each key and its list of values, sum the values.

```python
def reduce(key, values):
    yield (key, sum(values))
```

## Spark

MapReduce has two major limitations. The programming model is rigid, and writing every intermediate result to disk becomes a performance bottleneck.

**Spark** is a general-purpose cluster computing system that addresses both. It is dataflow based. You define a series of transformations on data, and Spark figures out how to execute them in parallel, which makes it more expressive and usually more efficient than MapReduce. Higher-level APIs like dataframes and SQL sit on top.

### Resilient Distributed Datasets (RDDs)

The core data structure in Spark ([Zaharia et al. 2012](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia)). RDDs are immutable, distributed collections of objects, essentially a partitioned collection of records that can be cached in memory across machines. They are fault tolerant because each RDD records how it was computed, so a lost partition can be recomputed from its source.

- **Transformations**: create a new RDD from an existing one. They are lazy, meaning they don't compute the result right away (e.g. `map`, `filter`, `join`, `union`, `intersection`, `distinct`).
- **Actions**: compute a result from an RDD, triggering execution of the DAG (e.g. `collect`, `count`, `reduce`, `saveAsTextFile`).

#### Task Scheduling

Spark supports general DAGs of tasks, where each task is a unit of work sent to a worker. The DAG scheduler breaks the computation into stages, where each stage is a set of tasks that can run in parallel. The task scheduler then schedules tasks within each stage. Functions are pipelined together when possible, and tasks are scheduled in a cache-aware and partition-aware manner.

#### Libraries

- **MLlib**: scalable machine learning
- **GraphX**: graph processing
- **Spark Streaming**: real-time stream processing
- **Spark SQL**: SQL interface for Spark

## Spark vs. Hadoop MapReduce

- **Performance**: Spark is normally faster, with caveats. Spark wants memory, so its benefits shrink on commodity hardware, and MapReduce holds up better when the compute is shared with other processes.
- **Ease of use**: Spark is more expressive and easier to program.
- **Generality**: Spark is more general, with higher-level APIs.

## Sources

- [Dean & Ghemawat (2004), MapReduce: Simplified Data Processing on Large Clusters](https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf)
- [Zaharia et al. (2012), Resilient Distributed Datasets: A Fault-Tolerant Abstraction for In-Memory Cluster Computing](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia)
- [HDFS Architecture](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
