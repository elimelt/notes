---
title: Components of an OS
aliases:
  - operating-systems/lecture-notes/components
category: Operating Systems
tags:
  - process-operations
  - address-space
  - memory management
  - virtual-memory
  - page-tables
  - io
  - device-drivers
  - file systems
  - kernel-structure
date: 2024-01-13
updated: 2026-07-30
status: evergreen
description: Surveys the services an OS provides (process operations, memory management, I/O, file systems) and compares monolithic, layered, and microkernel structures.
sources:
  - title: E. W. Dijkstra, "The Structure of the 'THE'-Multiprogramming System" (CACM, 1968)
    url: https://dl.acm.org/doi/10.1145/363095.363143
    type: paper
  - title: Operating systems course lecture notes
    type: lecture
---

This note maps out what an operating system actually contains. The first half lists the services the kernel provides for processes, memory, I/O, and files. The second half looks at how kernels arrange those pieces.

## Process operations

The OS provides operations to:

- create and delete a process
- suspend and resume a process
- clone a process
- communicate and synchronize between processes
- create and delete child processes (subprocesses)

## Memory management

Primary memory is the only storage the CPU can access directly. A program has to be in memory to execute, access is fast, and the contents disappear on power loss.

The OS allocates memory for a process, deallocates it when the process terminates, maintains the mapping between virtual and physical memory through page tables, and decides how much memory each process gets.

## I/O

A big chunk of the kernel deals with I/O. It acts as the glue between devices and the rest of the system, and it has to present a uniform interface over wildly different hardware.

### Device drivers

Drivers are the routines that talk to a specific device type. They encapsulate the device's details, e.g. how to initialize it, how to request I/O, and how to handle its interrupts. SCSI drivers, Ethernet card drivers, and video card drivers are all examples. The lecture put the count of device drivers written for Windows around 35,000.

### File systems

The file system is an abstraction on top of the physical storage drivers. It provides the usual per-file operations (open, close, read, write, seek) plus higher level operations on the file system itself:

- create and delete files and directories
- accounting and quotas
- backup and restore
- sometimes indexing, search, and file versioning

## Kernel structure

### Monolithic

```text
+----------------------+
|    User Programs     |
+----------------------+
|      Everything      |
|      Else in OS      |
+----------------------+
|     Device Driver/   |
|     hardware stuff   |
+----------------------+
```

Everything lives in one kernel, so a call from one module to another costs only a procedure call. That is the main advantage. The price is a codebase that resists change, since every module can reach into every other module.

### Layering

Dijkstra's ["THE" multiprogramming system](https://dl.acm.org/doi/10.1145/363095.363143) structured the OS as layers. Each layer presents a virtual machine to the layer above it and only uses the services of the layer below it:

- Layer 5: job managers, execute user programs
- Layer 4: device managers, handle devices and provide buffering
- Layer 3: console manager, implements virtual consoles
- Layer 2: page manager, implements virtual memory
- Layer 1: kernel, implements a virtual processor for each process
- Layer 0: hardware

Each layer can be tested and verified independently.

### Hardware abstraction layer

A HAL separates hardware-specific routines from the core OS, which makes the core portable and keeps hardware details out of the way of readers.

### Microkernels

Microkernels showed up in the late 80s and early 90s. The idea is to shrink the kernel and move as much as possible into user space. The microkernel keeps basic services like process management, memory management, and I/O. Higher level services (file system, networking, scheduling policy) run as user-space server processes.

The isolation between components buys reliability, and a smaller kernel means less code to port to new hardware. Extending the system means adding a server rather than patching the kernel. The cost is speed. Requests that a monolithic kernel would handle with a procedure call now cross address space boundaries, so a microkernel is probably slower.

## Related notes

- [[systems/operating-systems/lecture-notes/kernel-abstraction|hardware modes]]
- [[systems/operating-systems/lecture-notes/processes|processes]]
- [[systems/operating-systems/lecture-notes/file-systems|file systems]]
- [[systems/research/unix-timesharing-system|Unix timesharing system]]
- [[systems/operating-systems/reference|operating systems reference]]
- [[systems/research/barrelfish|multikernel]]
