---
title: Scheduling Benchmarks and Simulators
category: Scheduling
tags:
  - scheduling
  - benchmarks
  - simulation
  - queueing
  - fairness
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Runnable simulators for queueing, CPU scheduling, packet fairness, work stealing, and LLM request scheduling.
sources:
  - title: "Operating Systems: Principles and Practice"
    url: https://www.kea.nu/files/textbooks/ospp/
    type: textbook
---

## Purpose

These are not microbenchmarks against kernel schedulers. They are small simulators for checking the math and building intuition:

- queue growth versus utilization
- mean and tail latency under different scheduling policies
- per-flow fairness under packet schedulers
- load balance and steal counts under task schedulers
- TTFT/throughput tradeoffs under simple LLM-serving schedulers

The point is to preserve the pathways for grokking the models, not to pretend these scripts reproduce production systems exactly.

## Files

- `queue_sim.py`: M/M/1-style queue simulator with average and percentile latency
- `cpu_policies.py`: FIFO, SJF, SRPT, and RR on the same job set
- `packet_fairness.py`: FIFO, RR, and DRR over multiple packet flows
- `work_stealing.py`: toy task scheduler with local queues and steals
- `llm_batching.py`: simple request scheduler with KV-budget and batch-token constraints

## Reproduction

```bash
python3 content/systems/scheduling/benchmarks/queue_sim.py --rho 0.8 --jobs 20000
python3 content/systems/scheduling/benchmarks/cpu_policies.py --jobs 40 --seed 0
python3 content/systems/scheduling/benchmarks/packet_fairness.py --rounds 200
python3 content/systems/scheduling/benchmarks/work_stealing.py --workers 8 --tasks 2000 --seed 0
python3 content/systems/scheduling/benchmarks/llm_batching.py --requests 256 --seed 0
```

## Related Notes

- [[systems/scheduling/0-foundations/queueing-models-and-tail-latency|Queueing Models and Tail Latency]]
- [[systems/scheduling/1-single-resource/fifo-sjf-srpt-rr-and-mlfq|FIFO, SJF, SRPT, RR, and MLFQ]]
- [[systems/scheduling/3-network-and-packet/fair-queueing-wfq-and-drr|Fair Queueing, WFQ, and DRR]]
- [[systems/scheduling/5-ml-and-serving/request-scheduling-for-llm-serving|Request Scheduling for LLM Serving]]

