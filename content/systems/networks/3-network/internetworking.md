---
title: Internetworking
aliases:
  - networks/3-network/internetworking
category: Networks
tags:
  - networks
  - internetworking
  - ip-addressing
  - forwarding
  - arp
  - icmp
  - ttl
date: 2024-02-16
updated: 2026-07-30
status: evergreen
description: How IP connects networks that differ in service model, addressing, and packet size, covering IPv4 addressing, prefixes and CIDR, and datagram forwarding with longest prefix match.
sources:
  - title: "RFC 791: Internet Protocol"
    url: https://datatracker.ietf.org/doc/html/rfc791
    type: rfc
  - title: "RFC 4632: Classless Inter-domain Routing (CIDR)"
    url: https://datatracker.ietf.org/doc/html/rfc4632
    type: rfc
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Explain how networks built on different technologies get connected into one internet. Covers what networks can differ on, how IP addressing and prefixes work, and how a router forwards an IP datagram.

## How networks may differ

- Service model (datagrams vs virtual circuits, see [[systems/networks/3-network/networking-services|networking services]])
- Addressing
- QoS (priorities)
- Packet size
- Security (encryption, authentication)

Internetworking hides these differences behind a common protocol (IP) and a common addressing scheme (IP addresses).

### Connecting datagram and virtual circuit networks

Sending a datagram across a virtual circuit network means mapping a destination address to a VC and back again. One way to do it is to set up a VC between two routers and carry datagrams over that circuit:

```plaintext
+--------+   802.11   +--------+ <---- MPLS ----> +--------+  Ethernet  +--------+
|  host  |------------| Router |                  | Router |------------|  host  |
+--------+            +--------+ <--------------> +--------+            +--------+
 source                            VC network                           destination
```

## IP addressing

IP is the lowest common denominator of the internet. It lets networks that support entirely different services communicate, by asking very little of the underlying network and providing very little in return.

- IPv4 uses 32-bit addresses written in "dotted quad" notation, four 8-bit numbers separated by dots.
  - Ex: `192.168.1.1`
- IPv6 uses 128-bit addresses written in hexadecimal notation.
  - Ex: `2001:0db8:85a3:0000:0000:8a2e:0370:7334`

### IPv4 header

The header format below is from [RFC 791](https://datatracker.ietf.org/doc/html/rfc791). The TTL and protocol fields matter later: TTL expiry is what [[systems/networks/3-network/ICMP|ICMP]] Time Exceeded messages report, and the protocol field says whether the payload is TCP, UDP, or something else.

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
|                                        ....                                           |
+---------------------+---------------------+---------------------+---------------------+
|                                       Payload                                         |
|                                        ....                                           |
+---------------------+---------------------+---------------------+---------------------+
```

### IP prefixes

Addresses are allocated in blocks called prefixes. Addresses in an $L$-bit prefix share their first $L$ bits, which leaves $2^{32-L}$ addresses in the block. Prefixes are written in "addr/prefix" notation. For example, `128.13.0.0/16` is a 16-bit prefix containing $2^{32-16} = 65536$ addresses.

Originally IP addresses came in fixed-size class blocks:

- Class A: $2^{24}$ addresses
- Class B: $2^{16}$ addresses
- Class C: $2^{8}$ addresses

Allocation still works in blocks, but class boundaries are ignored in favor of CIDR, Classless Inter-Domain Routing ([RFC 4632](https://datatracker.ietf.org/doc/html/rfc4632)), which allows prefixes of any length.

For `128.13.0.0/16`, the first 16 bits name the network and the rest name the host:

```plaintext
        Network                Host
+----------+----------+----------+----------+
| 10000000 | 00001101 |   ....   |   ....   |
+----------+----------+----------+----------+
```

## IP datagram forwarding

When a host wants to send a packet, it first checks whether the destination IP is on the same network by matching the subnet. If it is, the host sends the packet directly over the link layer, using [[systems/networks/3-network/ARP|ARP]] to resolve the IP address to a MAC address. Otherwise it hands the packet to its default gateway, a router.

The router then forwards the packet to its next hop based on the destination IP and the router's forwarding table. In pseudocode:

```text
if NetworkNum of destination == NetworkNum of one of my interfaces:
    deliver packet to destination over that interface (using ARP)
else if NetworkNum of destination is in my forwarding table:
    deliver packet to the NextHop router for that entry
else:
    deliver packet to default router
```

### Longest prefix match

With CIDR, several forwarding table entries can match the same destination. A `/16` and a more specific `/24` inside it can both contain the address. The rule is to pick the longest matching prefix, meaning the most specific one, and forward to its next hop:

```text
best = default route
for each entry in the forwarding table:
    if (destination & entry.Mask) == entry.NetworkNum:
        if entry.Mask is longer than best.Mask:
            best = entry
deliver packet to best.NextHop
```

## Related notes

- [[systems/networks/3-network/routing|routing]]
- [[systems/networks/3-network/ARP|ARP]]
- [[systems/networks/3-network/ICMP|ICMP]]
- [[systems/networks/3-network/networking-services|networking services]]
