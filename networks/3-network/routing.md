#

Routers are devices within a network that handle forwarding packets out of the network. They use a **routing table** to determine the best path for a packet to reach its destination. The routing table contains information about known networks, including the next hop router to reach them.

## Forwarding Table vs. Routing Table

**1. Scope:**

- **Routing Table:** Big picture. Holds information on **all known networks** reachable through the router. Includes destination networks, subnet masks, and the next hop router to reach them.
- **Forwarding Table:** Detail-oriented. Contains information about **directly connected devices** on the same network segment. Maps MAC addresses to physical ports for efficient forwarding within the local network.

**2. Information:**

- **Routing Table:** Stores **network-level information**, including:
  - Destination subnet address
  - Subnet mask
  - Next hop router's IP address
  - Metrics (e.g., cost, hop count)
  - Additional information (e.g., interface)
- **Forwarding Table:** Holds **hardware-level information**, like:
  - MAC address of a device
  - Corresponding physical port on the router

**3. Dynamic Updates:**

- **Routing Table:** More dynamic, constantly updated based on routing protocols (e.g., RIP, OSPF, BGP) to reflect network changes.
- **Forwarding Table:** Static or dynamically updated based on learned MAC addresses of connected devices. Updates are faster than routing table changes.

**4. Size:**

- **Routing Table:** Generally larger, containing entries for all known networks, even those not directly connected.
- **Forwarding Table:** Smaller, only containing entries for devices physically connected to the router's ports.

**5. Function:**

- **Routing Table:** Used to **make routing decisions** and determine the best path for packets to reach their destination networks.
- **Forwarding Table:** Used to **physically forward packets** to the next device on the local network based on their MAC addresses.

**Analogy:** Think of the routing table as a city map showing different neighborhoods and highways. The forwarding table is like a detailed building floor plan within a specific neighborhood, guiding you to specific rooms.

## The Network as a Graph

Model the internet as a graph of routers (nodes) and links (edges). To simplify, we can model the graph as an _undirected_ **weighted** graph, where the weight of an edge represents the cost of sending a packet over that link. In practice, the internet is more accurately modeled as a _directed_ graph, but the undirected model is simpler.

The basic problem of routing is to find the shortest path between nodes in the graph. One could use **Dijkstra's algorithm** to find paths, and then save them to disk/memory as the routing table. However:

- It does not deal with node or link failures.
- It does not consider the addition of new nodes or links.
- Edge costs cannot change
- It does not scale well to large networks.

Therefore, routing protocols are typcially distributed and adaptive, running idependently on each router.

## Distance Vector Routing (RIP)

The **Routing Information Protocol (RIP)**, is a fundamental algorithm for navigating paths of the internet. It operates by exchanging routing information between neighboring routers, building a distributed understanding of the network topology. It is in the same class of algorithms as **Bellman-Ford**.

**Core Concepts:**

- **Hop Count:** RIP utilizes a simple metric: the number of hops (routers traversed) to reach a destination network. The route with the **lowest hop count** is considered optimal.
- **Routing Table:** Each router maintains a routing table, containing entries for reachable networks, their hop count, and the "next hop" router on the path.
- **Periodic Updates:** Routers periodically send updates to their neighbors, advertising their routing table entries (even if nothing has changed).
- **Triggered Updates:** Routers send updates immediately whenever they make a change to their local routing table.
- **Bellman-Ford Algorithm:** This algorithm, implemented within RIP, iteratively updates routing tables based on received updates, ensuring convergence to a loop-free routing state.
- **Failure Detection:** RIP uses a simple mechanism to detect failed links or routers. If a router doesn't receive an update from a neighbor for a certain period, it assumes the neighbor is down. Alternatively, a router could send a control message to its neighbors to check if they are still alive.

**Strengths:**

- **Simplicity:** RIP's straightforward approach makes it easy to implement and understand.
- **Rapid Convergence:** Routing updates propagate quickly, leading to fast adaptation to network changes.
- **Scalability:** Works well in smaller networks with limited complexity.

**Weaknesses:**

- **Limited Scope:** Hop count metric doesn't consider factors like bandwidth or delay, potentially leading to suboptimal paths.
- **Counting to Infinity:** Prone to routing loops in complex networks due to the hop count metric's limitations. This can be mitigated with techniques like split horizon (don't send routes to the node that you got it from).
- **Slow Convergence in Large Networks:** Frequent updates in large networks can overwhelm routers and slow down convergence.

**Implementation:**

Here is a simple implementation of Distance Vector Routing in C:

```c
#define MAX_ROUTES      128     /* maximum size of routing table */
#define MAX_TTL         120     /* time (in seconds) until route expires */

typedef struct {
    NodeAddr  Destination;    /* address of destination */
    NodeAddr  NextHop;        /* address of next hop */
    int        Cost;          /* distance metric */
    u_short   TTL;            /* time to live */
} Route;

int      numRoutes = 0;
Route    routingTable[MAX_ROUTES];


void mergeRoute (Route *new) {
    int i;
    for (i = 0; i < numRoutes; ++i) {
        if (new->Destination == routingTable[i].Destination) {
            if (new->Cost + 1 < routingTable[i].Cost)
                break; /* found a better route: */
            else if (new->NextHop == routingTable[i].NextHop)
                break; /* metric for current next-hop may have changed: */
            else
                return; /* route is uninteresting---just ignore it */
        }
    }
    if (i == numRoutes) {
        /* this is a completely new route; is there room for it? */
        if (numRoutes < MAXROUTES)
            ++numRoutes;
        else
            return; /* can`t fit this route in table so give up */
    }
    routingTable[i] = *new;
    routingTable[i].TTL = MAX_TTL; /* reset TTL */
    ++routingTable[i].Cost; /* account for hop to get to next node */
}

void updateRoutingTable (Route *newRoute, int numNewRoutes) {
    for (int i=0; i < numNewRoutes; ++i)
        mergeRoute(&newRoute[i]);
}

```

However, actual RIP operates using User Datagram Protocol (UDP) on port 520. Its messages are structured as follows:

```
RIP Message:
    Version (1 byte)
    Command (1 byte: 1 = request, 2 = response, 3 = update)
    Number of entries (2 bytes)
    RIP Entry (variable size)
    Address Family Identifier (2 bytes)
    Route Tag (2 bytes)
    IP Address (4 bytes)
    Next Hop IP Address (4 bytes)
    Metric (4 bytes: Hop Count)
```

RIP is a fairly limited and simple implementation of distance vector routing. It assigns a cost of 1 to each hop (effectively calculating the fewest hop path), and it only allows distances of up to 16 hops. Not used in most modern networks.

## Link State Routing

Each node maintains state locally, and then creates a **Link State Packet (LSP)** containing the following information:

- The ID of the node that created the LSP
- A list of directly connected neighbors of that node, with the cost of the link to each one
- A sequence number, incremented each time the LSP is updated
- A time to live for this packet, decremented at each hop

These packets are **flooded** throughout the network, meaning that each node sends the packet to all of its neighbors.

### Reliable Flooding

The sequence number and TTL of an **LSP** are used to ensure reliability and prevent loops. Adjacent nodes use ACKs and retransmissions. For non-adajcent nodes, to ensure that the most recent LSP is used, the LSP with the higher sequence number is always picked (if there is an existing LSP stored already). Once an LSP is received, the node stores it and forwards it to all of its neighbors, except the one it received it from.

New LSPs are generated both at regular intervals, and when an adjacent node goes down. Nodes send their neighbors "hello" packets to demonstrate that they are still alive. If a node doesn't receive a "hello" packet from a neighbor for a certain period, it assumes the neighbor is down and generates a new LSP.

In practice, the "regular interval" LSPs should be generated very infrequently to reduce overhead on the network. This way, the network can still converge quickly in the event of a failure, but not waste resources when nothing is changing.

When a node receives an LSP with TTL of 0, it deletes the record from its own database, and then floods the network with this packet so that all the other nodes can delete the LSP from their databases.


### Route Calculation

Based on **Dijkstra's algorithm**, but in practice uses **Forward Search**. Each node calculates the shortest path to all other nodes in the network, and then stores this information locally.

```python
M = {s}
for each n in N - {s}:
    C(n) = l(s,n)
while (N != M):
    M = M + {w} such that C(w) is the minimum for all w in (N-M)
    for each n in (N-M):
        C(n) = MIN(C(n), C(w)+l(w,n))
```

#### Forward Search

Uses a `Confirmed` and a `Tentative` list, both of which contain entries `(Destination, Cost, NextHop)`. The algorithm proceeds as follows:


1. Initialize the Confirmed list with an entry for myself; this entry has a cost of 0.
2. For the node just added to the Confirmed list in the previous step, call it node Next and select its LSP.
3. For each neighbor (Neighbor) of Next, calculate the cost (Cost) to reach this Neighbor as the sum of the cost from myself to Next and from Next to Neighbor. If Neighbor is currently on neither the Confirmed nor the Tentative list, then add (Neighbor, Cost, NextHop) to the Tentative list, where NextHop is the direction I go to reach Next.
4. If Neighbor is currently on the Tentative list, and the Cost is less than the currently listed cost for Neighbor, then replace the current entry with (Neighbor, Cost, NextHop), where NextHop is the direction I go to reach Next.
5. If the Tentative list is empty, stop. Otherwise, pick the entry from the Tentative list with the lowest cost, move it to the Confirmed list, and retu


### Open Shortest Path First (OSPF)

**OSPF** is a more modern and feature-rich link state routing protocol. It adds the following features to basic link state routing:

- Authentication: OSPF can use a password to authenticate LSPs, preventing unauthorized nodes from injecting false routing information.
- Hierarchical routing: partitions the network into **areas**, such that a given router only needs to know about the topology of its own area.
- Load balancing: can assign multiple paths to the same destination, and split traffic between them.

Of the five OSPF message types, type 1 is the “hello” message, which a router sends to its peers to notify them that it is still alive and connected as described above. The remaining types are used to request, send, and acknowledge the receipt of link-state messages.

OSPF sends Link State Advertisements (LSAs) instead of LSPs. LSAs contain information about links, including the Link ID, Link Data, and metric. The Link ID is typically the router ID of the router at the far end of the link. The metric represents the cost of the link. TOS (type of service) information allows OSPF to choose different routes based on the TOS field of IP packets.

#### Metrics

The ARPANET tested different approaches to link-cost calculation. The original metric measured queued packets on each link, but it didn't consider bandwidth or latency. A later version used delay as a measure of load, taking into account link bandwidth and latency. However, it suffered from instability under heavy load and had a large range of link values. A third approach compressed the metric range, accounted for link type, and smoothed the variation over time.

In real-world network deployments, metrics change rarely, if at all, and only under the control of a network administrator. Static metrics are the norm, with a common approach being to use a constant multiplied by (1/link_bandwidth).
