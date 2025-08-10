---
title: Domain Name System (DNS)
category: Networks
tags: domain name system, name resolution, distributed database, top-level domain, name server
description: The Domain Name System (DNS) is a distributed database that translates human-readable domain names into IP addresses, enabling communication on the internet. It covers the hierarchical namespace structure, the resolution process using iterative and recursive queries, and the role of local nameservers and root name servers. The document also discusses the DNS protocol, including zone management and caching mechanisms, which are crucial for the efficient and scalable operation of the global domain name system.
---

# Domain Name System (DNS)

## Namespaces

- **Names** are higher-level, human-readable identifiers for resources.
- **Addresses** are lower-level, machine-readable identifiers for resources.
- **Resolution/Lookup** is the process of mapping names to addresses.

## Before DNS

Machines retrieved a file called `hosts.txt` from a centralized server to resolve names to addresses. 

This approach was not scalable, as the `hosts.txt` file would have to be updated on every machine on the network.

## DNS

DNS is a naming service that maps names to IP addresses and vice versa. It is a distributed database implemented in a hierarchy of name servers.

- All DNS names end with a dot, which represents the root of the DNS hierarchy.
- The rightmost part of a DNS name is called the **top-level domain** (TLD).
- The top-level domain is managed by a **registry**.

### DNS Zones

Zones are a way to divide the domain name space into manageable sections. A zone is a contiguous portion of the global DNS namespace. 

#### Example
- EDU registry is responsible for the `.edu` TLD.
- UW is responsible for the `washington.edu` domain.
- The Allen School is responsible for the `cs.washington.edu` domain.

Each zone has one or more **name server** that is authoritative for the zone. The name server is responsible for maintaining the zone's records. For instance, the name server for `washingon.edu` is responsible for maintaining the records for `cs.washington.edu`.

### DNS Resolution

When a client wants to resolve an unknown name to an IP address, it sends a query to a DNS resolver. The resolver then sends a query to a root name server, which responds with the address of a TLD name server. The resolver then sends a query to the TLD name server, which responds with the address of the authoritative name server for the domain. The resolver then sends a query to the authoritative name server, which responds with the IP address of the domain.

### Iterative vs. Recursive Resolution

- **Recursive queries** are queries in which the DNS resolver asks the name server to return the answer directly.
- **Iterative queries** the name server returns the next name server to query.

Recursive queries are nice because it offloads the client burden for address resolution. Also lets the server cache over a pool of clients.

Iterative queries are nice because it minimizes the complexity of the server, and is easier to build high load servers. Also gives the client more control over the resolution process.

### DNS Caching

Latency needs to be fairly low for DNS resolution, so caching is important. Nameservers cache query results (including partial/iterative answers) for the duration of their TTL (time to live).

The caching is hierarchical, with the root servers at the top, and the client at the bottom. This means that the root servers are the most heavily loaded, and the client is the least heavily loaded.

### Local Nameservers

Local nameservers are the first point of contact for a client's DNS resolution. They are usually provided by the ISP, and are responsible for caching DNS records for a short period of time.   

They can also run on a host, or at an access point. Alternatively, you can use a public DNS resolver like Google's. Local name servers are typically configured via DHCP.

### Root Name Servers

Root (.) is served by 13 root servers (labeled `a.root-servers.net` through `m.root-servers.net`). These servers are distributed around the world and are operated by 12 independent organizations.

There are more than 250 distributed server instances to increase the fault tolerance and availability of the root server system. Most servers are reached by **IP anycast**, which means that the same IP address is advertised from multiple locations.

## DNS Protocol

DNS uses the User Datagram Protocol (UDP) on port 53 to serve requests. Uses ARQ for reliability. Messages are linked by a 16-bit ID field.

Servers can be replicated to handle load and reliability. Queries can return multiple records, and the client can choose which one to use.

Security is a major concern for DNS. DNSSEC is a suite of extensions that add security to the DNS protocol by signing DNS data, but it is not widely adopted.