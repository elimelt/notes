---
title: Disconnected Operation
category: Distributed Systems
tags:
  - disconnected-operation
  - distributed-systems
  - conflict-resolution
  - eventual-consistency
date: 2024-12-08
updated: 2026-07-30
status: evergreen
description: How systems keep accepting writes while offline, using Coda, Git, and offline-capable web apps as examples, and the conflict resolution strategies that make merging possible.
sources:
  - title: Coda File System project page (CMU)
    url: https://coda.cs.cmu.edu/
    type: docs
---

## Purpose

This note explains how systems support writes while disconnected from the network, and what it costs. The pattern shows up in file syncing, source control, and offline-capable apps, and the hard part is always the same merge and conflict resolution problem.

## Core idea

Always-available writes conflict with keeping a single authoritative copy of the data. To operate while disconnected, a client writes to a local copy and synchronizes with the rest of the system when connectivity returns. Since two clients can modify the same data while apart, writes can conflict, and conflicts get resolved either automatically or by a human.

There are two communication models:

- Clients only talk to a central service (Coda, SVN). Changes are logged locally and applied on reconnection.
- Clients talk to the service and to each other (Git). Changes are logged and exchanged with whatever peer you connect to, and merges happen again on each new connection.

## Coda

[Coda](https://coda.cs.cmu.edu/) mounts a remote file system as a local directory, keeping a partial replica of the global version and caching aggressively to reduce latency. While disconnected it records changes in a write-ahead log. On reconnection it replays the log to the server and merges the changes atomically.

Coda merges automatically when it can. When two users edit the same file, it creates a conflict file and leaves resolution to the user.

## Offline-capable web apps

Apps like Gmail and Google Docs support offline editing with a local cache plus a log of changes. On reconnection the log is sent to the server and merged, with conflicts resolved by application-level rules.

A common building block is the **version vector**: each client has a unique ID, each change is tagged with it, and comparing vectors during a merge tells you which changes are newer and which are concurrent. This is the same mechanism as [[distributed-systems/clocks|vector clocks]].

## Source code control

Source control is disconnected operation as the normal mode, permanently. Each client reads and writes its own local copy, and syncs are occasional and manual. The system tracks the full history of changes plus metadata, which is what makes late merging tractable.

## Building apps around local storage

A useful application model: write to a local storage engine (SQLite, LevelDB) and sync with the server when online. The synchronization mechanism carries all the difficulty, specifically how it resolves conflicts.

### Conflict resolution

- **Client wins**: the client's changes are always accepted
- **Server wins**: the server's changes are always accepted
- **Merge**: changes are combined, and remaining conflicts are resolved manually or automatically

### Merge strategies

- **Last write wins**: the most recent write is accepted, which requires some form of timestamp or versioning
- **Operation based**: changes are represented as operations (add, delete, and so on) and applied in order. CRDTs work this way.

## Related notes

- [[distributed-systems/consistency|consistency]]
- [[distributed-systems/dynamo-db|Dynamo]]
