---
title: Processes
aliases:
  - operating-systems/lecture-notes/processes
category: Operating Systems
tags:
  - processes
  - address-space
  - cpu-state
  - pid-namespace
date: 2024-01-13
updated: 2026-07-30
status: evergreen
description: What a process is, the pieces that make one up (address space, CPU state, OS resources), the idealized address space layout, and the PID namespace.
sources:
  - title: Operating systems course lecture notes
    type: lecture
---

A process is the OS's abstraction of a running program: a program in execution. The simplest case is one address space with a single thread of execution.

## What's in a process

A process consists of at least:

- an address space, containing the code (instructions) and data of the running program
- at least one CPU state, consisting of the instruction pointer (EIP), stack pointer (ESP), and the other general purpose registers
- a set of OS resources, including open files, open pipes, open network connections, and so on

### Address space

The stack grows down: push decrements ESP, pop increments it. The stack contains all runtime frames.

A process's address space, idealized:

```text
+----------------------+ <- 0x7FFFFFFF
|        Stack         |
|   (dynamic memory)   |
+----------------------+ <- ESP
|          |           |
|          v           |
|                      |
|          ^           |
|          |           |
+----------------------+
|        Heap          |
|   (dynamic memory)   |
+----------------------+
|        Data          |
|   (data segment)     |
+----------------------+
|        Code          | <- EIP
|   (text segment)     |
+----------------------+ 0x00000000
```

## OS process namespace

- Each process has a unique identifier, the PID.
- The PID namespace is global to the OS.
- Operations that create processes (e.g. `fork`) return the PID.
- Operations on processes (e.g. `kill`) take a PID as an argument.

## Related notes

- [[systems/operating-systems/lecture-notes/kernel-abstraction|kernel abstractions]]
- [[systems/operating-systems/lecture-notes/handle-tables|handle tables]]
- [[systems/operating-systems/v2-concurrency/4-concurrency-and-threads|concurrency and threads]]
