---
title: Objects Handles and Reference Counts
category: Operating Systems
tags: object manager, handles, reference counts, windows, c programming, operating systems
description: Covers the implementation of object handles and reference counting in operating systems, with a focus on the Windows object manager. Discusses the role of the object manager in managing system objects and the use of handles to provide secure access to these objects. Explains the concept of reference counting and how it is used to track the lifetime of objects and prevent premature deallocation.
---

# Obects Handles and Reference Counts

## Object Manager

Windows was written in C, which doesn't have a notion of "objects". Early Windows had its own **Object Manager**, which was responsible for defining object types, naming objects, handling handles for users etc. 

For example, there were objects for threads, processes, files, semaphores, etc.

Each object had a **handle count**, the number of handles the user has to the object, and the **ref count**, the number of references to the object within the kernel (which also includes handles).

