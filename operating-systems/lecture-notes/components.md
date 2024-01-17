# Components of an OS

## Process Operations

OS provides the following kinds of operations:

- *Create* a process
- *Delete* a process
- *Suspend* a process
- *Resume* a process
- *Clone* a process
- Inter-process *communication*
- Inter-process *synchronization*
- Create/delete *child* processes (*subprocess*)

## Memory Management

primary memory is directly accessible to the CPU.

- Programs must be in memory to execute
- Memory access is fast
- Memory is non-persistent (volatile)

OS must:

- Allocate memory for process
- deallocate memory when process terminates
- maintain mappings from physical -> virtual memory though *page tables*
- decide how much memory to allocate to each process

## I/O

- a "big" chunk of kernel deals with I/O. Soft of like the "glue" that connects devices to the rest of the system.
- OS must provide a uniform interface to devices

### Device Drivers

Routines that interact with specific device types. **Encapsulate** the details of the device.

- e.g. how to initialize the device, how to request I/O, how to handle interrupts, etc.
- ex: SCSI device drivers, Ethernet card drivers, video card drivers.

Note: Windows has ~35,000 device drivers.

### File Systems

A nice abstraction on top of physica storage device drivers. Provides the usual list of operations (open, close, read, write, seek, etc.), but also higher level operations on the fs itself:

- create/delete files
- create/delete directories
- accounting and quotas
- backup and restore
- (sometimes) indexing and searching
- (sometimes) file versioning


### Structure

```txt
Monolith:

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

advantages:
- cost of module interaction is low (procedure call)

disadvantages:
- hard to maintain
- hard to extend


### Layering


#### Dikjstra's "THE" multiprogramming system:

Each layer presents a "virtual machine" to the layer above it. Each layer only uses the services of the layer below it.

- Layer 5: Job Managers, execute user programs
- Layer 4: Device Managers, handle devices and provide buffering
- Layer 3: Console Manager, implements virtual consoles
- Layer 2: Page Manager, implements virtual memory
- Layer 1: Kernel, implements virtual processor for each process
- Layer 0: Hardware

Each layer can be tested and verified independently.

#### Hardware Abstraction Layer

Goal: seperate hardwarte-specific routines from the "core" OS. Provides protability and improves readability.


### Microkernels

Introduced in the late 80s, early 90s. Goal: minimize the kernel, move as much as possible into user space.

Results in:
- better reliability (isolation between components)
- better portability (less code to port)
- better extensibility (easier to add new features)

OS is split into two parts:

- microkernel: provides basic OS services (process management, memory management, I/O, etc.)
- system processes (servers): provide higher level services (file system, networking, scheduling, etc.)

Probably slower than monolithic kernel because of all the expensive context switches.

