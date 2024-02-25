# Transmission Control Protocol (TCP)

## Connection Establishment

Both sender and receiver must be ready to transfer data, and they need to agree on parameters like max segment size.


### Three-Way Handshake

Opens up connection between client and server. Each side probes the other with a fresh **Initial Sequence Number (ISN)**. Sends on a SYNchronize segment, and echos on ACKnowledge segment. This gives us robustness, but requires extra overhead.

- Client sends SYN(x)
- Server replies with SYN(y)ACK(x+1)
- Client replies with ACK(y+1)
- SYNs are retransmitted if lost


### Connection Release

TCP requires a two-way close. Client and server both finish sending all their data and send a FIN segment. Each FIN closes one direction of the connection.

- Active sends FIN(x), passive ACKs
- Passive sends FIN(y), active ACKs
- FINs are retransmitted if lost

### TIME_WAIT State

Wait a long time afer sending all segments before actually closing (2 x max segment lifetime). This is because the final ACK may be lost, and we need to make sure the other side has received it. Otherwise it might interfere with a new connection.