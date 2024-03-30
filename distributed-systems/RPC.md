# Look Into

- Remote Direct Memory Access (RDMA)
- Network File System (NFS)

# Remote Procedure Call (RPC)

A request from a client to execute a function on a server/different machine.
- To the client, looks like a local function call.
- To the server, looks like an implementation of a function call.

Google handles $10^{10}$ RPCs per second.

## Local Procedure Call

- Caller invokes function by name with args.
    - Pass args in register, push others onto stack.
    - Push return program counter (%rip) onto stack.
    - Jump to first instruction (entry point) of callee.
- Callee executes function, returns to caller.
    - Reads params from registers/stack.
    - Computes the function, possibly updating state.
    - Jump back to next instruction after call.

The compiler defines the protocol for the call above.

## Remote Procedure Call

- On client, implements a function that looks like a local call.
    - Parameters are *marshalled* into a message (arbitrary types)
    - Message is sent to server (possibly in multiple packets).
    - Client waits for response.
- On server, implements the function.
    - *Unmarshals* (parses) the message.
    - Computes the function, possibly updating state.
    - *Marshals* the return value into a message (possibly into multiple packets).
    - Sends the message back to the client.

Client/server implementation is usually auto-generated from procedure spec, e.g. Google's Protocol Buffers/Protobuf.

## RPC vs. Local Procedure Call

### Binding
- Client needs a connection to the server.
- Server must implement the required function
- Server needs to be running a compatible version/implementation of the function.

### Service Discovery Service
- A process that keeps track of all available services, including versions, schemas, locations, etc.

### Interface Description Language (IDL, e.g. Protobuf)
**Serialization is important!**

- Generate client/server serialization/deserialization stubs automatically based on the IDL.
    - Procedue args can be values or pointers, which need to be assembled into a single linear message in a transportable format (not always just a string, e.g. Protobuf using binary format).

### Failures

- Packets can be lost, reordered, or duplicated.
- Client/server can crash at any time (before, during, or after the call).
- Server/network can be slow, and client can time out.

Some of the network issues can be mitigated by TCP, but sockets can fail and messages aren't always transmitted over TCP anyways.


## Fault Model

- **Asynchronous fail stop nodes**
    - Computer may be arbitrarily slow while still working.
    - Nodes should always fail by stopping, before transmitting garbage data/forgetting state. This is a strong assumption. For non-fail-stop/arbitrarily behaving nodes, see *Byzantine Fault Tolerance*.
- **Network model**
    - Messages can be lost, delayed, reordered, or duplicated. Messages can be arbitrarily delayed while the network still works correctly.
    - Messages won't be corrupted (bit flips). This is another strong assumption. See error detection and correction for working without this assumption.
    - Network may partition some nodes from eachother.
        - Possible for nodes to be in isolated groups without a connection between them.
    - Network is (1) commutative and (2) transitive.
        - (1) If A can talk to B, B can talk to A.
        - (2) If A can talk to B and B can talk to C, then A can talk to C.
- Clients only make one RPC request at a time, a very strong assumption.

## Naive RPC

- **Nodes**
    - Any number of stateless clients and servers.
    - Servers perform some computation when they recieve a message, and then reply.
- **Messages**
    - Client request, server response
    - Client reqyest contains IP addr of client and server, name of procedure, arguments.
    - Server response contains IP addr of client and server, and results of the procedure.

## Client timeout and retry
If a request or reply message is dropped, the client will wait forever for the response. This can be fixed with client timer/retransmission, where the client sends the request again if it doesn't get a response in a certain amount of time. This leads to duplication and reordering of messages at the server.

We can handle this with a unique request ID. Include a message ID in each request/reply. When the client retransmits, it uses the same message ID. The server can then ignore duplicate requests.

### RPC Semantics

- **At least once**
    - Client resends on timeout, server executes every copy of requests that arrive
    - If client gets a response, it knows the server executed the request at least once. Otherwise, it doesn't know if the server executed the request(s) or not.
- **At most once**
    - Execute only the first copy that arrives at the server.
    - If client gets a reply, it knows the server executed the request exactly once. Otherwise, it doesn't know if the server executed the request or not (but it knows it didn't execute it more than once).
- **Exactly once**
    - Execute the request exactly once.
    - Requires a unique request ID, and the server to remember the request ID and the result of the request.

#### At least once

Client should do a finite number of retries, eventually giving up and returning an error to the caller.

This only works if the server is **idempotent**, meaning it has the same effect if it's executed multiple times. All read-only operations are idempotent, but not all write operations are. For example, icrementing a counter is not idempotent, but setting the counter to a value is.

Does TCP handle this? Not really despite being reliable. Most RPCs are sent over TCP, and it guarantees in-order delivery with retransmission and duplicate detection. However, it doesn't guarantee exactly-once semantics. If the server crashes after processing the request but before sending the response, the client will retransmit the request, and the server will execute it again.

**End to end principle**: Functionality should be implemented where it can be completely handled, rather than partially handled at each layer. This decreases the chance of partially completed work due to unrelated failures.


Examples:
| Example | Explanation |
|---|---|
| DNS lookup | Queries are read-only, so it's idempotent |
| MapReduce | The Map phase is idempotent since it is a pure function |
| NFS | If the client maintains offset, reading/writing a block is idempotent |


Importantly, in situations with multiple clients, operations like `Put(k, v)` are not idempotent, since the value of `k` can change between the time the client reads the value and the time it writes the value.

## Two Generals Problem

Just a thought experiment to emphasize the difficulty of message passing in a distributed system. Two generals are trying to coordinate an attack on a city. They are separated by a valley, and can only communicate by messenger. The messenger can be captured by the city, and the generals don't know if the message was delivered. The generals need to agree on a time to attack, but they can't be sure the message was delivered. They can only attack if they both agree on the time.

The problem boils down to the fact that at any point in time, if we sent a message, we don't know if it was delivered. Regardless of how many round trips you make to confirm, the last message sent could always have been dropped. This is a fundamental and central problem in distributed systems.



