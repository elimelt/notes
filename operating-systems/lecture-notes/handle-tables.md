---
title: Handle Tables
category: Operating Systems
tags: handle tables, process control block, context switch, scheduling, state queues
description: Covers the implementation of handle tables, which are used to manage the process control block (PCB) in operating systems. Discusses the PCB structure, including the process and CPU state, state queues for scheduling, and the creation of new PCBs. Explores techniques to optimize the creation of new PCBs for improved performance.
---

# Handle Tables


There is a local handle table for each process, and a global handle table within the kernel.


## Process Control Block (PCB)

- Data structure to keep track of process state. Each element identified by PID
- OS keeps all of a process' state in `proc` within the PCB while it isn't running.

`proc` has many many fields. (pid, pointer to paprent proc, execution state, etc.)

In Linux, defined within `task_struct(include/linux/sched.h)`. Has over 95 fields!

### proc and CPU state

**context switch**: take the currently running processes state from the CPU and save it in the PCB, then grab the next scheduled proccess' `proc` off of the PCB and load it into the CPU to run.

Choosing the next process to run is called **scheduling**.

The OS kernel is NOT a process, just a block of code. Remember: *the CPI is always executing code in the context of a process. That code may be in either kernel or user mode.*


### State Queues

Typically there is a queue of `proc`s that correspond to each of the states a process can take (ie `WAITING`, `READY`). There might even be many wait queues, one for each type of wait (particular device, timer, message, etc.).

- procs are just data structures, dynamically allocated in the OS memory. 
- procs are created by existing processes. creator is parent, creation is child.

### Creation

- `fork` basically clones process
- `exec` stops the current process, loads a new program into the address space (ie overwrites), initializes hardware and args for program, and places process on ready queue. 

Note that `exec` doesn't create a new process.

To create a new process (ie from a shell), fork the shell process, and then exec the program 

#### Making Creation Faster

method 1: `vfork`: 

the older (now uncommon) way to do it. Instead of making a new child address space being a copy, just point to the parent address space from the child. This was an unenforced "promise" that the child wouldn't modify the address space. The child has the same page table and everything.

method 2: copy on write.


 
