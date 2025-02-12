---
title: Hard Lessons Learned: Windows RtlZeroMemory
category: Operating Systems
tags: RtlZeroMemory, interrupt handling, Windows optimization, operating system development, memory management
description: Covers the implementation of the RtlZeroMemory function in the Windows operating system, highlighting performance optimizations and the impact on interrupt handling. Discusses the "Gary's Sad Story" case study, which demonstrates the importance of understanding low-level memory management details when optimizing system-level code.
---

# Hard Lessons Learned: Windows RtlZeroMemory

## Zero Memory

Make it faster by picking larger register (same optimization can be done to copy memory).

In early Windows, they picked the BIGGEST register (floating point)

## Speed Up Interrupt Handling

- Save only the registers needed by the device driver
- Who would've thought that a device driver would need to do floating point arithmetic.

## Gary's Sad Story

- Everyone in the Windows team ran nightly stress tests on each new build
-  Nightly bug checking of parts of the file system on multiple test machines
-  A *showstopping* bug was assigned to him. Bug was blue screening many test systems.
- Manually checked that *RtlZeroMemory()* to see if it zeros a buffer correctly. It was not.

It turns out Dave Cutler tried to optimize interrupt handling to not save fp registers. Both `RtlZeroMemory` and `RtlCopyMemory` didnt copy the fp registers. When the filesystem calls `RtlZeroMemory`, if an interrupt occurs and the device calls CopyMemory, this has side effects when control is returned to the process.

## Moral of the Story

- Many "good" optimizations have unforseen consequences
- OS develepment is riddled with examples where modifying code one place breaks code elsewhere.
- Unfortunately, bugs in your code are sometimes actually bugs elsewhere, but that won't stop you from being assigned with finding the bug yourself.
