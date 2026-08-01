---
title: The Unix Timesharing System
aliases:
  - systems-research/unix-timesharing-system
category: Systems Research
tags:
  - unix
  - systems
  - operating systems
  - paper-notes
  - file-systems
date: 2025-01-16
updated: 2026-07-30
status: draft
description: Paper and lecture notes on the original Unix paper, covering the file system implementation, device model, and process model.
sources:
  - title: The UNIX Time-Sharing System (Ritchie and Thompson)
    url: https://people.eecs.berkeley.edu/~brewer/cs262/unix.pdf
    type: paper
---

## Purpose

Notes from reading the Unix paper alongside lecture. These stay close to the mechanics, mostly the file system and process model. I never wrote up my own takeaways, so this is a record of the design more than a review of it.

## Citation

- [The UNIX Time-Sharing System](https://people.eecs.berkeley.edu/~brewer/cs262/unix.pdf), Ritchie and Thompson.

## Problem

The problem statement is deliberately unspecific. The authors were burnt by Multics and wanted a simpler, more general system. The key design goal is simplicity: everything is hierarchical, and everything is a file.

## File system implementation

The [[systems/operating-systems/lecture-notes/file-systems|file system]] is a tree, and additional file systems get mounted onto a file. A system table of i-numbers (the i-list) holds an i-node of metadata for each file. Path names don't distinguish between files and directories, and a mount table tracks mounted file systems.

Buffering is built into the kernel and transparent to the user, with write-behind flushing to disk when the buffer fills.

## Storage devices

Block devices store data in fixed-size blocks and manage allocation through a free list, a linked list of blocks. Hard disks, tape drives, and later devices like USB drives and SSDs fit this model, and early versions of Ethernet were exposed the same way. Character devices cover everything else.

## Execution

An **image** is an execution environment, a rough parallel to a container. A **process** is an instance of an image in execution. Program text is write-protected and shared between all processes running the same image, while each process gets its own virtual address space. The kernel sits underneath as the mediator for services, hardware, and shared resources.

## Sources

- [The UNIX Time-Sharing System](https://people.eecs.berkeley.edu/~brewer/cs262/unix.pdf)

## Related notes

- [[systems/research/exokernel|Exokernel]]
- [[systems/research/xen|Xen and the Art of Virtualization]]
- [[systems/operating-systems/lecture-notes/file-systems|File Systems]]
- [[systems/operating-systems/v4-persistent-storage/13-files-and-directories|Files and Directories]]
- [[systems/operating-systems/lecture-notes/io-systems-secondary-storage|I/O Systems and Secondary Storage]]
- [[systems/operating-systems/lecture-notes/file-systems|File Systems]]
- [[systems/operating-systems/v4-persistent-storage/13-files-and-directories|Files and Directories]]
- [[systems/operating-systems/lecture-notes/io-systems-secondary-storage|I/O Systems and Secondary Storage]]
