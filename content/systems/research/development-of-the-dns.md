---
title: Development of the Domain Name System
aliases:
  - systems-research/development-of-the-dns
category: Systems Research
tags:
  - dns
  - domain-name-system
  - networking
  - systems
  - paper-notes
date: 2025-01-19
updated: 2026-07-30
status: evergreen
description: Review notes on the DNS retrospective paper, covering the design requirements that replaced HOSTS.TXT, the name server and resolver split, zones, caching, and what held up.
sources:
  - title: Development of the Domain Name System (SIGCOMM 1988)
    url: https://courses.cs.washington.edu/courses/cse551/09sp/papers/dns.pdf
    type: paper
---

## Purpose

Reading notes on Mockapetris and Dunlap's retrospective on DNS. The note walks through the design requirements, the architecture, and the distribution and caching machinery, then records what I think the design got right and where it is weak.

## Citation

- [Development of the Domain Name System](https://courses.cs.washington.edu/courses/cse551/09sp/papers/dns.pdf), Mockapetris and Dunlap, SIGCOMM 1988.

## Problem

The original solution for naming was a single shared file, `HOSTS.TXT`, containing every hostname and its IP address. That worked while the number of hosts was proportional to the number of timesharing systems. Once the internet became many networks, each with many hosts, a centrally maintained file could not keep up in size or in rate of change. Naming needed a distributed database, and this paper describes the system built to provide one.

## Design requirements

- Provide all the functionality of `HOSTS.TXT`
- Allow distributed maintenance
- No obvious size limits on names, name components, or data associated with names
- Interoperate with the existing DARPA Internet
- Tolerable performance
- Independence from network topology, with the ability to encapsulate other name spaces
- Avoid forcing a single OS, architecture, or organizational structure; support both large timesharing systems and individual PCs

## Mechanism

### Architecture

Two main components. The name server is the repository of name-to-data mappings and answers queries. The resolver is the interface client programs use to query name servers. The line between them is deliberately blurry. An organization can run a centralized name server plus resolver shared by all its hosts, so individual PCs never need to run their own resolver.

### Name space

Domains are organized hierarchically, with all names sharing a common null root. DNS makes no assumptions about the structure or presentation of names, but suggests domains model the organization they represent.

### Data attached to names

DNS attaches arbitrary data to names, organized into typed resource records (RRs). Each RR carries a type, a class, and unstructured application data. Type represents the abstract resource and class represents the protocol family or instance. The designers expected types and classes to be extended often; in practice extension is rare, and more bits than necessary were allocated to those fields.

A name server answering a query is free to return extra data beyond what was asked for, anticipating future queries to cut down round trips. Root servers use this, returning both the name and the address of a host when a query only forced one of them.

### Zones

A zone is a complete description of a contiguous portion of the name space plus pointers to other zones. A zone can be a single node or the whole tree, but is typically a subtree. An organization gets control of a zone by persuading its parent to insert RRs marking the zone division; the CS department got `cs.washington.edu` by having `washington.edu` insert RRs marking a boundary between the two.

A zone administrator should provide redundancy by running multiple name servers. The zone is maintained as a master file on a master server, and secondary servers either refresh manually or run a zone refresh algorithm that polls a serial number and pulls updates when it increases. Zone transfers happen over TCP. A name server can host any number of zones, contiguous or not, and marks responses served from its own zone data (rather than cache) as authoritative.

### Caching

Every RR has a TTL in seconds, the maximum time a resolver may reuse the cached record. Zero means no caching. The zone administrator sets TTLs as part of the zone definition. Cached answers are meant to be as good as authoritative ones, though when both are available the authoritative answer wins. Negative responses get cached too, such as a nonexistent domain or a domain with no data of the requested type, which spares repeated queries for names that will keep failing.

### Root servers

Resolvers search downward from domains they already know, and carry hints pointing at the root servers and the top of their local domain. A resolver that can reach a root server can find any domain. A resolver that gets partitioned can still resolve names inside its local domain. Root servers therefore have to be highly available and geographically distributed.

## What the design got right

The hierarchy is doing a lot of work. It models namespaces after organizations, and the same structure gives natural units for distributing and delegating data. Caching being central to the design made good performance and availability possible while keeping policy and implementation simple, and negative caching in particular is a general optimization that costs little.

Stepping back, a distributed namespace was the inevitable shape of the solution. `HOSTS.TXT` could not scale with the internet's growth in either complexity or size. The design requirements were deliberately general, and the balance struck between flexibility and simplicity is a big part of why adoption went as well as it did.

## Evidence

The paper is a retrospective, so its evidence is deployment experience. DNS replaced `HOSTS.TXT` and absorbed the internet's growth. The underlying network turned out far less performant than the designers expected, and DNS coped because the common case, a cached answer, is fast, and multiple levels of caching cut the round trips needed after the initial queries.

## Assumptions and limits

Decentralized management brings inconsistency in cached answers, difficulty pushing updates through the system in real time, and murky accountability. The system also exposes no versioning metadata and no way to tune runtime performance, which some applications and organizations could use.

## Open questions

- What level of security was considered in the original design, and how has that evolved since?
- Are the type and class fields still over-allocated? Could versioning be introduced within those spare bits?

## Sources

- [Development of the Domain Name System](https://courses.cs.washington.edu/courses/cse551/09sp/papers/dns.pdf)

## Related notes

- [[systems/research/internet-design-philosophy|Design Philosophy of DARPA Internet Protocols]]
- [[systems/research/end-to-end-arguments-in-sys-design|End-to-End Arguments in System Design]]
