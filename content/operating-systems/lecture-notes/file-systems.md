---
title: File Systems
category: Operating Systems
tags: file systems, storage, hierarchical structure, programming interface, system calls
description: Covers the implementation of file systems, including the programming interface, differences between Windows and Unix file systems, and the on-disk structure of the FAT file system. Discusses key concepts such as file and directory management, design constraints, and the hierarchical structure of file systems.
---

# File Systems

A file system interacts with storage by reading/writing blocks (sectors) on a per-volume basis. It is basically a thick layer of abstraction over the raw storage device.

## Programming Interface

- Naming: files and directories in a hierarchical structure.
- Operations: create, delete, open, close, read, write, seek, stat, etc.

| Windows | Unix |
|---------|------|
| `CreateFile(name, CREATE)` | `open(name, O_CREAT)` |
| `CreateFile(name, OPEN)` | `open(name, O_RDONLY)` |
| `ReadFile(handle, buffer, size)` | `read(fd, buffer, size)` |
| `WriteFile(handle, buffer, size)` | `write(fd, buffer, size)` |
| `CloseHandle(handle)` | `close(fd)` |
| `FlushFileBuffers(handle)` | `fsync(fd)` |
| `SetFilePointer(handle, offset, whence)` | `lseek(fd, offset, whence)` |
| `GetFileSize(handle)` | `fstat(fd, &buf)` |
| `DeleteFile(name)` | `unlink(name)` |
| `MoveFile(old, new)` | `rename(old, new)` |



We all know about this and I'm not going to get into it.

### Windows vs. Unix

#### Moving Files

Windows and Unix have different ways of moving files. In Unix, you always use the `rename` system call. In Windows, moving a file within the same volume is a rename operation, whereas moving a file between volumes is a copy operation followed by a delete operation.

#### Deleting Files

In Unix, a file is not actually deleted until all references to it are removed. In Windows, a file is deleted as soon as the last reference to it is removed. This is why you can't delete a file that is open in Windows.

## Files

A file is logically just a sequence of bytes, typically consisting of data and properties/metadata. Some file systems also have types (ie. regular file, directory, symbolic link, device, etc.). 

Some files are also understood to be executable by the OS. In Windows, the file type is determined by the file extension. In Unix, the file type is determined by the file's metadata.

Shared file handles will also share the file's offset. This can be an issue if you have multiple threads or processes reading/writing to the same file handle.


## Directories

A directory is typically just a file that contains metadata about the files it contains in the form of **directory entries**. It is a mapping from file names to file metadata.


## Design Constriants

- Want to support small and large files efficiently. Small files need small blocks for efficient storage, whereas large files need large blocks for contiguity
- Store actual file data within **blocks**. Need an indexing structure to retrieve the blocks of a file: **inode** in Unix, **file control block** in Windows.
- Also need to be able to efficiently locate free space. Often done with either a **bitmap** or a **free list** on disk.
- Want to maximize spatial locality and minimize seek time, while minimizing fragmentation.
- Need reliability and fault tolerance. Can use **journaling** to recover from crashes, and error detection/correction codes + redundancy to recover from disk errors (RAID).

## On-Disk Structure

There is typically a layer of storage that actually gets persisted on disk, as well as the in-memory representation of the file system that is manipulated by the OS.

### FAT File System

The **File Allocation Table** file system is a simple file system that was used in DOS and Windows. It has a simple on-disk structure that consists of a **reserved area**, a number of **FAT areas**, and a **data area**. The reserved area contains the boot sector and metadata about the file system/disk layout. The FAT areas contain the file allocation table, which is a table that maps file names to disk blocks. The data area contains the actual file data.

```
+-----------------+-----------------+-----------------+-----------------+
| Reserved Area   | FAT Area 1      | FAT Area 2      | Data Area       |
+-----------------+-----------------+-----------------+-----------------+
```