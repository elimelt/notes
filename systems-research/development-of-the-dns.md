---
title: Development of the Domain Name System
category: systems
tags: dns, domain-name-system, networking, systems
description: Paper review of the paper Development of the Domain Name System
---

# [source](https://courses.cs.washington.edu/courses/cse551/09sp/papers/dns.pdf)

###### Development of the Domain Name System

---

### What is the Problem?

The original solution for naming was to share single file `HOSTS.TXT` that contained all the hostnames and their corresponding IP addresses. This originally worked fine, since the number of hosts was proportional to the number of timesharing systems. However, as the internet evolved to consist of many networks, each with many hosts, this solution became unscalable. Instead, a distributed database was needed to store the mappings of hostnames to IP addresses. This paper describes the development of the Domain Name System (DNS) to solve this problem.

### Summary 

#### Design Requirements

- Provide all current functionality of `HOSTS.TXT`
- Allow for distributed maintenance
- No obvious size limits for names, name components, data associated with names, etc.
- Interoperability with existing systems (DARPA Internet)
- Tolerable performance
- Independence from the underlying network topology, and ability to encapsulate other name spaces
- Avoid forcing a single OS/architecture/organization structure. Should support both large time-sharing systems and individual PCs

#### Architecture

Two main components:
- **name server**: repository of mappings of names to data, responsible for answering queries
- **resolver**: interface for client programs to query name servers

The lines are blurred, and particular this architecture allows for organizations to maintain a centralized name server/resolver to be shared by all hosts in the organization, meaning PCs wouldn't need to run their own resolver to resolve names.

#### Name space

Domains are organized hierarchically, with all names sharing a common "null" root. DNS doesn't make any assumptions about the structure or presentation of names, but does suggest that domains should model the organization they represent.

#### Data attached to names

DNS allows for arbitrary data to be attached to names, but does organize data into types. Each name has corresponding **resource records** (RRs) that contain a type and class, as well as unstructured application data. Type represents the abstract resource, and class represents the protocol family/instance, or in some case functionality (e.g. a universal mail registry).

Types and classes were originally expected to be often extended, but it is pretty rare in practice, and more bits than necessary were allocated to these fields.

Interestingly, when responding to queries, a name server is free to return any data in wants in addition to the requested data. It can therefore anticipate future queries to cut down on the number of round trips. For example, root servers include both the host address, and name when passing back the name of a host.

#### Database distribution

##### Zones

A complete description of a contiguous portion of the domain name space, along with some "pointers" to other zones. Zones can be either a single node, or the whole tree, but are typically a subtree.

An organization can get control of a zone by persuading its parent to insert RRs in its zone to mark a zone division, e.g. the CS dept. got `cs.washington.edu` by having `washington.edu` insert RRs to mark a zone boundary between `washington.edu` and `cs.washington.edu`.

An organization managing a zone should provide redundancy by having multiple name servers for the zone, and should maintain a "master file" and make it available within a "master" server. Then, secondary servers are either manually refreshed, or use a zone refresh algorithm which queries serial numbers and updates if it has increase. Zone transfers happen over TCP.

NSs can support any number of zones, which may or may not be contiguous. In fact, they don't even need to be in corresponding zone. When an NS responds to a query without cached data, it marks that response as "authoritative".

##### Caching

Each RR has an associated TTL in seconds, which is the maximum time a resolver can reuse the cached record (zero TTL means no caching). The administrator of a zone sets the TTL for each RR as part of their zone definition.

Cached answers should be "as good" as authoritative answers, and the design seeks to enable updates before TTL expiration. If both are available, the authoritative answer should be preferred.

As am optimization, negative responses should also be cached, e.g. non existent domain, or domain with no data associated.

#### Root servers

Resolvers search "downward" from domains they already know. They usually also have "hints" pointing at root servers and the top of their local domain. Thus, if a resolver can find a root server, it can find any domain. On the other hand, if a resolver is partitioned, it can at least resolve names in its local domain.

Root servers must be highly available and distributed geographically.

### Key Insights

- Seeing as how the internet is distributed in nature, a distributed database/namespace management system was inevitable. The predecessor, `HOSTS.TXT`, simply couldn't scale with the growth of the internet, both in terms of complexity and size.
- DNS was designed around very general requirements for functionality, but also struck a balance between flexibility and simplicity in order to be widely adoptive and performant.

### Notable Design Details/Strengths 

- Using a hierarchical structure gave a very powerful way to model namespaces after organizations, while also giving very natural ways to distribute and manage data, ultimately proving to be an extremely effective interface for the problem at hand.
- Caching being such a central part of the design made it possible to achieve good performance and availability, while remaining simple in terms of policy and implementation. In particular, negative caching is a very general but effective optimization.

### Limitations/Weaknesses 

- Decentralized management can lead to inconsistencies in cached answers, difficulty in pushing updates through the system in real-time, accountability issues, etc.
- The system doesn't expose versioning metadata,nor any way of tuning runtime performance, which could be useful for some applications/organizations with specific needs.

### Summary of Key Results

- DNS successfully replaced `HOSTS.TXT` with a far more scalable and extensible system, particularly in terms of growth in complexity and size of the internet.
- Although the underlying internet was far less performant than initially expected, DNS was able to cope with this by making the common case of cached answers very fast, especially considering the multiple levels of caching involved which drastically reduced the number of round trips needed to resolve a name after some initial queries.

### Open Questions

- What level of security was considered in the design of DNS, and how has this evolved over time?
- Are type/class fields still over-allocated? If so, could it be possible to introduce some sort of versioning within these fields?
