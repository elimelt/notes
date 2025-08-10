---
title: Distributed Computing for Data Mining
category: Distributed Systems
tags: data mining, distributed file systems, commodity hardware, MapReduce, Hadoop, Storage Infrastructure, Computation Infrastructure
description: Focuses on distributed computing approaches for data mining, specifically exploring how MapReduce and Resilient Distributed Datasets (RDDs) in Spark can be used to process large datasets. It compares the performance of these technologies using a word count example, providing insight into their strengths and weaknesses. The document also discusses the differences between Spark and Hadoop + MapReduce for data mining applications.
---

# Distributed Computing for Data Mining

How can we extract knowledge from large data sets?

- **Data mining**: the process of extracting actionable information from (usually) very large datasets.
- **Descriptive methods**: Find human-interpretable patterns in data. (e.g. clustering)
- **Predictive methods**: Use patterns to predict future data. (e.g. recommendation systems)

Typically, data is stored on networks of *commodity hardware* (cheap, off-the-shelf hardware) within data centers. A major challenge with this computing model is the failure of individual machines. One server may survive for ~3 years, but with 10,000 servers, you can expect one to fail every day. With 1M servers, you can expect 1000 failures per day.

One approach is to replicate data across multiple machines. However, transferring data is expensive and time intensive. A core idea of distributed computing is to move computation to the data, rather than moving data to the computation. Spark/Hadoop address these problems.

- **Storage Infrastructure**: A file system, like HDFS (Hadoop Distributed File System)
- **Computation Infrastructure**: A computation engine, like Spark

Distributed file system give you a global namespace. Typical usage patterns include huge files (100s of GBs to TBs), no updates in place (append only logs), and large streaming reads. HDFS is optimized for these patterns.

- **Chunk Servers**: Files are split into contiguous blocks, typically 16-64MB. Eacg block is replicated across multiple servers (x2-3), ideally in different racks. This allows for parallel reads and fault tolerance. Chunk servers are also oftentimes compute nodes as well.
- **Master Node**: AKA name node in Hadoop HDFS. Stores metadata about where files are stored, might be replicated.
- **Client Libraries**: A library that communicates with the master node to read/write data.

## MapReduce

**MapReduce** is a style of programming that is designed for
- Easy parallelization
- Invisible management of hardware/software failures
- Easy management of very large datasets
- Very little required memory (since data is read and written to disk)

There are several implementations of MapReduce, including **Hadoop** and **Spark**.

- **Map**: Apply a user-written function to each element of a list, producing a new list.
  - **Mapper** applies the map function to a single element. Mapny mappers grouped in a **Map task** (the main unit of parallelism).
- **Group by key**: Sorts and shuffles the output of the mappers so that all values for a given key are grouped together.
  - Output is a list of key to list of value pairs
- **Reduce**: Apply a user-written function to each key and its associated list of values, producing a new list.

It is important that your distribution of keys outputted by the map function is semi-uniform. Skew in keys leads to skew in the workload of reducers associated with those keys.

### Example: Word Count

You have a huge text document and you want to count the number of times each word appears (ie analyzing a log file).

**Map**: For each word in the document, output a key-value pair where the key is the word and the value is 1.

```python
def map(doc):
    for word in doc.split():
        yield (word, 1)
```

**Group by key**: Sort and shuffle the output of the mappers so that all values for a given key are grouped together.

```python
def group_by_key(pairs):
    pairs.sort()
    for key, group in itertools.groupby(pairs, key=lambda x: x[0]):
        yield (key, [x[1] for x in group])
```

**Reduce**: For each key and its associated list of values, sum the values.

```python
def reduce(key, values):
    yield (key, sum(values))
```

## Spark

The two major limitations of MapReduce are
- Rigid programming model
- Performance bottleneck due to disk I/O

**Spark** is a general-purpose cluster computing system that addresses these limitations. It is instead *dataflow* based, where you define a series of transformations on data, and Spark figures out how to execute them in parallel. It is meant to be a more expressive and efficient than MapReduce. There are higher-level APIs like dataframes and SQL that make it easier to work with data.

### Resilient Distributed Datasets (RDDs)
The core data structure in Spark. They are immutable, distributed collections of objects. You can perform transformations on RDDs to create new RDDs, and Spark will optimize the execution of these transformations.

They are essentially a partitioned collection of records that can be cached in memory across machines. They are fault-tolerant, meaning if a partition is lost, it can be recomputed from the original source.

- **Transformations**: Create a new RDD from an existing one. They are lazy, meaning they don't compute the result right away (eg `map`, `filter`, `reduce`, `join`, `union`, `intersection`, `distinct`).
- **Actions**: Compute a result from an RDD. They trigger the computation of the DAG (eg `collect`, `count`, `reduce`, `saveAsTextFile`).

#### Task Scheduling

Spark supports general DAGs of tasks, where each task is a unit of work that is sent to a worker. The DAG scheduler breaks the computation into stages, where each stage is a set of tasks that can be executed in parallel. The task scheduler then schedules tasks within each stage. Functions are pipelined together when possible, and tasks are scheduled in both a cache aware and partition aware manner.

#### Libraries

- **MLlib**: Scalable machine learning lib
- **GraphX**: Graph processing lib
- **Spark Streaming**: Real-time stream processing
- **Spark SQL**: SQL interface for Spark

## Spark vs. Hadoop + MapReduce

- **Performance**: Spark is normally faster, with caveats. Spark requires memory, so the benefits are less pronounced on commodity hardware. MR is better when you are running on compute that is shared with other processes.
- **Ease of Use**: Spark is more expressive and easier to use.
- **Generality**: Spark is more general, with higher-level APIs.