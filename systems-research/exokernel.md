---
title: Exokernel: An Operating System Architecture for Application-Level Resource Management
category: systems
tags: operating systems, exokernel, resource management
description: Paper review for the classic exokernel paper
---

### What is the Problem?

Operating systems with monolithic kernels prescribe interfaces of key OS abstractions like virtual memory, filesystem, but with these prescriptions come side-effects, particularly in the realm of performance. Applications cannot modify or optimize these abstractions for their specific needs, forcing them to work within the limitations of a "one-size fits all" implementation, which typically prioritizes generality over performance for any specific application.

### Summary 

The paper covers the exokernel architecture, which aims to minimize the "mechanism" role as much as possible, opting to leave implementations to the client, e.g. to the user's choice of library operating system. The key design choice here is to separate resource protection from management, e.g. to provide secure bindings to access a device, without necessarily understanding the use case.

The authors were able to realize significant (orders of magnitude) speedups on most primitive tasks compared to a more mature OS (Ultraix) by focusing almost solely on efficiently multiplexing hardware, and by minimizing the number of required system calls during regular operation.

### Key Insights

- General-purpose abstractions in monolithic kernels can lead to performance overhead
  - Resource management is next-to-impossible since most resources are completely abstracted. Instead the kernel interface should be as close to hardware as possible, opting to use physical addresses, etc.
  - Applications will oftentimes be working against built in "features" of the OS, e.g. databases slowed down by filesystems, non-zero-copy networking
- Applications must frequently defer to the kernel for operations that could be done in user space, incurring context switching overhead

### Notable Design Details/Strengths 

- The interface provided by the kernel should be as close to hardware as possible, so as to directly expose hardware resources to applications in a safe manner
- Library operating systems can be tailored to specific use cases, avoiding the overhead of general-purpose abstractions usually found in monolithic kernels
- kernel interface with limited scope leads to better overall design
  - completeness: optimizing the hell out of what little it does is a lot easier
  - simplicity: less code to maintain, less code to break
  - extensibility: easier to add new features via library OSes than to modify the kernel

### Limitations/Weaknesses 

- Compatibility between system-level software and dependencies has been kicked into user space, likely leading to less stability/reliability, or at the very least more work for the application developer and end user
  - Third party library OSes are very suspect
  - Unless standards are not only developed but widely adopted for all OS components in user space, this could be a major issue
- Cross-platform compatibility is not a priority, and additional work would be needed to port all upstream library OSes to a new exokernel to port an application

### Summary of Key Results

- Many primitives are 1-2 orders of magnitude faster than Ultraix
  - Exception handling, virtual memory, IPC, etc. faster than Ultraix, and in some cases faster than SOTA implementations
  - Primarily due to reduced context switching, low-overhead multiplexing of hardware, and specialized implementations of aforementioned systems in user space

### Open Questions

- Why didn't this work out? I was fully bought in by the end of the paper, but they were clearly never adopted.
- Can this approach be applied to modern, and particularly datacenter, workloads?
- How can malicious/destructive library OSes be prevented?