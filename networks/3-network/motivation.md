# Motivation behind the Network Layer

We can already build networks using the link layer using packet forwarding, but this doesn't scale well. The network layer allows you to connect multiple networks together, allowing for transparent communication between different link layer technologies.

## Shortcomings of the Link Layer

- **No global addressing**: Link layer addresses are only meaningful on the local network. We need a way to address hosts on different networks.
- **Doesn't scale well**: It is infeasable to maintain a routing table for every host on the internet locally.
- **Only one technology**: Link layer technologies are not interoperable. We need a way to connect different link layer technologies together.
- **Limited traffic control**: Link layer technologies are not designed to handle congestion or route around failures. Should also be able to control the bandwidth used by different applications.


## Network Layer Approach

- **Scaling**: Hierarchical addressing in the form of prefixes.
- **Heterogeneity**: Uses IP as a common protocol to connect different link layer technologies.
- **Bandwidth control**: Uses congestion control and lowest-cost routing to control traffic. Also allows for quality of service (QoS) to be implemented.

## Routing vs. Forwarding

- **Routing** is the process of deciding which path to send traffic. Happens on a global scale.
- **Forwarding** is the process of actually sending the packet from one node to another.

## Topics
- Network Service Model
    - Datagrams (packets)
    - Virtual Circuits
- IP
    - Internetworking
    - Forwarding (Longest Prefix Match)
    - Helpers: ARP and DHCP
    - Fragmentation and MTU discovery
    - Errors: ICMP
    - IPv6, scaling IP to the world
    - NAT and "middleboxes"
- Routing Algorithms
