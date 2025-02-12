---
title: Socket Reference
category: Networks
tags: socket, networking, system programming, C, Python
description: This document covers the implementation of sockets, a fundamental networking concept in system programming. It provides a reference for creating, configuring, and using sockets in both client and server applications, including examples in C and Python. Key topics include TCP and UDP socket types, binding sockets to addresses, listening for connections, accepting connections, sending and receiving data, and closing sockets. The document serves as a comprehensive guide for developers working on network-based applications.
---

# Socket Reference

## Creating a Socket

```c
#include <sys/types.h>
#include <sys/socket.h>


/**
 * @brief Creates a socket.
 *
 * @param domain specifies the protocol family to use.
 *   ex: AF_INET, AF_INET6, AF_UNIX, etc.
 * @param type The type of the socket.
 *   ex: SOCK_STREAM, SOCK_DGRAM, SOCK_RAW, etc.
 * @param protocol The protocol of the socket.
 *   ex: (IPPROTO_TCP, IPPROTO_UDP, UNSPEC, etc.)
 *
 * @return The file descriptor of the socket.
*/
int socket(int domain, int type, int protocol);
```

```python
import socket
# TCP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
```

## Server Side

### Binding a Socket

```c
#include <sys/types.h>
#include <sys/socket.h>

/**
 *
 * @brief Assigns the address specified by @p address to the socket
 *   @p socket.
 *
 * @param socket The socket fd to bind.
 * @param address The sockaddr struct containing the address and
 *   port to bind to. Usually retrieved from a call to getaddrinfo().
 * @param addr_len The length of the sockaddr struct.
 *
 * @return 0 on success, -1 on failure.
*/
int bind(int socket, struct sockaddr *address, int addr_len);
```

```python
# ...
port = 80

# Bind the socket to an address
serversock.bind((socket.gethostname(), port))
```

### Listening on a Socket

```c
#include <sys/types.h>
#include <sys/socket.h>

/**
 * @brief Marks the socket @p socket as a passive socket, that is,
 *   as a socket that will be used to accept incoming connection
 *   requests using accept().
 *
 * @param socket The socket to listen on.
 * @param backlog The maximum length of the queue of pending
 *   connections.
 *
 * @return 0 on success, -1 on failure.
*/
int listen(int socket, int backlog);
```

```python
# ...

backlog = 5

# Listen for connections
serversock.listen(backlog)
```

### Accepting a Connection

```c
#include <sys/types.h>
#include <sys/socket.h>

/**
 * @brief Accepts a connection on the socket @p socket.
 *
 * @param socket The socket to accept a connection on.
 * @param address A pointer to a sockaddr struct that will be
 *   filled with the address of the peer socket.
 * @param addr_len A pointer to an int that will be filled with
 *   the length of the sockaddr struct.
 *
 * @return The file descriptor of the new socket, or -1 on failure.
*/
int accept(int socket, struct sockaddr *address, int *addr_len);
```

```python
# ...

# Accept a connection
clientsock, addr = serversock.accept()
```

## Client Side

### Connecting to a Server

```c
#include <sys/types.h>
#include <sys/socket.h>

/**
 * @brief Connects the socket @p socket to the address specified
 *   by @p address.
 *
 * @param socket The socket to connect.
 * @param address The sockaddr struct containing the address and
 *   port to connect to. Usually retrieved from a call to getaddrinfo().
 * @param addr_len The length of the sockaddr struct.
 *
 * @return 0 on success, -1 on failure.
*/
int connect(int socket, struct sockaddr *address, int addr_len);
```

```python
import socket

# create a socket
clientsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect to a server
clientsock.connect(('http://elimelt.com', port))
```

## Sending and Receiving Data

```c
#include <sys/types.h>
#include <sys/socket.h>

/**
 * @brief Sends @p len bytes from @p buf on the socket @p socket.
 *
 * @param socket The socket to send data on.
 * @param buf The buffer containing the data to send.
 * @param len The length of the data to send.
 * @param flags Flags to modify the behavior of the send.
 *
 * @return The number of bytes sent, or -1 on failure.
*/
ssize_t send(int socket, const void *buf, size_t len, int flags);

/**
 * @brief Receives data from the socket @p socket and stores it
 *   in @p buf.
 *
 * @param socket The socket to receive data on.
 * @param buf The buffer to store the received data in.
 * @param len The length of the buffer.
 * @param flags Flags to modify the behavior of the receive.
 *
 * @return The number of bytes received, or -1 on failure.
*/
ssize_t recv(int socket, void *buf, size_t len, int flags);
```

```python
# ...

# Send data
clientsock.send('Hello, world!')

# Receive data
data = clientsock.recv(1024)
```

## Closing a Socket

```c
#include <sys/types.h>
#include <sys/socket.h>

/**
 * @brief Closes the socket @p socket.
 *
 * @param socket The socket to close.
 *
 * @return 0 on success, -1 on failure.
*/
int close(int socket);
```

```python
# ...

# Close the socket
clientsock.close()
```

## Simple Client

```c
// from book.systemsapproach.org

#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#define SERVER_PORT 5432
#define MAX_LINE 256

int
main(int argc, char * argv[])
{
  FILE *fp;
  struct hostent *hp;
  struct sockaddr_in sin;
  char *host;
  char buf[MAX_LINE];
  int s;
  int len;

  if (argc==2) {
    host = argv[1];
  }
  else {
    fprintf(stderr, "usage: simplex-talk host\n");
    exit(1);
  }

  /* translate host name into peer's IP address */
  hp = gethostbyname(host);
  if (!hp) {
    fprintf(stderr, "simplex-talk: unknown host: %s\n", host);
    exit(1);
  }

  /* build address data structure */
  bzero((char *)&sin, sizeof(sin));
  sin.sin_family = AF_INET;
  bcopy(hp->h_addr, (char *)&sin.sin_addr, hp->h_length);
  sin.sin_port = htons(SERVER_PORT);

  /* active open */
  if ((s = socket(PF_INET, SOCK_STREAM, 0)) < 0) {
    perror("simplex-talk: socket");
    exit(1);
  }
  if (connect(s, (struct sockaddr *)&sin, sizeof(sin)) < 0)
  {
    perror("simplex-talk: connect");
    close(s);
    exit(1);
  }
  /* main loop: get and send lines of text */
  while (fgets(buf, sizeof(buf), stdin)) {
    buf[MAX_LINE-1] = '\0';
    len = strlen(buf) + 1;
    send(s, buf, len, 0);
  }
}
```

```python
import socket
import sys

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((sys.argv[1], 5432))

while 1:
    line = sys.stdin.readline()
    if not line:
        break
    s.send(line)
s.close()
```

## Simple Server

```c
// from book.systemsapproach.org
#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#define SERVER_PORT  5432
#define MAX_PENDING  5
#define MAX_LINE     256

int
main()
{
  struct sockaddr_in sin;
  char buf[MAX_LINE];
  int buf_len, addr_len;
  int s, new_s;

  /* build address data structure */
  bzero((char *)&sin, sizeof(sin));
  sin.sin_family = AF_INET;
  sin.sin_addr.s_addr = INADDR_ANY;
  sin.sin_port = htons(SERVER_PORT);

  /* setup passive open */
  if ((s = socket(PF_INET, SOCK_STREAM, 0)) < 0) {
    perror("simplex-talk: socket");
    exit(1);
  }
  if ((bind(s, (struct sockaddr *)&sin, sizeof(sin))) < 0) {
    perror("simplex-talk: bind");
    exit(1);
  }
  listen(s, MAX_PENDING);

 /* wait for connection, then receive and print text */
  while(1) {
    if ((new_s = accept(s, (struct sockaddr *)&sin, &addr_len)) < 0) {
      perror("simplex-talk: accept");
      exit(1);
    }
    while (buf_len = recv(new_s, buf, sizeof(buf), 0))
      fputs(buf, stdout);
    close(new_s);
  }
}
```

```python
import socket
import sys

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((socket.gethostname(), 5432))
s.listen(5)

while True:
    clientsock, addr = s.accept()
    while True:
        data = clientsock.recv(1024)
        if not data:
            break
        print(data)
    clientsock.close()
```