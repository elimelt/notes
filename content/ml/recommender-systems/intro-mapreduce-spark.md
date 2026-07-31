---
title: Distributed Computing for Data Mining
aliases:
  - recc-sys/intro-mapreduce-spark
category: Recommender Systems
tags:
  - data mining
  - distributed file systems
  - commodity hardware
  - MapReduce
  - Hadoop
  - Spark
date: 2024-03-26
updated: 2026-07-31
status: evergreen
description: How MapReduce and Spark process datasets too large for one machine, and why recommender teams still lean on these patterns for feature generation, joins, and large-scale training data preparation.
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

Recommender papers often jump straight to the model and skip the machinery that made the training table exist in the first place. This note is about that machinery. Large recommenders depend on batch systems for log joins, feature aggregation, negative sampling, embedding preparation, and retraining at a scale that does not fit on one machine.

## The Setting

Data mining is the process of extracting useful structure from large datasets. In recommender work that usually means:

- aggregating user histories
- computing co-occurrence tables
- building candidate pools
- generating supervised training examples
- joining delayed labels back to impressions

The data lives on fleets of commodity machines. At that scale failures are routine, so the system has to expect them.

Replicating data across machines handles durability. The other problem is bandwidth. Moving terabytes over the network is expensive, so the standard move is to place the computation near the data.

That gives two layers:

- **Storage**: a distributed file system such as HDFS
- **Computation**: an execution model such as MapReduce or Spark

## Distributed File Systems

HDFS is designed for:

- very large files
- append-heavy workloads
- large streaming reads

Files are split into large blocks, typically replicated across machines and racks. A master node tracks metadata. Clients ask the master where blocks live, then talk directly to the data nodes.

This design matters for recommenders because offline jobs are full of giant scans over logs and fact tables. It is a bad fit for tiny random reads and a good fit for "read everything, aggregate, write a new table."

## MapReduce

MapReduce is a programming pattern built around three logical steps:

1. map records into key-value pairs
2. group values by key
3. reduce each key's values into an output

That sounds rigid because it is rigid. The benefit is that the runtime hides a lot of ugly distributed-systems detail:

- scheduling
- retries
- locality
- fault recovery

### Example: Co-Occurrence Counts

A recommender job might want item-item co-watch counts. For each user session, emit all co-occurring item pairs in the map step, shuffle by pair, then reduce by summing counts.

That is the same shape as word count, only with more painful skew.

## Spark

Spark relaxes the MapReduce straitjacket. Instead of one fixed map-shuffle-reduce pipeline, it supports a DAG of transformations over distributed datasets.

The core abstraction is the RDD, an immutable distributed collection whose lineage records how it was built. If a partition is lost, Spark can recompute it.

Useful properties for recommender workloads:

- in-memory caching for iterative jobs
- richer joins and filters
- easier expression of multi-stage pipelines
- built-in libraries for SQL, graph, and ML work

That matters because recommender preprocessing is often iterative. You build one table, join it to another, filter, bucketize, resample, then repeat. Spark fits that shape better than classic MapReduce.

## Where Recommender Teams Use This

Typical batch jobs in recommendation look like:

- aggregate rolling user features
- build item popularity and freshness tables
- compute training examples for retrieval and ranking
- sample negatives
- backfill delayed conversions or watch time
- export item embeddings into an ANN index

None of that is glamorous, though most production failures come from this layer sooner than from the model definition.

## Spark Versus Hadoop MapReduce

- **MapReduce** is simpler and robust for pure one-pass batch aggregation.
- **Spark** is more expressive and usually faster for iterative pipelines and repeated reuse of intermediate state.

For recommender teams, Spark usually wins because feature pipelines, joins, and sampling logic are rarely single-pass jobs.

## The Real Lesson

When a paper says "we trained on billions of examples," there is always a data system underneath it. In recommenders, the model is often only the last few percent of the engineering problem.

## Sources

- [Dean & Ghemawat (2004), MapReduce: Simplified Data Processing on Large Clusters](https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf)
- [Zaharia et al. (2012), Resilient Distributed Datasets: A Fault-Tolerant Abstraction for In-Memory Cluster Computing](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia)
- [HDFS Architecture](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
