---
title: Power Provisioning for a Warehouse-sized Computer
aliases:
  - systems-research/data-center-power-provisioning
category: Systems Research
tags:
  - datacenter
  - power
  - provisioning
  - capacity
  - utilization
  - paper-notes
date: 2025-03-12
updated: 2026-07-30
status: evergreen
description: Review notes on Google's study of datacenter power usage, which measures the gap between provisioned and actual power draw and estimates how many extra servers that gap can host.
sources:
  - title: Power Provisioning for a Warehouse-sized Computer (ISCA 2007)
    url: https://static.googleusercontent.com/media/research.google.com/en//archive/power_provisioning.pdf
    type: paper
---

## Purpose

Reading notes on the Google power provisioning paper. The note captures why the gap between rated and actual power draw matters economically, what the study measured, and where the analysis stops short.

## Citation

- [Power Provisioning for a Warehouse-sized Computer](https://static.googleusercontent.com/media/research.google.com/en//archive/power_provisioning.pdf), Fan, Weber, and Barroso, ISCA 2007.

## Problem

Datacenter power infrastructure is provisioned against nameplate ratings, but real machines almost never draw their rated maximum. That gap means the expensive part of the facility, the power delivery capacity, sits underused. Since building out capacity dominates cost, closing the gap amortizes the infrastructure over more machines and saves real money.

## Main idea

Measure actual power usage at scale, quantify the gap between provisioned and consumed power at rack, PDU, and cluster level, and use that headroom to pack more servers under the same power budget. Power capping acts as the safety net that makes the oversubscription safe.

## Evidence

The authors ran a 6-month study of power usage across large-scale workloads at Google, covering three major workloads (Websearch, Webmail, MapReduce) plus a real mixed-use datacenter. They found consistent underutilization of provisioned power, and the gap widens as you aggregate: a whole cluster almost never peaks the way a single rack can. Key numbers from the paper:

- Individual well-tuned applications could host 7% to 16% more machines within the same power budget, and a real datacenter running a mix of applications could host as much as 39% more.
- CPU dynamic voltage/frequency scaling was estimated to yield moderate energy savings, up to 23%.

## Key insights

Workload diversity across a datacenter, plus the variability between peak and average power per workload, means aggregate peak power is far below the sum of individual peaks. That headroom can be exploited safely as long as a power capping mechanism exists to throttle machines in the rare case the aggregate approaches the budget. Capping converts a hard provisioning problem into a soft enforcement problem, which lets operators deploy more aggressively with minimal risk.

The evaluation covers both well-tuned applications and messier realistic workloads, which makes the deployment estimates more credible than a study of a single benchmark would be.

## Assumptions and limits

The paper is descriptive rather than prescriptive. It tells you the gap exists and recommends driving idle power toward zero, but gives little guidance on how to design systems that actually do that. Cooling infrastructure and other related costs are also factored out of the analysis, so the economic picture is partial.

## Open questions

- Does the flat-tax assumption for non-critical power overhead hold up across other datasets?
- Is there a general framework system designers can use to drive idle power consumption to near zero?

## Sources

- [Power Provisioning for a Warehouse-sized Computer](https://static.googleusercontent.com/media/research.google.com/en//archive/power_provisioning.pdf)

## Related notes

- [[hardware/signal-conditioning/lecture-notes/lecture-1|C-SWAP: Cost, Size, Weight and Power]]
