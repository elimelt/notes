---
title: Encoding, Evolution, and Data Flow in Distributed Systems
category: Distributed Systems
tags: data serialization, schema evolution, compatibility, message passing, encoding formats
description: This document explores various aspects of data encoding and evolution in distributed systems. It covers different serialization formats, schema evolution strategies, and modes of data flow including databases, services, and message passing systems, with a focus on maintaining compatibility as systems change over time.
---

# Chapter 4

## Encoding and Evolution

**evolvability**: the ability to evolve as requirements change.

**schema-on-read**: schema isn't enforced when data is written, only when it is read. it can change over time.

**schema-on-write**: schema is enforced when data is written. it is usually enforced by a database schema.

**backward compatibility**: new code can read data that was written by old code, meaning new code understands old fields.

**forward compatibility**: old code can read data that was written by new code, meaning old code ignores new fields.

### Formats for Encoding Data

Programs typically work with at least two different representations of data:

- **in-memory data structures** (objects, arrays, hash maps, etc.)
- **serialized** (encoded) **bytes** (often stored on disk or sent over the network).

**serialization**: the process of translating data structures or object state into a format that can be stored (for example, in a file or memory buffer) or transmitted (for example, across a network connection link) and reconstructed later (possibly in a different computer environment). Also called encoding/marshaling.

**deserialization**: the reverse process of serialization, which is to extract data structures from a series of bytes. Also called decoding/unmarshaling.

Many built in serialization formats that are included with languages are not performant or space efficient (Java's built in serialization, Python's pickle, etc.). They are also not compatible with other languages. Generally a bad idea to use these formats for long term storage or communication between services.

**JSON** and **XML** are popular serialization formats that are language independent and human readable. Both have good support for `utf-8` strings, but not for binary strings. Workarounds with `base64` encoding work, but increase data size by 33%.

**CSV** is also popular, albeit less powerful. It is not self describing, so it is not good for data with multiple types, and instead relies on application code to interpret the data.

**Binary encoding** is essentially a custom encoding format, although binary implementations for other encodings exist. They are usually more compact than JSON, XML, and CSV, and are also usually faster to encode and decode. Probably a bad idea for inter-org communication, but acceptable for internal communication.

**Protocol Buffers** (protobuf) is a popular binary encoding format. It is a schema language that defines data types and a binary encoding format. It is not self describing, and requires a schema definition to be decoded. Most languages have protobuf libraries that generate classes from a schema definition in order to encode/decode data. Uses field tags to identify fields in the binary encoding, which are assigned to each field in the schema definition. This allows fields to be reordered without breaking compatibility. Doesn't have array/list types, instead uses repeated fields.

**Thrift** similar to protobuf, uses IDL to define data types and a binary encoding format. It is more mature than protobuf, but has a more complex schema language. Also has many code gen tools for different languages. Has 3 different protocols: dense protocol (C++ only), binary protocol (all languages), and compact protocol (all languages). In binary protocol, field names are not included, instead **field tags** are used, which are assigned to each field in the schema definition. Supports array/list types, and allows nested lists.

**Avro** Another binary encoding that was made as an alternative to protobuf and thrift for Hadoop. Uses a schema to specify encoding. Has two schema langs: IDL, for human editing, and one similar to JSON, for machine reading. Doesn't use tag numbers or any identifying field info; just lengths and data values. Uses variable length integers to encode lengths. Uses writer/reader schema setup.

### What makes protobuf, thrift and avro good?

- **Compact structure**: data is encoded as a sequence of fields, each of which contains a key (field tag) and a value. The key indicates the field's name and data type. Field tags are used to identify fields from the schema, and variable length integers are used for the field tags.
- **Schema evolution**: new fields can be added to the schema, but must have a new tag number and either be optional or have a default value. Old code can read data with new fields (ignores new fields), and new code can read data with old fields. Fields can be removed, but only if the field tag is not reused. Fields can be renamed, but only if the field tag is not reused. Fields can be reordered without breaking compatibility.

### Writer Reader Schema Setup

- **Avro** allows two different schemas to coexist so long as they are compatible.
- If the code reading data encounters a value in the writer schema that isn't in the reader schema, it is ignored.
- On the other hand, if the writer schema doesn't recognize a field from the reader schema, the default value is used. This allows for forward and backward compatibility.
- Can have old version as writer and new as reader, or vice versa. To remain compatible, may only add/remove fields with default values (ie 0, NOW(), etc.).
- To allow NULL as default val in Avro however, must use union type.
- Changing field names is backward compatible, but not forward compatible, since aliases are used to map old field names to new ones.

Versioning is tricky. Depending on the use case, it is handled differently. For example, if you are storing gigabytes of data in Hadoop, all encoded with the same schema, then you only need to include the writer schema once in the file.

However, in a database where data is written over a long period of time, you can use a version number, and a table of versions for schema version.

In an inter-service communication context, schemas can be negotiated between client and server on connection setup. Using a database of schema versions might be a good idea here.

### Dynamically Generated Schemas

**Situation:** Want to dump database to file on disk using a binary encoding format.

**Problem:** Schema has evolved over time, and there are many different versions of the schema in the database. Would need to manuallty assign field tags for each version of the schema, and then write a custom encoder/decoder for each version.

**Solution:** Avro schema dynamically generated from database schema. Can be rerun whenever schema changes.

This kind of dynamic schema generation was a design goal of Avro, and is less so for protobuf and thrift. Static code generation was a design goal of protobuf and thrift, and is less so for Avro. This makes Avro a natural choice in dynamic languages where code gen is frowned upon (and more generally compile steps), although there are also code generation tools for Avro in static languages.

Keeping a database of schema versions is a good idea, and can be used to generate Avro schemas for each version of the schema. This can be used to generate a schema for each version of the database, and then used to encode/decode data from each version of the database.

## Modes of Dataflow

Generally, one process encodes, and another decodes.

### Dataflow Through Databases

The process that writes to the database is the encoder, and the process that reads from the database is the decoder. Backwards compatability is nessessary for the database to work. It is likely at some point that multiple processes accessing a given database will run different versions of "the code" at a given time. Thus, you need both forward and backward compatibility. Preservation of unknown fields is tricky, and sometimes needs to be solved at the application level.

Generally, can update any value at any time, especially long term; "Data outlives code".

### Dataflow Dumping to Files to Archival Storage

Encoder: process that dumps data to file. Decoder: process that reads data from file. Typically encoded with latest schema, and is a good opportunity to encode in OLAP friendly format (column oriented). Avro is a good choice.

### Dataflow Through Services: REST and RPC

Encoder: client process that sends request to server. Decoder: server process that receives request from client. Generally, client and server are written by same org, so they can be updated at the same time. However, if client and server are written by different orgs, then they may be updated at different times. Thus, you need both forward and backward compatibility.

**Service oriented architectures** are often used in large orgs, where different teams are responsible for different services. Services expose an API, which provides encapsulation that allows the service to be updated without breaking clients. This means that different services may be updated at different times, and thus may be running different versions of the code. Thus, you need both forward and backward compatibility. This is especially true for public APIs, where you have no control over the client. **Web services** are HTTP based services that exist in different contexts:

- intra-organization: services that are only used internally
- public: services that are used by external clients
- partner: services that are used by external clients, but are not public

**REST** is a design philosophy that builds on HTTP. Uses simple data formats, URLs for identifying resources, and HTTP features for cache control, authentication, and content type negotiation.

I'm not even going to get into **SOAP**.

**RPC** is a design philosophy that builds on the idea of calling a function on a remote server. Tries to provide _location transperency_ by abstracting network communication when triggering remote method calls. Many are overly complex, and are not compatible with other languages. **gRPC** is a modern RPC framework that uses protobuf as the interface definition language, and HTTP/2 as the underlying protocol. It is a good choice for internal services, but not for public APIs.

#### Problems with RPC

Network requests are fundamentally different from local function calls. They can fail, be delayed, or be delivered multiple times. This makes designing systems that use RPC more complex, since you need to take into account these failure modes. **Idempotence** is a good way to allow transparent retries, since it means that the same request can be sent multiple times without causing unintended side effects. REST doesn't try to hide the fact that it is a network protocol, and thus is more transparent about failure modes.

Furthermore, the platform lock-in of RPC is a problem. This ties you to a specific language, and makes it difficult to use other languages. This is especially true for public APIs, where you have no control over the client.

#### Current Direction of RPC

Various RPC frameworks exist on top of all the previously mentioned encodings. New generations of RPC frameworks use futures/promises to represent asynchronous responses, and use streaming to represent long lived connections. Some frameworks also include service discovery, which allows clients to find servers without hardcoding their location.

#### Advantages of REST

Vast ecosystem of tools, including servers, load balancers, proxies, caches, and monitoring tools. This makes it easy to build a scalable system. Also, since REST is built on HTTP, it is easy to debug with standard tools. Furthermore, since REST is built on HTTP, it is easy to build a system that works with web browsers. This is especially true for public APIs, where you have no control over the client.

#### Data Encoding and Evolution in RPC

Simplifying assumption about services: All servers updated first, then all clients. This requires forward compatibility, but not backward compatibility.

Service compatibility is difficult in RPC, since it oftentimes needs to be maintained indefinitely. There is no single standard for versioning in RPC, and thus it is often done ad-hoc.

### Dataflow Through Asynchronous Message-Passing

Somewhere between RPC and Databases. Messages are sent from one process to another, and the sender doesn't wait for a response. This is useful for handling high volumes of messages, and for decoupling the sender from the receiver. Uses a message broker (like Kafka, RabbitMQ, etc.), which is a server that receives messages from producers and delivers them to consumers. The broker is responsible for routing messages to the correct destination.

Usually works as follows:

- producer sends message to a named queue/topic, for which there can be one or more consumers
- broker stores message until it is consumed, delivering it to all consumers of the posted topic
- consumer receives message from queue, and processes it

A producer is one way communication, but can be used for request/response. This is useful for decoupling the sender from the receiver, and for handling high volumes of messages. Message brokers often don't enforce any particular data format, and thus are not opinionated about encoding. However, they do need to be able to route messages to the correct destination, and thus need to be able to read the message headers.

Several advantages:

- **Durability**: messages are stored on disk until they are consumed. This allows the broker to be restarted without losing messages.
- **Multiple consumers**: messages can be delivered to multiple consumers. This allows you to scale the number of consumers.
- **Asynchronous**: producers and consumers don't need to be online at the same time. This allows you to buffer messages if the consumer is temporarily unavailable.
- **Queues**: messages can be buffered in a queue if the consumer is not ready to process them yet. This allows you to decouple producers from consumers.

Usually one way communication, but can be used for request/response. This is useful for decoupling the sender from the receiver, and for handling high volumes of messages.

### Distributed Actor Frameworks

**Actor model**: a model of concurrent computation that treats actors as the universal primitives of concurrent computation. In response to a message that it receives, an actor can: make local decisions, create more actors, send more messages, and determine how to respond to the next message received. Actors are essentially state machines that communicate by sending messages to each other.

The same message passing system is used for communication between actors on the same machine and actors on different machines. This means that the same code can be used for both local and remote communication. There is less of a mismatch between local and remote communication, since they use the same primitives. This is in contrast to RPC, where local and remote communication are fundamentally different.

**Actor frameworks** are libraries that provide an implementation of the actor model. They are often used for building distributed systems, since they provide a way to scale up the number of actors. They are also useful for building systems that need to be highly available, since they provide a way to replicate actors. Still need to worry about forward and backward compatibility. Different frameworks have different approaches to compatibility. For example:

- **Akka** uses Java's serialization by default, but can be configured to use protobuf for rolling upgrades.
- **Orleans** uses custom encoding by default, and can be configured to use other encodings. Need to set up and shut down clusters when migrating schemas/versioning.
- **Erlang OTP** experimental support for mapping Erlang data types to protobuf. Still need to be careful about schema evolution.
