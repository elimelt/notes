---
title: Data Models and Relationships in Database Systems
aliases:
  - designing-data-intensive-applications/part-1-foundations-of-data-systems/ch2-data-models-and-query-languages
category: Database Systems
tags:
  - relational-databases
  - document-databases
  - graph-databases
  - data-modeling
  - query-languages
date: 2023-12-19
updated: 2026-07-30
status: evergreen
description: Reading notes on chapter 2 of Designing Data-Intensive Applications. Covers relational, document, and graph data models, how each handles relationships, data locality, and MapReduce-style querying.
sources:
  - title: Designing Data-Intensive Applications, Martin Kleppmann
    url: https://dataintensive.net/
    type: book
---

## Purpose

Reading notes on chapter 2 of [Designing Data-Intensive Applications](https://dataintensive.net/) by Martin Kleppmann. The chapter compares the relational, document, and graph data models, with relationships between records as the axis that separates them.

## The relational and document models

The relational model organizes data into tables of rows queried with SQL. The document model, common in NoSQL databases, stores self-contained documents, usually as JSON.

The awkward translation between in-memory objects and relational tables is often called an impedance mismatch, and it is why so much middleware exists, most commonly an object-relational mapping (ORM) layer.

## Relationships

Use ids to refer to related data instead of embedding it. An id never changes and is often much smaller than the data it points to.

One-to-many relationships are by far the most common type of relationship in databases. In SQL they are a foreign key; in a document they are an embedded array of ids.

```sql
CREATE TABLE users (
    user_id INT PRIMARY KEY,
    username VARCHAR(200) UNIQUE
);

CREATE TABLE orders (
    order_id VARCHAR(255) PRIMARY KEY,
    user_id INT REFERENCES users (user_id)
);
```

```json
{
  "user_id": 1,
  "username": "martin",
  "order_ids": [1, 2]
}
```

Many-to-many relationships are less common. In SQL they get a join table:

```sql
CREATE TABLE users (
    user_id INT PRIMARY KEY,
    username VARCHAR(200) UNIQUE
);

CREATE TABLE groups (
    group_id INT PRIMARY KEY,
    group_name VARCHAR(200) UNIQUE
);

CREATE TABLE user_groups (
    user_id INT REFERENCES users (user_id),
    group_id INT REFERENCES groups (group_id),
    PRIMARY KEY (user_id, group_id)
);
```

```json
{
  "user_id": 1,
  "username": "martin",
  "group_ids": [1, 2]
}
```

Many-to-many relationships are natural in SQL but awkward in document databases, since joins in document databases are weak or missing. Often the practical answer is to denormalize some of the data into the document:

```sql
SELECT * FROM users
JOIN user_groups USING (user_id)
JOIN groups USING (group_id)
WHERE group_name = 'devops';
```

```json
{
  "user_id": 1,
  "username": "martin",
  "groups": [
    { "group_id": 1, "group_name": "devops" },
    { "group_id": 2, "group_name": "dba" }
  ]
}
```

Two older and more general models come up when relationships dominate. The network model generalizes the hierarchical model by letting a child record have several parents, forming a graph of records connected by links. The graph model generalizes further, letting edges carry properties as well as vertices.

## Choosing a data model

Schema-on-write is the traditional approach: define a relational schema, then only write data that conforms to it. It enforces data quality and helps performance, at the cost of flexibility. Schema-on-read skips upfront enforcement and interprets structure when data is read. It handles rapidly changing requirements well, and it copes with data written by many different applications.

Choose whichever model simplifies your application code the most and matches your access patterns.

## Data locality

Data locality means related data items sit together on the same storage device, for example the same disk block or the same server node. Queries that touch collocated data avoid extra seeks and network hops.

A document database has to load an entire document even when the query needs a small part of it, so keep documents small. Google Spanner gets locality in a relational model by letting rows be interleaved (nested) within a parent table. Column-family databases such as Bigtable, HBase, and Cassandra manage locality with a similar idea. Many relational databases also have XML and JSON column types, which store documents inside a row of a table.

## MapReduce querying

MapReduce is a programming model for processing large amounts of data in bulk across many machines, popularized by Google. It has two steps. The map step takes a document as input and produces intermediate key-value pairs. The reduce step takes all values emitted for a key and collapses them into a result, which can be a single value or a more complex structure.

MapReduce fits batch processing. It does not fit interactive queries that need low latency. Some NoSQL databases, for example MongoDB and CouchDB, expose a limited form of MapReduce for reading batches of documents. The same aggregation looks like this in SQL, MongoDB's mapReduce API, and MongoDB's aggregation pipeline:

```sql
-- traditional SQL
SELECT date_trunc('month', observation_timestamp) AS observation_month,
 sum(num_animals) AS total_animals
FROM observations
WHERE family = 'Sharks'
GROUP BY observation_month;
```

```js
// MapReduce in MongoDB
db.observations.mapReduce(
    // collect data
  function map() {
    var year = this.observationTimestamp.getFullYear()
    var month = this.observationTimestamp.getMonth() + 1
    emit(year + '-' + month, this.numAnimals)
  }, // aggregate the data
  function reduce(key, values) {
    return Array.sum(values)
  },
  { // query to select the documents
    query: { family: 'Sharks' },
    out: 'monthlySharkReport'
  }
)
```

```js
// Aggregation pipeline in MongoDB
db.observations.aggregate([
 { $match: { family: "Sharks" } },
 { $group: {
 _id: {
 year: { $year: "$observationTimestamp" },
 month: { $month: "$observationTimestamp" }
 },
 totalAnimals: { $sum: "$numAnimals" }
 } }
]);
```

## Property graphs

Each vertex consists of:

- A unique identifier
- A set of outgoing edges
- A set of incoming edges
- A collection of properties (key-value pairs)

Each edge consists of:

- A unique identifier
- The vertex at which the edge starts (the tail vertex)
- The vertex at which the edge ends (the head vertex)
- A label describing the kind of relationship between the two vertices
- A collection of properties (key-value pairs)

Conceptually the model fits in two relational tables:

```sql
-- Conceptual graph model in SQL
CREATE TABLE vertices (
 vertex_id integer PRIMARY KEY,
 properties json
);

CREATE TABLE edges (
 edge_id integer PRIMARY KEY,
 tail_vertex integer REFERENCES vertices (vertex_id),
 head_vertex integer REFERENCES vertices (vertex_id),
 label text,
 properties json
);

CREATE INDEX edges_tails ON edges (tail_vertex);

CREATE INDEX edges_heads ON edges (head_vertex);
```

In practice, graph databases are implemented differently because traversals over this relational encoding are slow. Dedicated query languages such as Cypher express multi-hop traversals directly, which is painful to write as recursive SQL joins.

## Triple-stores and SPARQL

A triple-store holds three-part statements of the form `(subject, predicate, object)`. The subject and object are vertices, and the predicate acts as the edge label, so the model is equivalent in power to a property graph. SPARQL is the query language for triple-stores that hold RDF data, and its pattern-matching syntax resembles Cypher's.

## Sources

- [Designing Data-Intensive Applications](https://dataintensive.net/), Martin Kleppmann, chapter 2

## Related notes

- [[systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications|reliable, scalable systems]]
- [[systems/databases/foundations/ch3-storage-and-retrieval|storage and retrieval]]
