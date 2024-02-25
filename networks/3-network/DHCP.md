# Dynamic Host Configuration Protocol (DHCP)

**DHCP** is the protocol used to assign IP addresses within a given network. Unlike MAC addresses, IPs are not hard-coded or unique to a device, and can be reassigned to different devices over time. This gives the network much needed flexibility, but also requires a way to manage the assignment of IPs. This is where DHCP comes in.

DHCP sits on top of the **UDP** protocol, and uses **port 67** for the server, and **port 68** for the client.

## DHCP Server

The **DHCP Server** is a device that assigns IP addresses to devices on the network. It is typically a router or a server, and is responsible for managing a pool of IP addresses. When a device connects to the network, it broadcasts a **DHCP Discover** message to the network (sending to addr of all 1s). The DHCP server listens for these messages, and responds with a **DHCP Offer** message. This message contains an IP address that the server is willing to assign to the device. The device then sends a **DHCP Request** message to the server, and the server responds with a **DHCP Ack** message, confirming the assignment of the IP address.

The protocol also supports replicated DHCP servers, which can be used to provide fault tolerance. If a DHCP server fails, the client can simply request an IP from another server.

## DHCP Client

**DHCP** clients are pretty ubiquitous, and are built into most devices that connect to a network. To renew an IP address, the client sends a **DHCP Request** message to the server, and the server responds with a **DHCP Ack** message, confirming the renewal.

## DHCP Relay

Not all networks have a running DHCP server. In this case, a **DHCP Relay** can be used to forward DHCP messages to a server on another network. The relay listens for **DHCP Discover** messages, and forwards them to the server. The server then responds with a **DHCP Offer** message, and the relay forwards it to the client.