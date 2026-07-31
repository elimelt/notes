---
title: Sharding
aliases:
  - distributed-systems/sharding
category: Distributed Systems
tags:
  - sharding
  - consistent-hashing
  - indirection-tables
  - load-balancing
  - data-distribution
date: 2024-05-06
updated: 2026-07-30
status: incomplete
description: Two approaches to assigning keys to shards, consistent hashing and indirection tables, and the load problems each one has. Does not yet cover resharding or replication placement.
sources:
  - title: "Dynamo: Amazon's Highly Available Key-value Store (SOSP 2007)"
    url: https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf
    type: paper
---

## Purpose

Sharding is deciding which server owns which keys. This note covers the two assignment schemes I've seen most, consistent hashing and indirection tables, and the load problems each one runs into.

## Consistent hashing

The classic approach hashes keys and servers into the same modular space, and each shard owns the region between itself and its neighbor. This is consistent hashing, and [Dynamo](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) is the well-known production example. It works, but it has drawbacks:

- **Load imbalance**: random placement of servers on the ring gives some shards much larger regions than others, so load skews even when keys are uniform. Dynamo counters this with virtual nodes, placing each server at many points on the ring.
- **Hotspots**: a few very popular keys can overload whichever shard owns them, and the hash placement gives you no way to split just those keys off.
- **Data migration**: adding a shard means moving the keys in the region it takes over, which is expensive.

## Indirection tables

A cooler approach in my opinion. Put a table of `hash(key) -> server address` on every client, with many more table entries than servers. Load balancing then becomes table assignment: give fewer entries to servers whose entries hold more or hotter keys. Broadcast table changes to every client server. Moving one table entry migrates a small slice of keys, so rebalancing is cheap and targeted.

## Related notes

- [[systems/distributed-systems/scaling-web-services|scaling web services]]
- [[systems/distributed-systems/load-balancing|load balancing]]
- [[systems/distributed-systems/dynamo-db|Dynamo]]
