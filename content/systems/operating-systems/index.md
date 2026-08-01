---
title: Operating Systems
category: Operating Systems
tags:
  - operating systems
  - processes
  - threads
  - virtual-memory
  - file systems
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Overview of the operating systems notes, spanning kernels, concurrency, memory, storage, and performance measurements.
sources:
  - title: Operating systems course lecture notes
    type: lecture
  - title: "Operating Systems: Principles and Practice"
    url: https://www.kea.nu/files/textbooks/ospp/
    type: textbook
---

## Purpose

This section mixes lecture notes, textbook notes, and benchmarks. The payoff is that the abstractions and the measurements live in one place. You can read about virtual memory in one note and then jump straight to a benchmark that makes a cache or TLB effect visible.

For the conceptual path, start with [[systems/operating-systems/v1-kernels-and-processes/2-the-kernel-abstraction|the kernel abstraction]], [[systems/operating-systems/v1-kernels-and-processes/3-the-programming-interface|the programming interface]], then the concurrency notes in [[systems/operating-systems/v2-concurrency/4-concurrency-and-threads|concurrency and threads]] and [[systems/operating-systems/v2-concurrency/5-synchronizing-access-to-shared-objects|synchronization]]. Storage picks up in [[systems/operating-systems/v4-persistent-storage/11-file-systems-overview|file systems overview]].

## Clusters

- Core abstractions: [[systems/operating-systems/v1-kernels-and-processes/2-the-kernel-abstraction|kernel abstraction]], [[systems/operating-systems/v1-kernels-and-processes/3-the-programming-interface|programming interface]]
- Concurrency: [[systems/operating-systems/v2-concurrency/4-concurrency-and-threads|threads]], [[systems/operating-systems/v2-concurrency/5-synchronizing-access-to-shared-objects|synchronization]], [[systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling|uniprocessor scheduling]]
- Memory and translation: [[systems/operating-systems/lecture-notes/paging|paging]], [[systems/operating-systems/lecture-notes/tlb|TLB]], [[systems/operating-systems/benchmarks/tlb|TLB benchmark]]
- Storage: [[systems/operating-systems/v4-persistent-storage/11-file-systems-overview|file systems overview]], [[systems/operating-systems/v4-persistent-storage/13-files-and-directories|files and directories]]
- Measurements: [[systems/operating-systems/benchmarks/README|benchmark guide]], [[systems/operating-systems/benchmarks/false_sharing|false sharing]], [[systems/operating-systems/benchmarks/bandwidth|memory bandwidth]]
- Reference material: [[systems/operating-systems/reference|OSPP volumes]], [[systems/operating-systems/section-notes/section-1|C and GDB review]]
