---
title: Dynamo: Amazon's Highly Available Key-value Store
category: Distributed Systems
tags: key-value store, database design, high availability, consistency, object versioning, conflict resolution
date: 2024-08-04
description: A highly available key-value storage system sacrificing consistency under failure conditions, using object versioning and application assisted conflict resolution.
---
# Dynamo: Amazon's Highly Available Key-value Store

[reading](https://dl-acm-org.offcampus.lib.washington.edu/doi/pdf/10.1145/1323293.1294281)


Dynamo is a highly available key-value storage system that sacrifices consistency under certain failure conditions, making extensive use of object versioning and application assisted conflict resolution.

## Related notes

- [[distributed-systems/consistency|consistency]]
- [[distributed-systems/sharding|sharding]]
- [[distributed-systems/disconnected-operation|disconnected operation]]
