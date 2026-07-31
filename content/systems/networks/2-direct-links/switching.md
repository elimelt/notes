---
title: Switched Ethernet
aliases:
  - networks/2-direct-links/switching
category: Networks
tags:
  - ethernet
  - switching
  - mac-address
  - forwarding-table
  - spanning-tree
  - sdn
date: 2024-02-07
updated: 2026-07-30
status: evergreen
description: How L2 switches forward frames. Covers learning switches and their forwarding tables, the distributed spanning tree algorithm, switch implementation from software to NPUs, and the SDN split between control and data planes.
sources:
  - title: "Computer Networks: A Systems Approach (Peterson and Davie)"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Modern Ethernet is switched. Instead of sharing one cable and arbitrating with [[systems/networks/2-direct-links/multiple-access|CSMA/CD]], each host gets a point-to-point link to a switch that forwards frames by MAC address. This note covers how switches learn where to forward, how they avoid loops, and how they are built.

## Learning switches

**L2 switches** connect devices inside enterprise and university networks. Historically a switch acted as a *bridge* joining multiple Ethernet segments. Today it usually connects hosts point-to-point.

A **learning switch** builds its forwarding table from traffic. When a frame arrives, the switch records the source MAC address and the arrival port. When it needs to forward a frame, it looks up the destination MAC address in the table and sends the frame out the recorded port. If the destination isn't in the table, it floods the frame out every port except the one it arrived on. Flooding is always correct, just wasteful, so the table is an optimization that the switch can rebuild at any time.

The following table-update code is adapted from [Peterson and Davie](https://book.systemsapproach.org/):

```c
#define BRIDGE_TAB_SIZE   1024  /* max size of bridging table */
#define MAX_TTL           120   /* time (in seconds) before an entry is flushed */

typedef struct {
    MacAddr     destination;    /* MAC address of a node */
    int         ifnumber;       /* interface to reach it */
    u_short     TTL;            /* time to live */
    Binding     binding;        /* binding in the Map */
} BridgeEntry;

int     numEntries = 0;
Map     bridgeMap = mapCreate(BRIDGE_TAB_SIZE, sizeof(BridgeEntry));

void
updateTable (MacAddr src, int inif)
{
    BridgeEntry       *b;

    if (mapResolve(bridgeMap, &src, (void **)&b) == FALSE )
    {
        /* this address is not in the table, so try to add it */
        if (numEntries < BRIDGE_TAB_SIZE)
        {
            b = NEW(BridgeEntry);
            b->binding = mapBind( bridgeMap, &src, b);
            /* use source address of packet as dest. address in table */
            b->destination = src;
            numEntries++;
        }
        else
        {
            /* can't fit this address in the table now, so give up */
            return;
        }
    }
    /* reset TTL and use most recent input interface */
    b->TTL = MAX_TTL;
    b->ifnumber = inif;
}
```

## Distributed spanning tree algorithm

Flooding breaks if the topology has loops, since frames circulate forever. The switches therefore agree on a spanning tree of the topology and only forward along it. The algorithm is Radia Perlman's, and it runs without any central coordination.

Initially every switch assumes it is the root. Switches broadcast **configuration messages** containing:

- the ID of the sender
- the ID of what the sender believes is the root
- the sender's distance (in hops) from that root

Each switch listens to the configuration messages it receives and remembers the best root it has seen, judged in this order:

- lowest root ID
- equal root IDs, lower distance
- equal root IDs and distances, lower sender ID

When a switch adopts a better root, it adds one to the advertised distance and rebroadcasts. A switch that realizes it isn't the root stops originating configuration messages and only forwards the root's (still adding 1 to the distance). A switch that hears a better path over a port stops sending messages out that port. When the system stabilizes, only the root originates configuration messages, and every other switch just forwards them along the tree.

```c
// Pseudocode for the distributed spanning tree algorithm

#define MAX_BRIDGES 1024

struct bridge {
    macaddr     root;       // ID of the root
    int     distance;       // distance to the root
    int     port;           // port to reach the root
    int     TTL;            // time to live
};

struct message {
    macaddr root;           // ID of the root (mac address)
    int     distance;       // distance to the root
    macaddr     sender;     // ID of the sender (mac address)
};

struct bridge bridges[MAX_BRIDGES];
struct message state;

void
update(struct message* m, int port)
{
    if (m->root < state.root || (m->root == state.root && m->distance < state.distance))
    {
        state.root = m->root;
        state.distance = m->distance + 1;
        state.sender = m->sender;
        state.port = port;
    }
    else if (m->root == state.root && m->distance == state.distance && m->sender < state.sender)
    {
        state.sender = m->sender;
        state.port = port;
    }
}

void
broadcast(struct message* m)
{
    for (int i = 0; i < MAX_BRIDGES; i++)
        if (i != state.port)
            send(i, m);
}
```

## Implementation

A switch can be as simple as a general-purpose processor with multiple network interfaces. High-end switches add hardware acceleration, and get called hardware switches, though every switch mixes hardware and software. Switches and routers share so much implementation that a network administrator often buys one forwarding box and configures it as an L2 switch, an L3 router, or both. Peterson and Davie cover this ground in depth in [their chapter on switching](https://book.systemsapproach.org/).

### Software switches

A software switch is limited by the cost of passing every packet through main memory, which bites hardest on short packets. Per-packet processing costs like header parsing add up too, and table lookups are usually the most expensive per-packet routine. Control logic like the spanning tree algorithm stays off the per-packet path.

### Bare-metal switches

The split between the **control plane** (background processing) and the **data plane** (per-packet processing) drives modern switch design. Domain-specific processors now deliver ASIC-level forwarding performance with software-level programmability, so one box can be programmed as an L2 switch, an L3 router, or a hybrid.

Bare-metal switches built on Network Processing Units (NPUs) are the common form. An NPU is optimized for parsing packet headers and making forwarding decisions, at rates measured in Tbps. Internally it combines fast SRAM, TCAM for bit-pattern matching, and a multi-stage forwarding pipeline that keeps many packets in flight at once. Programming details vary by chip vendor.

### Software defined networking

SDN decouples the control plane from the data plane. Routing algorithms run as software on servers, and the forwarding decisions they compute get pushed down to bare-metal switches. OpenFlow standardized the interface between the two planes, so controllers and switches from different vendors interoperate.

Splitting the planes also means a logically centralized control plane can drive a distributed data plane, and each side can scale independently. Cloud providers run SDN inside their datacenters and across their backbones for exactly this reason. The Network Operating System (NOS) makes the model usable, detecting network changes and exposing an abstract network map so control applications can compute globally optimized behavior against a graph instead of programming individual boxes.

## Related notes

- [[systems/networks/2-direct-links/multiple-access|multiple access]]
- [[systems/networks/2-direct-links/framing|framing]]
