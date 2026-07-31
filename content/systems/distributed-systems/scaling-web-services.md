---
title: Scaling Web Services with Distributed Architectures
aliases:
  - distributed-systems/scaling-web-services
category: Distributed Systems
tags:
  - distributed-systems
  - two-tier-architecture
  - load-balancing
  - caching
  - edge-computing
  - microservices
date: 2024-04-26
updated: 2026-07-30
status: evergreen
description: The standard progression for scaling a web service, from stateless two-tier designs through look-aside caching to edge data centers and service oriented architectures.
---

## Purpose

This note walks the standard progression for scaling a web service: split stateless frontends from stateful storage, put load balancers between the tiers, add a caching layer, and then push work toward the edge or split the application into services.

## Two tier architecture

The two tier design separates a scalable pool of frontend servers from a scaled-out storage backend. Clients map to frontend servers, and frontend servers map to the storage servers holding their data.

### Two-tier RESTful web architecture

Keep a scalable number of stateless servers hosting the client-facing application code. A crashed frontend costs nothing, since the user can connect to any other one. Behind them, run a scalable number of backend storage servers in a carefully designed distributed system, often using [[systems/distributed-systems/primary-backup|primary/backup]] or Paxos for availability and fault tolerance. Anything that must survive crashes belongs in the backend.

### Load balancing

Load balancers sit between the tiers. They need to map any given client to a frontend server, consistently per connection, which `hash(clientIP, port) -> frontendServerIP` handles. They also map each frontend server to a storage server via `hash(key) -> storageServerIP`, where the key identifies the data a query touches. The system should adapt automatically when servers of any type are added.

### Three-tier web architecture: look-aside caching

Add a set of cache servers to absorb queries before they reach storage. Frontend servers send each query to the cache first, fall back to the storage servers on a miss, and then write the retrieved data into the cache. This pattern is look-aside caching.

Caching can be arranged other ways. The cache could fetch values from storage itself, transparently to the frontend, so misses never need handling in application code. That tightly couples the cache and the storage server, usually forcing all queries through the caching layer and making the two services harder to design independently.

The cache tier has to scale too. Cache servers need not be 1:1 with frontend or storage servers, but they should handle the load of the frontends they serve, and they should answer with lower latency than the storage layer they shield.

## Newer architectures

### Edge computing

Move data processing closer to the client. Users are globally distributed, and distance shows up as latency.

Large applications place **edge data centers** near users, often hosting only the web and cache (RESTful) layers. Content can be pushed to the edge before anyone requests it. **Core data centers** host web, cache, and storage layers, replicated across sites for disaster tolerance.

### Service oriented architecture

Each team exposes its data and functionality through an external interface, and all communication happens through network calls. Each service runs as a standalone product with its own service level agreement to its clients. Designing for this means assuming the callers and the network are hostile.

### Microservices

Organize a complex application as a large number of independent services communicating through [[systems/distributed-systems/RPC|RPC]], each using primary/backup or Paxos for availability and fault tolerance. Components can then be developed and scaled independently.

## Related notes

- [[systems/distributed-systems/load-balancing|load balancing]]
- [[systems/distributed-systems/sharding|sharding]]
- [[systems/distributed-systems/distributed-cache-coherence|distributed caching]]
