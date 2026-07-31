---
title: Distributed Systems
category: Distributed Systems
tags:
  - distributed systems
  - replication
  - consensus
  - sharding
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Overview of the distributed systems notes, from ordering and consistency to replication, consensus, and scalable services.
---

## Purpose

The notes here revolve around one question: how do you keep useful global behavior when no machine can see the whole system at once? The cleanest starting path is [[systems/distributed-systems/clocks|clocks]], then [[systems/distributed-systems/ordering-events-in-distributed-systems|event ordering]], then [[systems/distributed-systems/consistency|consistency]]. That gives the vocabulary the replication and consensus notes use later.

From there, the section branches into system-building patterns such as [[systems/distributed-systems/primary-backup|primary backup]], [[systems/distributed-systems/sharding|sharding]], and [[systems/distributed-systems/load-balancing|load balancing]], plus consensus notes such as [[systems/distributed-systems/paxos-intro|Paxos introduction]] and [[systems/distributed-systems/paxos-made-simple|Paxos Made Simple]].

## Entry points

- Time and ordering: [[systems/distributed-systems/clocks|clocks]], [[systems/distributed-systems/ordering-events-in-distributed-systems|ordering events]], [[systems/distributed-systems/consistent-global-state|consistent global state]]
- Replication and consistency: [[systems/distributed-systems/consistency|consistency]], [[systems/distributed-systems/primary-backup|primary backup]], [[systems/distributed-systems/non-blocking-two-phase-commit|non-blocking two-phase commit]]
- Scalable services: [[systems/distributed-systems/load-balancing|load balancing]], [[systems/distributed-systems/sharding|sharding]], [[systems/distributed-systems/scaling-web-services|scaling web services]]
- Case studies: [[systems/distributed-systems/google-file-system|Google File System]], [[systems/distributed-systems/bigtable|Bigtable]], [[systems/distributed-systems/dynamo-db|Dynamo]]
