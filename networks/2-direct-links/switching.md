---
title: Switched Ethernet
category: Networks
tags: ethernet, switching, MAC address, forwarding table, bridge
description: Covers the implementation of switched Ethernet networks, including the use of bridging tables for MAC address forwarding, the distributed spanning tree algorithm for network topology discovery, and different switch architectures such as software switches and bare-metal switches. Discusses software-defined networking as an approach to managing and configuring Ethernet switches programmatically.
---

# Switching

## Switched Ethernet

**L2 Switches** are used within enterprise and university networks to connect multiple devices on the same network. Historically, they were used as a "*bridge*" to connect multiple Ethernet segments, but are now typically used in a "*point-to-point*" configuration.

**Learning Switches** are a type of L2 switch that learns the MAC addresses of devices connected to it. When a device sends a frame to the switch, the switch records the source MAC address and the port into its forwarding table. When a device sends a frame to the switch, the switch looks up the destination MAC address in its forwarding table and forwards the frame to the appropriate port. If the destination MAC address is not in the table, the switch floods the frame to all ports except the one it was received on.

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

### Distributed Spanning Tree Algorithm

Initially, all switches assume they are the root of the tree. Switches *broadcast* **configuration messages** that contain the `following:

- The ID of the sender
- The ID for what the sender believes to be the root
- The distance (in hops) of the sender to what the sender believes to be the root

Each swtich listens to configuration messages being broadcasted, and remebers the "best" root it has seen. This is defined as:

- The lowest root ID
- Equal root IDs, but lower distance
- Equal root IDs and distances, but lower sender ID

Once it identifies the best root, it adds one to the disance and broadcasts a configuration message with the new root and distance. If a switch realizes it isn't the root anymore, it stops broadcasting configuration messages and starts forwarding frames (still adding 1). Similarly, once a switch recieves a message that indicates a better path, it stops sending messages over that port.

Once the system stabilizes, the only the root will be sending configuration messages, and all other switches will be forwarding.

```c
// Psuedo code for the distributed spanning tree algorithm

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

To create a switch, all you need to do is buy a general-purpose processor and equip it with multiple network interfaces. However, switches that deliver high-end performance typically take advantage of additional hardware acceleration. These are referred to as hardware switches, although both approaches obviously include a combination of hardware and software.

The implementation of switches and routers have so much in common that a network administrator typically buys a single forwarding box and then configures it to be an L2 switch, an L3 router, or some combination of the two.

### Software Switches

The performance of switches is limited by the need to pass packets through main memory. This can be a bottleneck, especially for short packets. The cost of processing each packet, such as parsing its header and making forwarding decisions, can also be a limiting factor. Non-trivial algorithms used by switches, like the spanning tree algorithm, are not directly part of the per-packet forwarding decision. Table lookups are often the most costly routine executed on a per-packet basis.

### Bare-Metal Switches

The distinction between the control plane (background processing) and the data plane (per-packet processing) is important. Recent advances in domain-specific processors have made it possible to build high-performance switches that combine the performance of ASICs with the agility of software. These switches can be programmed to be L2 switches, L3 routers, or a hybrid.

Bare-metal switches using Network Processing Units (NPUs) have become popular. NPUs are optimized for processing packet headers and making forwarding decisions. They can process packets at rates measured in Terabits per second (Tbps). The exact programming of an NPU depends on the chip vendor.

Internally, an NPU utilizes fast SRAM-based memory, TCAM-based memory for matching bit patterns, and a multi-stage forwarding pipeline. The use of a multi-stage pipeline allows for efficient packet processing and high throughput.

The networking industry is entering a commoditized world, similar to the computing industry, where standardized components and open source software are available for building high-performance switches.

### Software Defined Networks

SDN (Software Defined Networks) decouples the network control plane from the data plane, allowing routing algorithms to run on software and packet forwarding decisions to be made by bare-metal switches. The standard interface between the control and data planes, known as OpenFlow, enables interoperability between different implementations. This concept of disaggregation has led to the trend of using commodity servers and bare-metal switches in network infrastructure.

Another important aspect of disaggregation is that a logically centralized control plane can be used to control a distributed network data plane. This allows for scalability and availability, as the two planes can be configured and scaled independently. Cloud providers have embraced this approach, using SDN-based solutions within their datacenters and across their backbone networks.

The Network Operating System (NOS) is a key enabler for SDN's success. It provides high-level abstractions and a Network Map to simplify network control functionality. The NOS detects changes in the network and the control application implements desired behavior on an abstract graph. By centralizing this logic, a globally optimized solution can be achieved.