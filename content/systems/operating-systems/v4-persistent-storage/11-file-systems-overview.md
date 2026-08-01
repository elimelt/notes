---
title: File Systems, Introduction and Overview
aliases:
  - operating-systems/v4-persistent-storage/11-file-systems-overview
category: Operating Systems
tags:
  - file systems
  - nonvolatile storage
  - metadata
  - executable files
  - file streams
date: 2024-01-08
updated: 2026-07-30
status: evergreen
description: Chapter notes on OSPP chapter 11. What a file system has to provide, the properties of nonvolatile storage, and the core abstractions of files, directories, links, and volumes.
sources:
  - title: "Operating Systems: Principles and Practice (2nd ed.), Anderson and Dahlin, chapter 11"
    url: https://ospp.cs.washington.edu/
    type: textbook
---

## Purpose

Notes on chapter 11 of [Operating Systems: Principles and Practice](https://ospp.cs.washington.edu/). This chapter sets up the file system abstraction; the implementation details live in [[systems/operating-systems/v4-persistent-storage/13-files-and-directories|files and directories]].

A file system has to deliver several things at once:

- **Reliability**
- **Large capacity and low cost**
- **High performance**
- **Named data**
- **Controlled sharing**

## Nonvolatile Storage

Unlike DRAM, nonvolatile storage is persistent, and it is generally cheaper with higher capacity. The price is speed. A magnetic disk access takes on the order of milliseconds against DRAM's nanoseconds, roughly 5 orders of magnitude slower. Current nonvolatile storage technologies also do not allow random access to individual words. Data must be read and written in fixed-size blocks (e.g. 512 bytes). Both properties shape everything a file system does: it batches work into blocks and fights hard to avoid touching the device at all.

## The File System Abstraction

A **file** is a named collection of data in a file system, consisting of the data itself plus metadata describing it (size, owner, permissions, timestamps, and where the data lives on disk).

Files can be *executable*. Executable binaries on Linux begin with a magic number telling the OS how to run the file. Scripts can be executable too, beginning with a shebang (`#!`) followed by the interpreter that should run them.

A traditional file is a single logical stream of bytes. MacOS's HFS+ and Windows NTFS support multiple streams (forks) per file, and in those systems the read and write system calls take an argument naming which stream to touch.

Terms worth having down cold: **directory**, **root directory**, **home directory**, **current working directory**, **path**, **absolute path**, **relative path**.

### Links

The mapping between a name and a file is a **hard link**. A file system that allows multiple hard links to one file stops being a tree and becomes a directed acyclic graph. A **symbolic link** maps a name to another file name instead of to the file itself, which lets you reference files on other volumes or systems. Some operating systems layer similar features above the file system. Windows has **shortcuts**, ordinary files that Windows recognizes and redirects through. MacOS has **aliases**, which behave like symbolic links and also fix themselves up when the target file moves.

### Volumes

A **volume** is a collection of physical storage resources forming one logical storage device. In the simplest case a volume is a single disk. A disk can also be partitioned into multiple volumes, and a single volume can span multiple disks.

## Related notes

- [[systems/research/unix-timesharing-system|The Unix Timesharing System]]
- [[systems/operating-systems/v4-persistent-storage/13-files-and-directories|files and directories]]
- [[systems/operating-systems/lecture-notes/io-systems-secondary-storage|secondary storage]]
