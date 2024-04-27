# Scaling Web Services with Distributed Architectures

## Two Tier Architecture

Many companies adopted the idea of a two tier architecture for web services. The idea was to have a scalable number of frontend servers, mapping clients to one of those servers. Then, you could also have a scaled out backend with multiple storage severs, mapping frontend servers to the data they needed in the storage servers.

### Two-Tier RESTful Web Architecture

Keep a scalable number stateless servers hosting the client and running application code. Importantly, it doesn't matter if a client server crashes, since the user can just connect to some other client server. At the same time, run a scalable number of backend servers running in a carefully designed distributed system, often using primary/backup or paxos for high availability and fault tolerance. Anything that needs to be persistent across crashes should be handled on the backend.

### Load Balancing

Typically, the layer between the tiers of such architectures are composed of load balancers, which need to map any given client to a desirable front-end server. This needs to be consistent per connection, which can be done with `hash(clientIP, port) -> clientServerIP`. Additionally, you need to map each client server to a storage server, which can be done by `hash(key) -> storageServerIP`, where the key is some identifier for the location of the data in a given query to our storage system.

Importantly, the system should automatically adapt to the addition of any type of server.

### Three-Tier Web Architecture: Look-aside Caching

Also maintain a set of cache servers to offload queries to the storage server. Client servers first send their query to the cache server, and if there is a cache miss they then fall back to the storage servers, and then write the retrieved data to the cache (this is look-aside caching).

There are other ways to do caching. For instance, the cache could directly retrieve values transparently to the client server, such that cache misses don't need to be handled. However, this tightly couples the cache and the storage server, often requiring that all queries pass through the caching layer, making it harder to design the two services independently.

Of course, caching needs to be scalable as well. Cache servers don't necessarily need to be 1:1 with client/storage servers, but they should be able to handle the load of the client servers they are caching for adaptively. They should also ideally have lower latency than actual queries executed in the storage layer.

## Newer Architectures

### Edge Computing

**Moving data processing closer to the client.**

Users are often globally distributed, leading to higher latency and thus worse user experience.

To mitigate this, large applications will often be globally distributed in **edge data centers**, ideally with one reasonably near every user. Often, only the web and cache (*RESTful*) layer are present on the edge, and content can be distributed by "pushing" it to the edge before it is ever requested.

In tandem, **core data centers** host the web, cache, *and* storage layer, replicating all of this across data centers for disaster tolerance.

### Service Oriented Architecture

Services define external interfaces, and often requires distributed systems that work in a hostile environment. All teams expose the data/functionality through this interface, and **all** communication happens through network calls. Each service runs as a standalone product with its own *service level agreement* to its clients.

### Microservices

Organize complex distributed applications as a large number of independent services communicating through RPC, each using primary/backup or paxos for high availability and fault tolerance.

This allows for independent development of components of a larger system, where each component can scale independently.
