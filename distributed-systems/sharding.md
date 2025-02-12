---
title: Sharding
category: distributed-systems
tags: sharding, consistent hashing, indirection tables, load balancing, data distribution
description: Explains the concept of sharding in distributed systems, its approaches and implications.
---

# Sharding

## Consistent Hashing

A classic approach is to maintain a modular space of hashed keys, and use the regions between shards to assign keys. This is known as **consistent hashing**. It works, but has some drawbacks:

- **Load Imbalance**: If the keys are not evenly distributed, some shards will be more heavily loaded than others.
- **Hotspots**: If the keys are not evenly distributed, some shards will be more heavily loaded than others.
- **Data Migration**: When adding a new shard, keys need to be moved around, which can be expensive.

## Indirection Tables

A cooler approach in my opinion. Just put a table of `hash(key) -> server address` on every client, and assign fewer table entries to buckets with more keys. This way, the load is more evenly distributed. You can then broadcast any changes to the table to every client server.