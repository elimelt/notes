# Networking Services

## Store-and-Forward Packet Switching

- Routers receive a complete packet, storing it temporarily if necessary, before forwarding it to the next hop.
- Use statistical multiplexing to share link bandwidth over time.
- Switching element has internal buffering for contention. Buffer is typically a FIFO queue, where if full, packets are dropped.

## Datagrams vs. Virtual Circuits

**Datagrams** are a connectionless service that sends packets from one host to another. Like postal letters. Each packet is independent and can take a different route to the destination. This is the most common service on the internet. Each packet contains destination address. Routers use this to forward packets, maybe on different paths for each subsequent message. Each router has a forwarding table keyed by destination address. The table contains the next hop for each destination, but the entries change over time as the network topology changes.

**Virtual Circuits** are a connection-oriented service that sets up a path between the source and destination before sending packets. Like a phone call. Each packet follows the same path and is identified by a connection ID. This is less common on the internet, but is used in technologies like ATM and Frame Relay.

| Issue | Datagram | Virtual Circuit |
|-------|----------|-----------------|
| Setup phase | Not needed | Required |
| Router state | Per destination | Per connection |
| Addresses | Packet carries full destination address | Short connection ID to label|
| Routing | Per packet | Per circuit |
| Failures | Easy to mask | Hard to mask |
| QoS | Hard to provide | Easier to provide |

