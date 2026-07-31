---
title: Domain Name System (DNS)
category: Networks
tags:
  - DNS
  - name-resolution
  - distributed-database
  - top-level-domain
  - name-server
date: 2024-03-07
updated: 2026-07-30
status: evergreen
description: How DNS maps names to IP addresses, covering the hierarchical namespace, zones, iterative and recursive resolution, caching, root servers, and the protocol itself.
sources:
  - title: "RFC 1034: Domain Names - Concepts and Facilities"
    url: https://datatracker.ietf.org/doc/html/rfc1034
    type: spec
  - title: "Root Servers"
    url: https://root-servers.org/
    type: docs
  - title: "CSE 461: Computer Networks, University of Washington"
    url: https://courses.cs.washington.edu/courses/cse461/
    type: lecture
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Explain how DNS resolves human-readable names into IP addresses at internet scale, and why its hierarchy and caching are what make that scale work.

## Namespaces

Names are high-level, human-readable identifiers for resources. Addresses are low-level, machine-readable identifiers. Resolution, or lookup, maps names to addresses.

## Before DNS

Machines fetched a file called `hosts.txt` from a centralized server and resolved names against it locally. Every name change meant redistributing the file to every machine on the network, which stopped scaling as the internet grew. DNS ([RFC 1034](https://datatracker.ietf.org/doc/html/rfc1034)) replaced it.

## The DNS hierarchy

DNS is a naming service that maps names to IP addresses and back. It is a distributed database implemented as a hierarchy of name servers, and the namespace itself is hierarchical.

- Every fully qualified DNS name ends with a dot, the root of the hierarchy.
- The rightmost label is the top-level domain (TLD), like `.edu` or `.com`.
- Each TLD is managed by a registry.

### Zones

Zones divide the namespace into manageable pieces. A zone is a contiguous portion of the global namespace under one administrator. For example, the EDU registry runs the `.edu` TLD, UW runs `washington.edu`, and the Allen School runs `cs.washington.edu`. Each zone has one or more authoritative name servers that maintain its records. Authority can be delegated, so the servers for `washington.edu` delegate `cs.washington.edu` to the Allen School's servers.

## Resolution

A client resolving an unknown name sends the query to a DNS resolver. The resolver asks a root name server, which answers with the address of the right TLD name server. The TLD server answers with the authoritative name server for the domain, and that server finally answers with the IP address.

### Iterative vs. recursive queries

In a recursive query, the resolver asks a server to return the final answer directly, and that server does the rest of the walking. In an iterative query, each server just returns the next server to ask.

Recursive service takes the resolution burden off the client and lets the server build a cache shared across its whole pool of clients. Iterative service keeps the server simple, which makes high-load servers easier to build, and leaves the client in control of the process. Root and TLD servers answer iteratively, and local resolvers typically offer recursion to their clients.

### Caching

Resolution sits on the critical path of nearly every connection, so latency matters and caching does the heavy lifting. Nameservers cache query results, including the partial answers from iterative resolution, for the duration of each record's TTL. The caching follows the hierarchy. Answers near the root change rarely and get cached widely, which is what keeps the root servers from being crushed by the world's lookups.

### Local nameservers

The local nameserver is a client's first stop. It is usually run by the ISP, though it can run on the host itself or at an access point, and public resolvers like Google's 8.8.8.8 are an alternative. Clients typically learn their local nameserver via DHCP.

### Root name servers

The root is served by 13 named servers, `a.root-servers.net` through `m.root-servers.net`, operated by 12 independent organizations. Each name is actually hundreds of server instances spread around the world, reached by IP anycast, where the same IP address is advertised from many locations and routing delivers the query to a nearby one. Current instance counts and operators are listed at [root-servers.org](https://root-servers.org/).

## Protocol

DNS runs over UDP on port 53, see [[networks/4-transport/UDP|UDP]]. Reliability comes from the client retransmitting on timeout, with a 16-bit ID field linking each response to its query. Servers are replicated for load and availability, queries can return multiple records, and the client picks which to use.

Plain DNS has no authentication, so responses can be spoofed. DNSSEC adds signatures over DNS data to fix this, but adoption is limited.

## Related notes

- [[networks/5-application/HTTP|HTTP]]
- [[networks/5-application/CDNs|content delivery networks]]
- [[networks/3-network/global-internet|the global Internet]]
