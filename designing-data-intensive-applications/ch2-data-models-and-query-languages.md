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
        {"group_id": 1, "group_name": "devops"},
        {"group_id": 2, "group_name": "dba"}
    ]
}
```

**Network model** is a generalization of the hierarchical model, in which a child record may have several parents. It is a graph of records, connected by links.
