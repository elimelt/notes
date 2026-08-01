---
title: Scheduling
category: Scheduling
tags:
  - scheduling
  - queueing
  - fairness
  - latency
  - throughput
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Cross-cutting systems notes on scheduling, from queueing laws and fairness objectives to CPU, packet, cluster, and model-serving schedulers.
sources:
  - title: "Operating Systems: Principles and Practice"
    url: https://www.kea.nu/files/textbooks/ospp/
    type: textbook
  - title: The Tail at Scale
    url: https://cacm.acm.org/research/the-tail-at-scale/
    type: paper
  - title: Deficit Round Robin
    url: https://dl.acm.org/doi/10.1145/217382.217453
    type: paper
---

## Purpose

This section is for scheduling as a systems idea rather than as one chapter inside operating systems. The same questions keep reappearing across CPUs, routers, clusters, storage services, and model-serving systems:

- which job or flow goes next
- what objective matters most
- where the bottleneck actually is
- how fairness trades against latency and throughput
- what mechanism enforces the policy

The emphasis here should stay reference-heavy. The goal is to preserve the derivations, code sketches, and mental pathways for grokking the main policies well enough to reuse them in another domain.

## Reading Path

The best route is to start with the math, then the single-resource policies, then the multi-resource and domain-specific schedulers.

1. [[systems/performance/latency-throughput-and-utilization|Latency, Throughput, and Utilization]]
2. [[systems/operating-systems/v2-concurrency/7-queueing-theory|Queueing Theory]]
3. [[systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling|Uniprocessor Scheduling]]
4. [[systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling|Multiprocessor Scheduling]]
5. [[systems/distributed-systems/load-balancing|Load Balancing]]
6. [[ml/serving-systems/batching|Batching]]
7. [[ml/serving-systems/performance-modeling|Performance Modeling]]

## Clusters

- Foundations:
  - [[systems/scheduling/0-foundations/littles-law-and-bottleneck-analysis|Little's Law and bottleneck analysis]]
  - [[systems/scheduling/0-foundations/queueing-models-and-tail-latency|queueing models and tail latency]]
  - [[systems/performance/latency-throughput-and-utilization|latency, throughput, and utilization]]
  - [[systems/distributed-systems/load-balancing|tail latency and queueing under load balancing]]
- Runnable artifacts:
  - [[systems/scheduling/benchmarks/README|scheduling benchmarks and simulators]]
- CPU scheduling:
  - [[systems/scheduling/1-single-resource/fifo-sjf-srpt-rr-and-mlfq|FIFO, SJF, SRPT, RR, and MLFQ]]
  - [[systems/scheduling/1-single-resource/real-time-scheduling-edf-and-rate-monotonic|EDF and rate monotonic]]
  - [[systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling|uniprocessor scheduling]]
  - [[systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling|multiprocessor scheduling]]
  - [[systems/operating-systems/v2-concurrency/4-concurrency-and-threads|threads and scheduler activations]]
- Parallel and locality-aware scheduling:
  - [[systems/scheduling/2-parallel-and-multiprocessor/work-stealing-affinity-and-numa|work stealing, affinity, and NUMA]]
  - [[systems/scheduling/2-parallel-and-multiprocessor/numa-aware-scheduling-and-locality|NUMA-aware scheduling and locality]]
- Resource contention and waiting:
  - [[systems/operating-systems/v2-concurrency/5-synchronizing-access-to-shared-objects|synchronization and scheduler interaction]]
  - [[systems/research/locality-principle|locality, working sets, and thrashing]]
- Network and packet scheduling:
  - [[systems/scheduling/3-network-and-packet/fair-queueing-wfq-and-drr|fair queueing, WFQ, and DRR]]
- Cluster and datacenter scheduling:
  - [[systems/scheduling/4-cluster-and-datacenter/cluster-scheduling-and-dominant-resource-fairness|cluster scheduling and DRF]]
  - [[systems/scheduling/4-cluster-and-datacenter/stragglers-speculation-and-overload|stragglers, speculation, and overload]]
  - [[systems/scheduling/4-cluster-and-datacenter/admission-control-backpressure-overload|admission control, backpressure, and overload management]]
- Model-serving scheduling:
  - [[systems/scheduling/5-ml-and-serving/request-scheduling-for-llm-serving|request scheduling for LLM serving]]
  - [[ml/serving-systems/batching|batching]]
  - [[ml/serving-systems/parallelism|parallelism]]
  - [[ml/serving-systems/performance-modeling|performance modeling]]
  - [[ml/serving-systems/speculative-decoding|speculative decoding]]
- Adjacent systems:
  - [[systems/networks/4-transport/TCP|TCP congestion behavior]]
  - [[systems/networks/2-direct-links/multiple-access|scheduled versus random access on links]]
  - [[systems/distributed-systems/managing-critical-state|leadership and serialized critical work]]

## Planned Depth

The section should eventually cover at least these layers:

- queueing laws, response-time distributions, and bottleneck analysis
- single-resource policies like FIFO, SJF, SRTF, RR, MLFQ, EDF, and fair sharing
- multiprocessor policies like affinity scheduling, work stealing, gang scheduling, and NUMA-aware placement
- packet and flow schedulers like WFQ and DRR
- cluster schedulers, dominant-resource fairness, and straggler mitigation
- request scheduling, admission control, and SLO-aware scheduling for modern model-serving systems

## Notes on Scope

Some notes already exist in other branches and should stay there because their home context matters. This section is meant to link them together and eventually add the missing cross-domain material, not flatten everything into one folder.
