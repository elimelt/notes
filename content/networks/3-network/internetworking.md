---
title: Internetworking
category: Networks
tags: internetworking, networks, ip addressing
description: Covers the implementation of internetworking, including how different network types can be connected, and the fundamentals of IP addressing. Discusses the concepts of IPv4 addressing, IP prefixes, and IP datagram forwarding using the longest prefix match algorithm.
---

# Internetworking

## How netorks may differ

- Serive model (datagrams vs virtual circuits)
- Addressing
- QOS (priorities)
- Packet size
- Security (encryption, authentication)

Internetworking hides the difference with a common prorocol (IP) and a common addressing scheme (IP addresses).

### Connecting Datagram and Virtual Circuit Networks

Need to map a destination address to a VC and visa versa. In order to accomplish this, might have to set up a VC between two routers, and then use datagrams to send packets between the routers.

```plaintext
+--------+   802.11   +--------+ <---- MPLS ----> +--------+  Ethernet  +--------+
|  host  |------------| Router |                  | Router |------------|  host  |
+--------+            +--------+ <--------------> +--------+            +--------+
 source                            VC network                           destination
```

## IP Addressing

IP is the lowest common denominator of the internet. It allows networks that support entirely different services to communicate. Asks very little of the underlying network, and provides very little in return.

- IPv4 uses 32-bit addresses written in "dotted quad" notation (Four 8-bit numbers separated by dots).
  - Ex: `255.255.255.0`
- IPv6 uses 128-bit addresses written in hexadecimal notation.
  - Ex: `2001:0db8:85a3:0000:0000:8a2e:0370:7334`

### IPv4

```plaintext

<--------------------------------------- 32 bits --------------------------------------->

+---------------------+---------------------+---------------------+---------------------+
| Version |    IHL    |   Dif. Services     |         Total Length (bytes)              |
+---------------------+---------------------+---------------------+---------------------+
|              Identification               |    | DF | MF |  Fragment Offset (13 bits) |
+---------------------+---------------------+---------------------+---------------------+
|  Time to Live (TTL) | Protocol (TCP, UDP) |            Header Checksum                |
+---------------------+---------------------+---------------------+---------------------+
|                               Source IP Address (32 bits)                             |
+---------------------+---------------------+---------------------+---------------------+
|                            Destination IP Address (32 bits)                           |
+---------------------+---------------------+---------------------+---------------------+
|                                  Options (0 or more words)                            |
|                                                                                       |
|                                        ....                                           |
+---------------------+---------------------+---------------------+---------------------+
|                                       Payload                                         |
|                                                                                       |
|                                        ....                                           |
+---------------------+---------------------+---------------------+---------------------+

```

### IP Prefixes

- Addresses allocated in blocks called "prefixes".
  - Addresses in an L-bit prefix have the first L bits in common.
  - There are $2^{32-L}$ addresses in an L-bit prefix.
- Written in "addr/prefix" notation.
  - Ex: `128.13.0.0/16` is a 16-bit prefix and contains $2^{32-16} = 65536$ addresses.
- Originally, IP addresses were allocated in fixed size blocks to a designated class. Still are, but class is now ignored in favor of CIDR (Classless Inter-Domain Routing).
  - Class A: $2^{24}$ addresses
  - Class B: $2^{16}$ addresses
  - Class C: $2^{8}$ addresses

#### Example:

`128.13.0.0/16`

```plaintext
        Network                Host
+----------+----------+----------+----------+
| 10000000 | 00001101 |   ....   |   ....   |
+----------+----------+----------+----------+
```

## IP Datagram Forwarding

When a host wants to send a packet to another host, it first checks if the destination IP address is on the same network (matching subnet). If it is, it can send the packet directly over the link layer (using ARP to get resolve IP address to MAC address). Otherwise, it sends the packet to the _default gateway_, or **router**.

The router then forwards the packet to its **next hop** based on the destination IP and the router's routing table.

```python
if (NetworkNum of destination = NetworkNum of one of my interfaces):
    deliver packet to destination over that interface (using ARP)
else:
    if (NetworkNum of destination is in my forwarding table):
        deliver packet to NextHop router
    else:
        deliver packet to default router
```

#### Longest Prefix Match

- For each packet, find the longest prefix that contains the destination address, ie. the most specific match.
- forward the packet to the next hop for that prefix.

```python
for each entry in the forwarding table:
    if (NetworkNum of destination & Mask) == (NetworkNum of entry & Mask):
        deliver packet to NextHop router
```

- [Internetworking](#internetworking)
  - [How netorks may differ](#how-netorks-may-differ)
    - [Connecting Datagram and Virtual Circuit Networks](#connecting-datagram-and-virtual-circuit-networks)
  - [IP Addressing](#ip-addressing)
    - [IPv4](#ipv4)
    - [IP Prefixes](#ip-prefixes)
      - [Example:](#example:)
  - [IP Datagram Forwarding](#ip-datagram-forwarding)
      - [Longest Prefix Match](#longest-prefix-match)

