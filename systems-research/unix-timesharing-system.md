---
title: The Unix Timesharing System
category: Operating Systems
tags: unix, systems, operating systems
description: Paper review/notes from lecture of Unix Timesharing System
---

# [source](https://people.eecs.berkeley.edu/~brewer/cs262/unix.pdf)

###### The Unix Timesharing System

---

### What is the Problem?

A very unspecific problem. Essentially they were burnt by Multics and wanted to create a simpler and more general system.

### Summary 

Key design goal is simplicity. Everything is hierarchical. Everything is a file.

#### File System Implementation

- Tree strucutre
- FS mounted on a file
- Sys table of i-numbers (i-list)
- i-node contains metadata for each file
- path names don't distinguish between files and directories
- mount table for mounted file systems
- buffering is built into kernel and transparent to user
    - write-behind (flushes to disk when buffer is full)

#### Storage Devices

- block devices
    - data is stored in fixed-size blocks
    - "free list" of blocks for allocation, Linked list of blocks
    - hard disks, usb drive, ssd, tape drives
    - early versions of ethernet
- character devices

#### Execution

- **Image** is an execution env (parallel container)
- **Process** is an instance/execution of an image
    - Program text write-protected and shared between all instances of that process
    - Separate virtual address space for each process
- Kernel
    - Mediator for accessing services/hardware/shared resources
### Key Insights

-
-

