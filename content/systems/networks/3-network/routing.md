---
title: Routing
aliases:
  - networks/3-network/routing
category: Networks
tags:
  - networks
  - routing
  - distance-vector
  - link-state
  - rip
  - ospf
date: 2024-02-25
updated: 2026-07-30
status: evergreen
description: Intra-domain routing, covering the routing table vs. forwarding table distinction, the network-as-graph model, distance vector routing with RIP, and link state routing with reliable flooding, forward search, and OSPF.
sources:
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
  - title: "RFC 2453: RIP Version 2"
    url: https://datatracker.ietf.org/doc/html/rfc2453
    type: rfc
  - title: "RFC 2328: OSPF Version 2"
    url: https://datatracker.ietf.org/doc/html/rfc2328
    type: rfc
---

## Purpose

Explain how routers inside a network decide where packets go. Covers the two data structures involved, the graph model of the problem, and the two families of intra-domain routing protocols, distance vector and link state. Routing between networks is a different problem, covered in [[systems/networks/3-network/BGP|BGP]].

## Routing table vs. forwarding table

Routers forward packets toward destinations outside the local network. Two tables show up in that job, and it helps to keep them apart (the distinction here follows [Peterson & Davie](https://book.systemsapproach.org/)):

- The **routing table** is the data structure the routing protocol builds. It maps network prefixes to information about how to reach them, including the next hop router and the metric the protocol computed. It exists to make routing decisions.
- The **forwarding table** is the structure consulted for every packet, so it is optimized for fast lookup. It maps a network prefix to the outgoing interface and whatever link-level information the router needs to actually transmit the frame, such as the next hop's MAC address.

The routing table changes when the routing protocol learns something new about the topology. The forwarding table is derived from it. The rest of this note is about how the routing table gets built.

## The network as a graph

Model the network as a graph of routers (nodes) and links (edges). To simplify, treat the graph as undirected and weighted, where the weight of an edge is the cost of sending a packet over that link. A directed graph is more accurate in practice, since the two directions of a link can behave differently, but the undirected model is simpler to reason about.

The basic problem of routing is finding lowest-cost paths between nodes. You could run Dijkstra's algorithm once (see [[algorithms/graphs-intro|graph fundamentals]]) and save the answers as the routing table, but a static computation has problems:

- It doesn't handle node or link failures.
- It doesn't handle new nodes or links.
- Edge costs can't change.
- It doesn't scale to large networks.

So routing protocols are distributed and adaptive, running independently on each router.

## Distance vector routing (RIP)

The **Routing Information Protocol (RIP)** ([RFC 2453](https://datatracker.ietf.org/doc/html/rfc2453)) is the classic distance vector protocol. Each router exchanges routing information with its neighbors and builds up a distributed picture of the network. The update rule is the same one used by **Bellman-Ford**.

How it operates:

- **Hop count metric**: RIP counts the routers a path traverses and treats the lowest hop count as best.
- **Routing table**: each router keeps an entry per reachable network with its hop count and the next hop on the path.
- **Periodic updates**: routers periodically advertise their routing table entries to their neighbors, even when nothing has changed.
- **Triggered updates**: a router also sends an update immediately whenever it changes its own table.
- **Failure detection**: if a router hears nothing from a neighbor for long enough, it assumes the neighbor is down. A router can also probe its neighbors with a control message.

What it does well: the protocol is simple to implement and understand, updates propagate quickly, and it works fine in small networks.

Where it falls down: hop count ignores bandwidth and delay, so the chosen path can be a bad one. Distance vector protocols are prone to the counting-to-infinity problem, where two routers keep raising each other's estimate of a dead route one hop at a time. Split horizon mitigates it (don't advertise a route back to the neighbor you learned it from). In large networks, frequent updates load the routers and convergence slows down.

### Implementation

A distance vector routing table merge, adapted from [Peterson & Davie](https://book.systemsapproach.org/):

```c
#define MAX_ROUTES      128     /* maximum size of routing table */
#define MAX_TTL         120     /* time (in seconds) until route expires */

typedef struct {
    NodeAddr  Destination;    /* address of destination */
    NodeAddr  NextHop;        /* address of next hop */
    int       Cost;           /* distance metric */
    u_short   TTL;            /* time to live */
} Route;

int      numRoutes = 0;
Route    routingTable[MAX_ROUTES];

void mergeRoute (Route *new) {
    int i;
    for (i = 0; i < numRoutes; ++i) {
        if (new->Destination == routingTable[i].Destination) {
            if (new->Cost + 1 < routingTable[i].Cost)
                break; /* found a better route */
            else if (new->NextHop == routingTable[i].NextHop)
                break; /* next hop may have changed */
            else
                return;
        }
    }
    if (i == numRoutes) {
        if (numRoutes < MAX_ROUTES)
            numRoutes++;
        else
            return; /* can't fit this route in table so give up */
    }
    routingTable[i] = *new;
    routingTable[i].TTL = MAX_TTL; /* reset TTL */
    routingTable[i].Cost++;
}

void updateRoutingTable (Route *newRoute, int numNewRoutes) {
    for (int i = 0; i < numNewRoutes; ++i)
        mergeRoute(&newRoute[i]);
}
```

Actual RIP runs on UDP port 520, and its messages carry a list of route entries:

```text
RIP Message:
    Version
    Command (request, response, update)
    Number of entries
    RIP Entry (variable size)
        Address Family Identifier
        Route Tag
        IP Address
        Next Hop IP Address
        Metric
```

RIP is a limited implementation of distance vector routing. It assigns a cost of 1 to each hop, so it computes fewest-hop paths, and a metric of 16 means unreachable, which caps usable paths at 15 hops. Most modern networks use something else.

## Link state routing

Distance vector routers only tell their neighbors what they can reach. Link state routers instead tell everyone exactly what their local neighborhood looks like, and let each router compute paths from the full map. Each node creates a **Link State Packet (LSP)** containing:

- The ID of the node that created the LSP
- A list of that node's directly connected neighbors, with the cost of the link to each one
- A sequence number, incremented each time the LSP is updated
- A time to live, decremented at each hop

These packets are **flooded** through the network, meaning each node forwards them to all of its neighbors.

### Reliable flooding

The sequence number and TTL keep flooding sane. Adjacent nodes use ACKs and retransmissions, so an LSP reliably crosses each link. When a node already has an LSP from the same origin, it keeps the one with the higher sequence number, so stale information loses. On receiving a new LSP, a node stores it and forwards it to all neighbors except the one it came from.

Nodes generate new LSPs at regular intervals and whenever an adjacent node goes down. Neighbors exchange "hello" packets to show they are alive, and a node that stops hearing hellos from a neighbor assumes it is down and generates a new LSP. The periodic LSPs should be infrequent, so the network converges quickly on failures without wasting resources when nothing changes.

When a node receives an LSP with TTL 0, it deletes that record from its own database and floods the expired LSP so every other node deletes it too.

### Route calculation

Each node runs a shortest-path computation over its LSP database. The textbook algorithm is Dijkstra's. With $N$ the set of nodes, $s$ the node doing the computation, $l(w,n)$ the cost of the link between $w$ and $n$, $C(n)$ the current best cost from $s$ to $n$, and $M$ the set of nodes whose cost is settled:

```text
M = {s}
for each n in N - {s}:
    C(n) = l(s,n)
while N != M:
    M = M + {w} such that C(w) is the minimum for all w in (N - M)
    for each n in (N - M):
        C(n) = MIN(C(n), C(w) + l(w,n))
```

#### Forward search

Real implementations use **Forward Search**, which is Dijkstra's algorithm restated with two lists, `Confirmed` and `Tentative`, whose entries are `(Destination, Cost, NextHop)`:

1. Initialize the `Confirmed` list with an entry for myself with cost 0.
2. Call the node just added to `Confirmed` in the previous step `Next`, and select its LSP.
3. For each neighbor of `Next`, calculate the cost to reach that neighbor as the cost from myself to `Next` plus the cost from `Next` to the neighbor. If the neighbor is on neither list, add `(Neighbor, Cost, NextHop)` to `Tentative`, where `NextHop` is the direction I go to reach `Next`.
4. If the neighbor is already on `Tentative` with a higher cost, replace its entry with `(Neighbor, Cost, NextHop)`.
5. If `Tentative` is empty, stop. Otherwise move the lowest-cost entry from `Tentative` to `Confirmed` and go back to step 2.

### Open Shortest Path First (OSPF)

**OSPF** ([RFC 2328](https://datatracker.ietf.org/doc/html/rfc2328)) is the widely deployed link state protocol. It adds several features to basic link state routing:

- Authentication: OSPF can authenticate its messages, so an unauthorized node can't inject false routing information.
- Hierarchy: the network partitions into **areas**, and a router only needs the topology of its own area. This is the same scaling move [[systems/networks/3-network/global-internet|the global Internet]] makes with autonomous systems.
- Load balancing: OSPF can assign multiple paths to the same destination and split traffic between them.

Of the five OSPF message types, type 1 is the "hello" message a router sends to its peers to show it is still alive and connected. The remaining types request, send, and acknowledge link-state messages.

OSPF floods Link State Advertisements (LSAs) rather than LSPs. An LSA carries per-link information: the Link ID (typically the router ID at the far end of the link), the Link Data, and the metric, meaning the cost of the link. Type of service (TOS) information lets OSPF choose different routes for packets based on the TOS field in the IP header.

#### Metrics

The ARPANET tested different approaches to link-cost calculation, and the history is a caution about clever metrics (recounted in [Peterson & Davie](https://book.systemsapproach.org/)). The original metric measured queued packets on each link, which ignored bandwidth and latency. A later version used measured delay as the load signal, which accounted for both, but it was unstable under heavy load and produced a huge range of link values. A third revision compressed the metric range, accounted for link type, and smoothed the variation over time.

In real deployments, metrics change rarely, if at all, and only under the control of a network administrator. Static metrics are the norm, commonly a constant times $1/\text{link bandwidth}$.

## Related notes

- [[systems/networks/3-network/BGP|BGP]]
- [[systems/networks/3-network/global-internet|the global Internet]]
- [[algorithms/graphs-intro|graph fundamentals]]
