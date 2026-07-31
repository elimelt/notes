---
title: Objects Handles and Reference Counts
aliases:
  - operating-systems/lecture-notes/windows-objects-handles-refcounts
category: Operating Systems
tags:
  - object-manager
  - handles
  - reference-counts
  - windows
date: 2024-01-19
updated: 2026-07-30
status: incomplete
description: The Windows object manager, and how handle counts and reference counts track the lifetime of kernel objects.
sources:
  - title: Windows Internals, Part 1 (Russinovich, Solomon, Ionescu)
    type: book
  - title: Operating systems course lecture notes
    type: lecture
---

This note records how early Windows tracked the lifetime of kernel objects.

Windows was written in C, which has no notion of objects, so the kernel built its own. Early Windows had an **object manager** responsible for defining object types, naming objects, and handing out handles to users. Threads, processes, files, and semaphores were all object types.

Each object carried two counts. The **handle count** is the number of handles users hold on the object. The **ref count** is the number of references to the object within the kernel, and it includes the handles. The kernel-side count prevents premature deallocation. An object can only be freed once its ref count reaches zero, so kernel code that is still using an object keeps it alive even after the user closes every handle.

This is a stub from lecture. It stops before covering how handles resolve to objects through per-process handle tables.

## Related notes

- [[systems/operating-systems/lecture-notes/handle-tables|handle tables]]
