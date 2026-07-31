---
title: Fundamentals of Data-Intensive Application Design and Scalability
category: Software Engineering
tags:
  - reliability
  - scalability
  - maintainability
  - data-systems
  - performance
date: 2023-12-19
updated: 2026-07-30
status: evergreen
description: Reading notes on chapter 1 of Designing Data-Intensive Applications. Covers faults versus failures, how to describe load and response time, and the three ingredients of maintainability.
sources:
  - title: Designing Data-Intensive Applications, Martin Kleppmann
    url: https://dataintensive.net/
    type: book
---

## Purpose

Reading notes on chapter 1 of [Designing Data-Intensive Applications](https://dataintensive.net/) by Martin Kleppmann. The chapter defines the vocabulary the rest of the book leans on: reliability, scalability, and maintainability, and how to reason about each.

## Data intensive vs. compute intensive

An application is data-intensive when the hard part is the volume, complexity, or rate of change of its data rather than raw CPU work. Kleppmann's point is that these applications get built from a small set of standard building blocks:

- Databases, which store data so it can be found again later
- Caches, which remember the result of an expensive operation to speed up reads
- Search indexes, which let users search or filter data by keyword
- Stream processing, which sends messages to other processes for asynchronous handling
- Batch processing, which periodically crunches a large amount of accumulated data

## Reliability

A fault is one component of the system deviating from its spec. A failure is the system as a whole no longer providing the service the user needs. The design goal is to keep faults from turning into failures.

### Hardware faults

Hard disks crash, RAM corrupts, power supplies die. The traditional response is hardware redundancy, for example RAID for disks and dual power supplies. As systems grow to many machines, hardware faults stop being rare events, so the book argues for tolerating whole-machine loss in software on top of hardware redundancy.

### Software faults

Crashes, runaway processes, slowdowns, and cascading failures tend to be correlated across machines, which makes them harder than hardware faults. Lots of small things help: thinking carefully about assumptions and interactions in the system, thorough testing, process isolation, letting processes crash and restart, and measuring system behavior in production. If a system is expected to provide some guarantee, for example that a message queue emits as many messages as it ingests, it can check that invariant while running and alert on any discrepancy.

### Human errors

Operators and engineers misconfigure things. The mitigations are structural:

- Design systems in a way that minimizes opportunities for error
- Decouple the places where people make the most mistakes from the places where mistakes cause failures
- Test thoroughly at all levels
- Allow quick and easy recovery
- Set up detailed and clear monitoring

## Scalability

Scalability describes a system's ability to cope with increased load. Load is described with a few numbers that are easy to measure, called load parameters:

- Requests per second
- Read-write ratio
- Cache hit rate
- Concurrent users

Two questions frame any scalability discussion. When you increase a load parameter and keep resources (CPU, memory, network bandwidth) unchanged, how does performance degrade? And when you increase a load parameter, how much do you need to increase resources to keep performance unchanged?

### Latency and response time

Latency is the duration a request waits to be handled, during which it is latent, awaiting service. Response time is the delay between a client sending a request and receiving a response, so it includes network delays and queueing on top of service time.

### Measuring response time

Use percentiles rather than averages. Look at the median (p50) alongside the tail, p95 and p99. When a single user request fans out into multiple backend calls, measure the p99 of the overall request, since the slowest backend call dominates the user's experience. Kleppmann calls this tail latency amplification: the more backend calls a request makes, the higher the chance it hits at least one slow one.

### Coping with load

Scaling up (vertical scaling) means moving to a more powerful machine. Scaling out (horizontal scaling) means distributing the load across multiple smaller machines. Elastic systems add computing resources automatically when they detect a load increase and remove them when load drops. There is no generic solution. Scale based on access patterns rather than data size.

## Maintainability

Operability means making it easy for operations teams to keep the system running smoothly. Make common tasks easy, and preferably automatic. Good monitoring is crucial here.

Simplicity means making it easy for new engineers to understand the system by removing as much accidental complexity as possible. Abstraction is the main tool for managing complexity.

Evolvability means making it easy for engineers to change the system in the future as requirements change. Good abstractions and modularity allow components to be replaced and the overall architecture to be modified without a complete reimplementation.

## Sources

- [Designing Data-Intensive Applications](https://dataintensive.net/), Martin Kleppmann, chapter 1

## Related notes

- [[designing-data-intensive-applications/part-1-foundations-of-data-systems/ch2-data-models-and-query-languages|data models and query languages]]
- [[designing-data-intensive-applications/part-1-foundations-of-data-systems/ch3-storage-and-retrieval|storage and retrieval]]
