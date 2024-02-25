# Internet Control Message Protocol (ICMP)

ICMP is a network layer protocol used to report errors and exchange control messages. It is also the basis for tools like `ping` and `traceroute`.

One particularly useful ICMP message is the **ICMP Redirect**, which is used to inform a host that a better route exists for a given destination. When a host receives an ICMP Redirect, it updates its routing table to use the new route.

## Traceroute

`traceroute` works by continuously sending packets with increasing TTLs, and listening for ICMP Time Exceeded messages. When a packet reaches a router, the router decrements the TTL, and if it reaches 0, it sends an ICMP Time Exceeded message back to the source. This message contains the IP address of the router, and the time it took for the packet to reach it.

After each packet, `traceroute` prints the IP address of the router and the time it took for the packet to reach it. This is repeated until the destination is reached.

## Ping

`ping` works by sending ICMP Echo Request messages to the destination, and listening for ICMP Echo Reply messages. When the destination receives an Echo Request, it responds with an Echo Reply. This is repeated until the user stops the command.