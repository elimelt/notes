---
title: Disconnected Operation
category: distributed-systems
tags: disconnected operation, distributed systems, conflict resolution, eventual consistency
description: Explains the concept of disconnected operation in distributed systems and its implications.
---

# Disconnected Operation

Always available writes inherently pose a problem in distributed systems. To allow for disconnected operation, we need to be able to write to a local copy of the data, and then synchronize it with the rest of the system when we're back online. Many apps today are built to work with intermittent lack of connectivity, for example, file syncing apps/sourcing control systems. In many of these systems, writes can conflict, and need to be resolved either manually or automatically.

## Two Models

- Applications only communicate with the cloud (Coda, SVN)
  - Log changes, apply on reconnection
- Applications communicate with cloud and other clients (Git)
  - Log changes and exchange with other clients
  - Remerge changes when connected to a new client

## Coda

Coda lets you mount a remote file system as a local directory. The local file system is a partial replica of the global version. It makes extensive use of local caching to reduce latency. While disconnected, it uses a write ahead log to record changes. When reconnected, it replays the log to the server and merges changes atomically.

When possible, Coda will merge changes automatically. If there are conflicts, i.e. two users edit the same file, Coda will create a conflict file and let the user resolve it.

## Gmail/Google Docs

Apps like Gmail and Google Docs allow for offline editing by using a local cache and log of changes. When reconnected, the changes are sent to the server and merged. In the case of conflicts, the application specifies a set of rules to resolve them automatically.

One common general approach is to use a **version vector** to track changes. Each client has a unique ID, and each change is tagged with the client's ID. When changes are merged, the version vector is used to determine which changes are newer.

## Source Code Control

- Eventual Consistency with read/write on a local copy, and occasional sync manually
- Track history of changes and metadata
- Multiple clients can edit their own copy of the code and merge changes later

## Interesting Application Model

Use local storage engines (like SQLite, LevelDB, etc.) for local writes and sync with the server when online. The key to making this strategy work is the synchronization mechanism, and how conflicts are resolved.

### Conflict Resolution

- **Client wins**: The client's changes are always accepted
- **Server wins**: The server's changes are always accepted
- **Merge**: Changes are combined, and conflicts are resolved manually or automatically

### Merge Strategies

- **Last write wins**: The last write is always accepted. This requires some form of timestamp or versioning.
- **Operation based**: Changes are represented as operations (add, delete, etc.) and are applied in order. This is how CRDTs work.
