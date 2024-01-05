# Network Components

## Parts of a network

**Application** (app, user) - The application is the program that is running on the computer. It is the program that is using the network to communicate with other computers. Examples of applications are web browsers, email clients etc.

**Host** (end system, edge device, node) - The host is the computer that is running the application. It is the computer that is using the network to communicate with other computers. Examples of hosts are desktop computers, laptops, mobile phones etc.

**Router** (switch, node, hub) - Device used to relay messages between links. Connects networks together. Examples of routers are home routers/access points, cabel/DSL modems etc.

**Link** (channel) - A connection between nodes. Examples of links are Ethernet cables, fiber optic cables, wireless connections etc.

### Types of links

- **Full-duplex** - Both nodes can send and receive at the same time. *Bidirectional*. Ex: ethernet
- **Half-duplex** - Only one node can send at a time. *Bidirectional*. Ex: WiFi
- **Simplex** - Only one node can send at a time. *Unidirectional*. Ex: 

### Wireless Links

Messages are **broadcast**. All nodes in range recieve the message. Often, in graph depictions of a network, only the logical (but not all possible) links are shown.

## Network Names by Scale

**Personal Area Network** (PAN) - A network that is available in a single person's vicinity.

*Examples*: Bluetooth, USB, FireWire etc.

**Local Area Network** (LAN) - A network that is available in a single building.

*Examples*: Ethernet, WiFi etc.

**Metropolitan Area Network** (MAN) - A network that is available in a city.

*Examples*: cable TV, DSL etc.

**Wide Area Network** (WAN) - A network that is available in a country or geographic location.

*Examples*: a large ISP, 3G/4G wireless networks etc.

**Internet** - A network that is available globally.

*Examples*: the Internet.


When you connect multiple networks, you get an **internetwork**, or **internet**. The Internet (capital I) is the internet we all know and love.

#### Switched Network

**Switched networks** forward messages from node-to-node, until they reach their destination. The two most common switched networks are **circuit-switched** (phones) and **packet-switched** (most computer networks) networks.

```txt
    +-- (Host)      --+
    |                 |
(Link)                |
    |                 |  logical
    +-- (Host)        |    link
    |                 |
(Link)                |
    |                 |
    +-- (Host)      --+
```

Packet switched networks (PSN) send data in discrete chunks, called **packets**, or messages. PSNs typically use **store-and-forward** switching, where the entire packet is received and loaded into memory, then forwarded to the next node. This is opposed to a circuit switched network, where a stream of data is sent over a maintained connection.

Networks use an _address_ to identify the destination of a packet. Packets can be sent from node to node (_unicast_), but also to all other nodes _(broadcast_), or to a subset of nodes (_multicast_).



## Network Boundaries

```
(Router) --- (Host) --- client
   |
(Link)
   |
(Router) --- (Host) --- server
```

#### What part is the network?

Everything that isn't the application level. Some people do and don't include the host, but in this course we do.

#### Can think of "the cloud" as a generic network...

```
   +-- (Host) --- client
   |
(Cloud)
   |
   +-- (Host) --- server
```

## Key Interfaces

The network is designed to be modular, and there are clearly defined interfaces betweem (1) apps and the network, and (2) the network components themselves.

This is achieved through **protocols** and **layering**.

- Each instance of a protocol communicates to its peer through the same protocol.
- Each instance of a protocol uses only the services of the layer below it.

*"Protocols are horrizontal, and layers are vertical."*

```
# define protocols X, Y,
# where Y is a lower below X


   (comm using X)
X <---------------> X  <- (peers)
^                   ^
| <- (Y service) -> |
|                   |
Y <---------------> Y  <- (peers)
    (comm using Y)
```

#### Examples of protocols:
TCP, UDP, HTTP, FTP, SMTP, POP3, IMAP, DNS, DHCP, ARP, ICMP, IP, Ethernet, WiFi, Bluetooth, USB, FireWire, DSL, cable TV, 3G/4G, etc.

#### Example of a stack
```
 (browser)
    ||
+--------+
| HTTP   |
+--------+
| TCP    |
+--------+
| IP     |
+--------+
| 802.11 |
+--------+
    ||
    ++==>
```


### Encapsulation

Protocol layering is built upon literal encapsulation of data. Each lower level protocol wraps the higher level protocol's data in its own format with extra information. Similar to putting a letter in an envelope, and then sending it to someone in the mail.

The message "on the wire" for the above stack might look like...

```
                    +------+
                    | HTTP |
                    +------+
              +-----+------+
              | TCP | HTTP |
              +-----+------+
         +----+-----+------+
         | IP | TCP | HTTP |
         +----+-----+------+
+--------+----+-----+------+
| 802.11 | IP | TCP | HTTP |
+--------+----+-----+------+
```

When two nodes communicate, the sender builds up these layers until the data is ready to be transported over the physical medium. Then, once the data is recieved, the reciever peels back the layers until it reaches the application layer.

It is more involved that this diagram in practice. Trailers and headers of each request segment are needed, and the content is often encrypted or compressed. Furthermore, segmentation and reassembly happens when nodes communicate as well.

### Demultiplexing

When a message is recieved, it needs to be passed through exactly the protocols that use it. This is done using **demultiplexing keys** found in the headers of each protocol. Ex: IP protocol field, TCP port number, etc.

### Advantages of Layering

- **Modularity** - Each layer can be changed without affecting the other layers, so long as the interface remains the same.
- **Abstraction** - Each layer can be thought of as a black box. Information hiding can be used to connect different systems that rely on different protocols under the hood.
- **Standardization** - Each layer can be standardized, and then implemented by many different vendors.

### Disadvantages of Layering

- **Inefficiency** - Each layer adds overhead to the message. This is especially true for small messages, since the amount of overhead relative to the message size is large.
- **Hides information** - Each layer hides information from the layer above it. This can make debugging difficult, and limits some applications of the network (like an app that wants to know the network latency, or a network that needs to know about app priorities like QoS).

## OSI Layers

### Application Layer

Services that are used with end user applications. Examples: HTTP, FTP, SMTP, POP3, IMAP, DNS, DHCP, etc.

### Presentation Layer

Formats the data so it can be understood by the application layer. Also handles encryption and compression. Examples: JPEG, MPEG, ASCII, etc.

### Session Layer

Manages the connection between two nodes. Examples: NetBIOS, PPTP, etc.

### Transport Layer

Responsible for the transport protocol and error handling. Examples: TCP, UDP, etc.

### Network Layer

Responsible for routing and addressing. Reads the IP address from a packet. Examples: Routers, Layer 3 switches, etc.

### Data Link Layer

Responsible for the physical addressing. Reads the MAC address from a data packet/frame. Examples: Switches, bridges, etc.

### Physical Layer

Transfer data on a physical medium. Examples: Hubs, NICS, Cables, etc.


## The actual Internet Protocol Stack

```
+-------------+---------------+
| Application | SMTP, HTTP,   |
|             | RTP, DNS      |
+-------------+---------------+
| Transport   | TCP, UDP      |
+-------------+---------------+
| Internet    | IP            |
+-------------+---------------+
| Link        | Ethernet, DSL,|
|             | 3G/4G, WiFi,  |
+-------------+---------------+
```

## Course Reference Model

**Application** - Programs that use network services
**Transport** - Provides end-to-end data delivery
**Network** - Provides data delivery across multiple networks
**Link** - Sends frames over one or more links
**Physical** - Sends bits using physical signals
