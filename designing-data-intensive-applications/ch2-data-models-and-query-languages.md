# Chapter 2

## Data Models and Query Languages

**Relational Model** We all know SQL

**Document Model** As well as NoSQL

### Mismatch between Relational Model and OOP

Awkward translation between objects and relations leads to middleware, oftentimes a **object-relational mapping (ORM)**

### Relationships

It is useful to use ids to refer to related data, rather than embedding it. It never changes, and it is often much smaller.

**One-to-many** relationships are by far the most common type of relationship in databases.

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

**Many-to-many** relationships are less common, but they do exist.

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

**Many-to-many relationships** are natural in SQL, but awkward in document databases. Often, the best way to deal with many-to-many relationships in a document database is to denormalize some of the data, since joins are limited.

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

**Network model** is a generalization of the hierarchical model, in which a child record may have several parents. It is a graph of records, connected by links.

**Graph model** is a further generalization, in which edges can have properties as well as vertices.

### Choosing a data model

**Schema-on-write** is the traditional approach of defining a relational schema for your data, and then writing data that conforms to the schema. It is good for ensuring data quality, and it is also good for performance. However, it is inflexible.

**Schema-on-read** is the approach of not enforcing a schema ahead of time, but only reading it when you read from the database. It is good for handling data with rapidly changing requirements, and for cases where you need to load data from many different applications.

Choose whichever model simplifies your application code the most, and matches your access patterns.

### Data locality

is the collocation of related data items on the same storage device (e.g. disk block, server node, etc.). It is important for performance.

**Locality in query execution** is the collocation of data items that are accessed together in the same query. It is important for performance.

For document databases, you need to load the entire document, even if you only need a small portion of it. Keep documents small.

**Examples**: Google Spanner uses nested data structures, and it allows secondary indexes on nested fields. MongoDB and Elasticsearch allow you to index nested fields, but they don’t allow secondary indexes on nested fields. Column family databases such as BigTable, HBase, and Cassandra.

Many relational databases also have XML and JSON data types, which allow you to store documents within a row of a table.

### MapReduce Querying

**MapReduce** is a programming model for processing large amounts of data in bulk across many machines, popularized by Google. It is a two-step process:

1. The **map** step takes a document as input and produces an intermediate representation of key-value pairs.

2. The **reduce** step takes the output of the map step, with the same key appearing once for each value, and produces a result. The result can be a single value per key, or an arbitrarily complex data structure.

**MapReduce** is a good model for batch processing of data, but it is not suitable for interactive queries or applications that require low latency. Some NoSQL databases have a limited form of MapReduce for reading batches of documents (e.g. MongoDB, CouchDB).

```sql
-- traditional SQL
SELECT date_trunc('month', observation_timestamp) AS observation_month,
 sum(num_animals) AS total_animals
FROM observations
WHERE family = 'Sharks'
GROUP BY observation_month;
```

```js
// Map Reduce MongoDB
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
// Aggregation pipeline with MongoDB
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

#### Property Graphs

Each **vertex/node** consists of:

- A unique identifier
- A set of outgoing edges
- A set of incoming edges
- A collection of properties (key-value pairs)

Each **edge** consists of:

- A unique identifier
- The vertex at which the edge starts (the tail vertex)
- The vertex at which the edge ends (the head vertex)
- A label to describe the kind of relationship between the two vertices
- A collection of properties (key-value pairs)

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

In practice, graph databases are usually implemented differently, because the above model is not very efficient. Specialized query languages are used to traverse the graph in an imperative style.

