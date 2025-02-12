---
title: Batch Processing Systems and MapReduce Fundamentals
category: Distributed Systems
tags: batch processing, mapreduce, distributed filesystems, data analysis, etl
description: This document explores batch processing systems, focusing on MapReduce and distributed filesystems. It covers Unix tools for log analysis, the MapReduce programming model, and various join techniques in distributed environments. The document also discusses applications of batch processing in search indexing and recommendation systems.
---

# Chapter 10
## Batch Processing

**Services** (*online systems*) are design to handle requests from users or other services. Performance is measured in *requests per second* and *response time*.

**Batch processing** (*offline systems*) run scheduled jobs periodically that process accumulated data. Performance is measured in *throughput*.

**Stream processing** (*near-real-time systems*) are a hybrid of online and offline systems. Performance is measured in *latency*, and they usually take in a stream of *events* and calculate *aggregates* in real time, as opposed to running calculations on accumulated data.


### Batch Processing with Unix Tools

**Log analysis** is a common batch processing task. Applications append log entries to a file, and a batch job periodically processes the log file and generates a report.

```bash
cat /var/log/<application>/<logfile> |  # read the log file
    awk '{print $<url_idx>}' |          # extract the 7th field (URL)
    sort |                              # sort the URLs
    uniq -c |                           # count the number of occurrences of each URL
    sort -r -n |                        # sort numerically in descending order
    head -n 5                           # take the top 5
 ```

 Equivalently, using Python:

 ```python
from collections import Counter

with open('/var/log/<application>/<logfile>') as f:
    urls = [line.split()[<url_idx>] for line in f]
    for url, count in Counter(urls).most_common(5):
        print(url, count)
 ```

However, these two examples differ in that python uses an in-memory hash table, whereas the Unix pipeline uses a disk-based merge sort that can handle data sets larger than memory, and is thus more scalable.

### MapReduce and Distributed Filesystems

**MapReduce** is a programming model for processing large amounts of data in bulk across many machines. It is a batch processing system that runs a user-defined *map* function in parallel over many input *records*, and then runs a user-defined *reduce* function in parallel over the output of the map function.

**Hadoop** is an open source implementation of MapReduce. It is a distributed system that runs on a cluster of machines, and it includes a distributed filesystem called **HDFS** (*Hadoop Distributed Filesystem*).

**HDFS** is designed for storing large files with streaming access patterns, and is optimized for throughput rather than latency. It is based on the *Google File System* (*GFS*), and is similar to *Amazon S3*, although it is not an object store and allows you to run computations on the data stored in it.

Using the Unix pipeline example from above, a (single node) MapReduce job would look like this:

1. Read all input file logs and break into records (lines)
2. Map: extract the URL from each record and output a key-value pair of `(URL, _)`
3. Sort all key-value pairs by key
4. Reduce: count the number of occurrences of each URL

A multi-node MapReduce job would look like this:

1. Read all input file logs and break into records (lines)
2. Map: extract the URL from each record and output a key-value pair of `(URL, _)`
3. Shuffle: group all key-value pairs by hashed key and schedule a reduce task for each group written to disk (sorted by url)
4. Reduce: count the number of occurrences of each URL in the group

This is a single MapReduce job, but often people run a sequence of MapReduce jobs in a pipeline, where the output of one job is the input of the next job. This is called a **workflow**. You can run jobs in sequence using input and output files, or use a scheduler like **Airflow** to manage the workflow.

**Sort-merge joins** Used to combine two sorted lists of records into one sorted list of records. They are used in MapReduce to join the output of the map function before the reduce function.

```python
# psuedocode to join event and user data by user_id
# this is JUST PSEUDOCODE, not actual MapReduce code

# user: { user_id, name, date_of_birth, ... }
map_user_data(user):
    emit_intermediate(user.user_id, user.date_of_birth)

# event: { user_id, event_type, ... }
map_events(event):
    emit_intermediate(event.user_id, event.event_type)

# join: { user_id, date_of_birth, event_type, ... }
reduce_join(user_id, values):
    user = values[0]
    event = values[1]
    payload = { dob: user.date_of_birth, event: event.event_type }
    emit(user_id, payload)
```



**Group-by** Used to group records by a key, and is used in MapReduce to group the output of the map function before the reduce function.

```python
# psuedocode to group events by user_id
# this is JUST PSEUDOCODE, not actual MapReduce code

# event: { user_id, event_type, ... }
map_events(event):
    emit_intermediate(event.user_id, event.event_type)

# group: { user_id, [event_type, ...] }
reduce_group(user_id, values):
    emit(user_id, values)
```

Distributing a join acorss multiple machines is difficult in the the presence of skew. If one user has many events, then the reducer that processes that user's events will be slower than the other reducers. To avoid skew, several algorithms exist and are implemented in tools like Pig and Hive.

Above was an example of a **reduce-side join**, where the join is performed in the reduce function. An alternative is a **map-side join**, where the join is performed in the map function. This is only possible if the join is between two datasets that are partitioned in the same way. For example, if the user data and event data are partitioned by user_id, then the join can be performed in the map function.

Map-side joins are best when joining a large dataset with a small dataset, because the small dataset can be loaded into memory on each machine. This is called a **broadcast join**. Particularly, a **broadcast hash join** is when the small dataset is hashed in the memory of each machine. This is a "replicated join" in Pig, and a "MapJoin" in Hive. You can also use a disk index instead of a hash table for small datasets that woudn't fit in memory.

```python
# psuedocode to join event and user data by user_id
# this is JUST PSEUDOCODE, not actual MapReduce code

# user: { user_id, name, date_of_birth, ... }
users = load_users()

# event: { user_id, event_type, ... }
map_events(event):
    user = users[event.user_id]
    payload = { dob: user.date_of_birth, event: event.event_type }
    emit(user_id, payload)
```


A **partitioned hash join** is when you partition your map-side join in such a way that you only need to read a small portion of either dataset into memory. For example, if you partition both datasets by the first digit of the user_id, then you only need to read ~10% of each dataset into memory on any given partition. This requires that each join input is partitioned in the same way. These are known as "bucketed map joins" in Hive.

```python
# psuedocode to join event and user data by user_id
# this is JUST PSEUDOCODE, not actual MapReduce code

# user: { user_id, name, date_of_birth, ... }
users_partition = load_users_with(ENV.partition_key)

# event: { user_id, event_type, ... }
map_events(event):
    user = users_partition[event.user_id]
    payload = { dob: user.date_of_birth, event: event.event_type }
    emit(user_id, payload)
```


### Output of Batch Workflows

**Search indexes** are used to make data searchable. Often, you can use batch processing to build indexes from a datasource. For example, building search indexes for a massive collection of documents would look something like this:

1. Extract the text from each document
2. Tokenize the text into words
3. Remove common words (stop words)
5. Build an index from words to documents

This can be distributed across multiple machines by partitioning the documents by ID, and then building an in-memory index for each partition. Then, you can merge the in-memory indexes into a single index.

```python
# psuedocode to build a search index
# this is JUST PSEUDOCODE, not actual MapReduce code

# document: { id, text, ... }
map_document(document):
    for word in tokenize(document.text):
        if word not in stop_words:
            emit_intermediate(word, document.id)

# index: { word, [document_id, ...] }
reduce_index(word, values):
    emit(word, values)
```

**Reccomendation systems** are used to reccomend items to users based on their past behavior. For example, you can use batch processing to build a reccomendation system for a feed of posts from other users. To design a system like this, we want reccomendations to be queryable in real time with low latency. Furthermore, the reccomendations should be processed in batches to reduce the load on the database.

Instead of using a database client to process data in our batch job, we create an immutable store of our data in a distributed filesystem. Then, we can run a batch job to process the data and write the results to a database. This is called **extract-transform-load** (*ETL*).

```python
# psuedocode to build a reccomendation index
# Running on a single machine that doesn't handle user requests

# load a partition of the data into memory (without relying on db client)
inmem_store_partition = load_data_from_db(ENV.partition_key)

# process data of this partition
index = build_index_with_map_reduce(inmem_store)

# write the patition's index to the filesystem
write_partition_index_to_fs(ENV.partition_key, index)
```

```python
# psuedocode to query a reccomendation index

def query(user_id):
    result = offload_query_to_partition(user_id)
    return result
```














