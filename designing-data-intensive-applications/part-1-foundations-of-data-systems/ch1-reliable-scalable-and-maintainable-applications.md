# Chapter 1
## Reliable, Scalable, and Maintainable Applications

### "Data intensive" vs. "Computer intensive"

A data-intensive application is typically built from standard building blocks:

- Store data so that they, or another application, can find it again later (databases)
- Remember the result of an expensive operation, to speed up reads (caches)
- Allow users to search data by keyword or filter it in various ways (search indexes)
- Send a message to another process, to be handled asynchronously (stream processing)
- Periodically crunch a large amount of accumulated data (batch processing)

![image](./sc.png)


### Reliability
A fault is usually defined as one component of the system deviating from its spec, whereas a failure is when the system as a whole stops providing the required service to the user.

**Hardware faults (hard disk crashes, RAM errors, etc.)**
...

**Software faults (crashes, runaway process, slowdowns, cascading failures, etc.)**
Lots of small things can help: carefully thinking about assumptions and interactions in the system; thorough testing; process isolation; allowing processes to crash and restart; measuring, monitoring, and analyzing system behavior in production. If a system is expected to provide some guarantee (for example, in a message queue, that the number of incoming messages equals the number of outgoing messages), it can constantly check itself while it is running and raise an alert if a discrepancy is found

**Human errors (operator error, configuration error, etc.)**
- Design systems in a way that minimizes opportunities for error.
- Decouple the places where people make the most mistakes from the places where they can cause failures.
- Test thoroughly at all levels.
- Allow quick and easy recovery
- Set up detailed and clear monitoring


**Scalability:** the term we use to describe a system's ability to cope with increased
load. Load can be described with a few numbers that are easy to measure:

**Describing Load**
- Requests per second (RPS)
- Reads vs. writes (read-write ratio)
- Cache hit rate
- Concurrent users

When you increase a load parameter and keep the system resources (CPU, memory, network bandwidth, etc.) unchanged, how is the performance of your system affected?

When you increase a load parameter, how much do you need to increase the resources if you want to keep performance unchanged?

#### Latency and Response Time
**Latency** is the duration that a request is waiting to be handled-during which it is latent, awaiting service. **Response time** is the delay between a client sending a request and receiving a response.

#### When Measuring Load
Use percentiles. Look at the median (p50), the 95th percentile (p95), and the 99th percentile (p99).

When making multiple backend calls to external services, take special care to measure the p99 of the overall request latency (not just the p99 of each individual service call). This prevents latency amplification that would potentially impact users.

#### Coping with Load
- Scaling up (vertical scaling): moving to a more powerful machine
- Scaling out (horizontal scaling): distributing the load across multiple smaller machines
- Elasticity: automatically add computing resources when they detect a load increase, and remove resources when the load decreases

There is no generic solution. Scale based on access patterns, not on data size.

### Maintainability
**Operability:** make it easy for operations teams to keep the system running smoothly. Make common tasks easy, and preferably automatic. Good monitoring is also crucial.

**Simplicity:** make it easy for new engineers to understand the system, by removing as much complexity as possible from the system. Manage complexity with abstraction.

**Evolvability:** make it easy for engineers to make changes to the system in the future, adapting it for unanticipated use cases as requirements change. Good abstractions and modularity allow components to be replaced, and the overall system architecture to be modified, without complete reimplementation.