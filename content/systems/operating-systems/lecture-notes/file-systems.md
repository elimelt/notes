---
title: File Systems
aliases:
  - operating-systems/lecture-notes/file-systems
category: Operating Systems
tags:
  - file systems
  - storage
  - syscall
  - fat
date: 2024-03-04
updated: 2026-07-30
status: draft
description: The file system programming interface, how Windows and Unix differ on moving and deleting files, the constraints that drive on-disk layout, and the FAT on-disk structure.
sources:
  - title: unlink(2), Linux manual page
    url: https://man7.org/linux/man-pages/man2/unlink.2.html
    type: docs
  - title: Operating systems course lecture notes
    type: lecture
---

A file system reads and writes blocks (sectors) on a per-volume basis and turns them into files and directories. It is a thick layer of abstraction over the raw storage device. This note covers the programming interface, a couple of behavioral differences between Windows and Unix, the constraints that shape on-disk layout, and FAT as a concrete example.

## Programming interface

Naming is hierarchical: files live in directories, and directories nest. The operations are the familiar ones.

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

### Moving files

Unix always moves with the `rename` system call. Windows renames only when the file stays on the same volume; a move across volumes becomes a copy followed by a delete.

### Deleting files

Unix separates a file's name from the file itself. [`unlink`](https://man7.org/linux/man-pages/man2/unlink.2.html) removes the name, and the storage is reclaimed only after the last reference to the file (an open descriptor or a remaining hard link) goes away, so deleting a file that some process still has open works fine. Windows ties deletion to open handles instead. By default you cannot delete a file while a process has it open, which is where "file in use" errors come from.

## Files

A file is logically a sequence of bytes, plus properties and metadata. Some file systems also track a type (regular file, directory, symbolic link, device). Some files are understood to be executable by the OS. Windows decides a file's type by its extension, while Unix records the type in the file's metadata.

Shared file handles share the file's offset. Multiple threads or processes reading and writing through the same handle will step on each other's position.

## Directories

A directory is typically just a file whose contents are **directory entries**: a mapping from file names to file metadata.

## Design constraints

- Support small and large files efficiently. Small files want small blocks for storage efficiency, while large files want contiguity.
- File data lives in **blocks**, so an indexing structure has to locate the blocks of a file. Unix calls it an **inode**, Windows a **file control block**.
- Free space has to be findable quickly, usually with a **bitmap** or a **free list** on disk.
- Placement should maximize spatial locality while keeping seek time and fragmentation down.
- Crashes and disk errors happen. **Journaling** recovers from crashes, and error detection/correction codes plus redundancy (RAID) recover from disk errors.

## On-disk structure

The file system has two representations. One layer actually gets persisted on disk. A separate in-memory representation is what the OS manipulates.

### FAT

The **File Allocation Table** file system from DOS and early Windows keeps its on-disk structure simple. The volume splits into a reserved area, one or more FAT areas, and a data area:

```text
+-----------------+-----------------+-----------------+-----------------+
| Reserved Area   | FAT Area 1      | FAT Area 2      | Data Area       |
+-----------------+-----------------+-----------------+-----------------+
```

The reserved area holds the boot sector and metadata about the file system and disk layout. Each FAT area holds a copy of the file allocation table, which has one entry per data cluster, and each entry points to the next cluster of the file it belongs to, so a file is a linked chain through the table. Directory entries in the data area map file names to a file's starting cluster and metadata. The data area holds the actual file contents.

## Related notes

- [[systems/operating-systems/lecture-notes/io-systems-secondary-storage|I/O systems and secondary storage]]
