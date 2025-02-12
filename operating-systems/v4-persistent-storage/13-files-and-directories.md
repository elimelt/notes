---
title: Files and Directories
category: Operating Systems
tags: directories, index structures, free space maps, locality heuristics, file systems, persistence, performance
description: Covers the implementation of file systems, including the use of directories and index structures for organizing and accessing data. Discusses free space management techniques and locality heuristics to optimize file system performance. Examines the internals of directories, such as link structures, and the mechanisms for finding data in files, including case studies and the FAT file system.
---

# Chapter 13 - Files and Directories

Need to achieve the following:

- **performance**
- **flexibility**
- **persistence**
- **relability**

## Implementation Overview

Most implementations are based on four key ideas:

- directories
- index structures
- free space maps
- locality heuristics

### Directories and Index Structures

File names and offsets are mapped to storage blocks in two steps:

1. **directories** map names to file numbers
2. **index structures** map file numbers and offsets to storage blocks

Often, the index is some form of tree.

### Free Space Maps

Free space maps are used to keep track of which blocks are free and which are in use. At a minimum, it needs to work, but it is also nice if files are allocated in a way that gives better spacial locality. For example, many file systems implement free space maps as bitmaps in persistent storage.

### Locality Heuristics

Locality heuristics are used to improve performance. Operating systems implement their own policies on where to store data in order to increase the spacing locality of files. For instance, storing files in the same directory in the same area of the disk. Some also periodically _defragment_ the disk by rewriting files to be contiguous.

## Directories: Naming Data

Can simply store name -> number mappings in a file that represents the directory. As a base case, you can just have a predefined number for the root directory. Linux's Fast File System (FFS) uses 2 as the root directory's number. Files in the same directory are often accessed together, so it is nice to store them in the same area of the disk so that caching can work its magic.

Although they are files, directories need their own API to prevent users from accidentally corrupting the directory structure. However, processes can still `read` directories to get a list of files in a directory, but it can be convinent to have a syscall to get the list of files in a directory (`getdents` in Linux).

### Internals

Although simple lists of file name number pairs works (and were used in early versions of Linux), modern file systems use more complex data structures to acccomodate large directories. Linux XFS, Microsoft NTFS, and Oracle ZFS all use trees to store directories.

XFS uses a B+ tree, and directory entries are stored in the first part of the directory file. The B+ tree's root node is stored in a known offset (`BTREE_ROOT_PTR`). The fixed-size internal and leaf nodes are stored after the root node, and the variable-size directory entries are stored at the start of the file. Starting from the root, each tree node includes pointers to where in the file its children are stored.

#### Links

Hard links are multiple names (and directory entries) for the same file on disk. OS uses reference counting to garbage collect files that are unlinked.

Soft (symbolic) links are files that directly map to the name of another file.

A consequence of hard links is that you can't keep file metadata in the directory entry

## Files: Finding Data

Files systems usually try to:

- Locate blocks of disk that belong to a file
- Maximize sequential data placement
- Provide efficient access to all blocks
- Minimize overhead for small files
- Be scalable for large files
- Provide a place for metadata

Some properties of file systems are:

- The *index structure*, which maps file numbers and offsets to storage blocks. Is usually a tree.
- The *free space map*, which keeps track of which blocks are free and which are in use. Is usually a bitmap.
- The *locality heuristic*, which is used to improve performance. For example, storing files in the same directory in the same area of the disk.

Although storage arranges data in *sectors* (magnectic disk) or *pages* (flash), file systems usually use *blocks* as the unit of allocation. Blocks are usually a power of two multiple of the sector or page size. For example, Linux uses 4KB blocks on 512 byte sectors. FAT and NTFS call blocks *clusters*. Similarly, file systems store data in variable length arrays of contiguous tracks called *extents*. NTFs calls them *runs*.


### Case Studies

### FAT

Very simple file system that uses a linked list to store the index structure. Still used in places like flash drives and SD cards, and most recent version (FAT32) supports volumes with up to 2^28 blocks, and files with up to 2^32 - 1 byes.

The FAT is an array of 32-bit entries that resides in a reserved area of the volume. Each file has a linked list of FAT entries that point to the blocks that make up the file. Directories map file names to the index of the first FAT entry for the file.

System can also use the FAT for free space tracking. OS scans for unused entries (0x00000000), and takes it out of the free list.

FAT usually uses simple allocation strategies like first-fit or next-fit. To deal with the resulting fragmentation, some implementations have a defragmentation tool that rewrites files to be contiguous. For example, the FAT degrafmenter in Windows XP tries to rewrite files to be within the same extent.

It is widely used because it is simple. In addition to simple storage technologies, even some applications use FAT to store data. For example, there is a FAT-like file system embedded in .doc files made in Microsoft Word 1997-2007.

**Drawbacks**:

- Usually poor locality of file data
- Poor random access due to nature of linked list
- Limited metadata and access control (no permissions, etc.)
- No hard links
- Limited file and volume sizes (volume max: 2^28 blocks, total max: 1TM)
- Lacks support for transactional updates

**Unix Fast File System (FFS)**: Uses a tree-based multi-level index, and many locality heuristics to achieve good spacial locality. Linux's ext2 and ext3 are based on FFS.

**NTFS**: Uses a tree-based structure that is more flexible than FFS's indexing scheme. Indexes variable sized extents* indead of individual blocks. NTFS is still used in Windows, and its techniques are used in many other modern file systems (ext4, XFS, HFS, HFS+).

**ZFS**: Uses **copy-on-write**, writing new versions of files to free disk space instead of overwriting old versions. This optimizes for reliability and write performance

