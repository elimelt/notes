---
title: Address Resolution Protocol (ARP)
category: Networks
tags: address resolution protocol, arp, discovery protocol, arp table, arp request, arp reply
description: Covers the Address Resolution Protocol (ARP), a discovery protocol used to map network layer addresses (such as IP addresses) to data link layer addresses (such as MAC addresses). Describes the ARP table, which stores the mapping between IP and MAC addresses, and the ARP request and reply process used to dynamically update this table. Discusses the key steps involved in the ARP request and reply mechanism, which allows hosts to determine the MAC address corresponding to a given IP address on the local network.
---

# Address Resolution Protocol (ARP)

**ARP** is used to map IP addresses to MAC addresses. It sits directly on top of the link layer, without using any servers or routers. ARP is just one example of a **discovery protocol**, which are used to find devices on a network. Other examples include **Zeroconf** and **Bonjour**. Discovery protocols more often than not use broadcast messages to find devices on the network.




### ARP Table

ARP maintains a table of IP addresses and their corresponding MAC addresses. This is typically stored in a given host's memory. You can see your ARP table with the `arp` command.

```bash
arp -a
```

### ARP Request

When a device wants to send a packet to another device on the same network, it first checks its ARP table to see if it knows the MAC address of the destination IP address. If it doesn't, it sends an ARP request to the broadcast MAC address `FF:FF:FF:FF:FF:FF` asking for the MAC address of the destination IP address.

```plaintext
ARP Request Packet:

  ....Link layer.....
+----------+----------+----------+----------+----------+
| SRC MAC  | DST MAC  | SRC IP   | DST IP   | Payload  |
+----------+----------+----------+----------+----------+
 from NIC    From ARP   From DHCP
```

### ARP Reply

Although the ARP request is broadcast, only nodes that already have an entry, or the destination IP address itself, will act on the request (ie refresh tables/learn MAC address). Other nodes will ignore the request. The destination IP address will then send an ARP reply to the source IP address with its MAC address.

