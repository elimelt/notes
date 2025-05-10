---
title: Power Provisioning for a Warehouse-sized Computer
category: Systems
tags: datacenter, power, provisioning, capacity, utilization
description: A paper review of Power Provisioning for a Warehouse-sized Computer
---

###### [Power Provisioning for a Warehouse-sized Computer](https://static.googleusercontent.com/media/research.google.com/en//archive/power_provisioning.pdf)

---

### What is the Problem?
Power provisioning for datacenters is challenging because there's a significant gap between maximum power draw ratings and actual maximum power consumption, leading to underutilization of power infrastructure. Building datacenter power capacity is expensive in nature, so this gap represents a significant opportunity for cost savings by ammortizing the cost of building out infrastructure.

### Summary
The authors present a 6-month study of power usage patterns across large-scale workloads to evaluate opportunities for maximizing power capacity utilization.  They find a pattern of significant underutilization, which could be used to deploy additional servers within the same power budget.

### Key Insights

- The diversity of workloads across a datacenter, as well as the variability between peak and average power consumption, can be safely exploited to increase server density by better matching power provisioning to actual demand
- Power capping provides a safety mechanism enabling more aggressive deployment with minimal risk

### Notable Design Strengths
- Evaluated effectiveness for both well-tuned applications and more realistic workloads
- Large-scale real-world measurements across three major workloads (Websearch, Webmail, MapReduce)

### Limitations/Weaknesses

- Wasn't very prescriptive about how to design more cost-effective systems within the context of the findings, just said to reduce idle power
- Cooling infrastructure and other relevant costs are factored out of the analysis

### Summary of Key Results
- CPU dynamic voltage/frequency scaling might yield moderate energy savings (up to 23%)
- They were able to host between 7% and 16% more computing equipment for individual (well-tuned) applications, and as much as 39% in a real datacenter running a mix of applications

### Open Questions
- Does the flat-tax assumption hold up across all datasets?
- Is there a general framework system designers can use to decrease their idle power consumption to near-zero?