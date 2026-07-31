---
title: "Dynamo: Amazon's Highly Available Key-value Store"
aliases:
  - distributed-systems/dynamo-db
category: Distributed Systems
tags:
  - key-value-store
  - high-availability
  - object-versioning
  - conflict-resolution
  - paper-notes
date: 2024-08-04
updated: 2026-07-30
status: incomplete
description: Stub notes on the Dynamo paper (SOSP 2007). Records the paper's main move and its core techniques; the mechanism details are not written up yet.
sources:
  - title: "Dynamo: Amazon's Highly Available Key-value Store (SOSP 2007)"
    url: https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf
    type: paper
---

## Purpose

Notes on the [Dynamo paper](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf). This is a stub. Only the main idea is recorded so far.

## Main idea

Dynamo is a highly available key-value store that sacrifices consistency under certain failure conditions. Writes are always accepted, so the system can produce divergent versions of an object, and it makes extensive use of object versioning with vector clocks plus application-assisted conflict resolution to reconcile them. Reconciliation happens at read time, and when the version history alone cannot decide, the application merges the divergent versions itself, the shopping cart being the paper's running example.

The paper's techniques worth writing up properly: consistent hashing for partitioning and replication, vector clocks for versioning, sloppy quorums with hinted handoff for availability during failures, and gossip-based membership.

## Related notes

- [[systems/distributed-systems/consistency|consistency]]
- [[systems/distributed-systems/sharding|sharding]]
- [[systems/distributed-systems/disconnected-operation|disconnected operation]]
- [[systems/distributed-systems/clocks|clocks]]
