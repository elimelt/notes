# File Systems: Introduction and Overview

What do we need in a filesystem?

- **Reliability**
- **Large capacity and low cost**
- **High performance**
- **Named data**
- **Controlled sharing**

### Nonvolatile Storage

As opposed to DRAM, nonvolatile storage is persistent. It is also generally cheaper and can have higher capacity. However, it is also orders of magnitude (~5 in the case of magnetic disk accesses) slower than DRAM. Current nonvolatile storage technologies don't allow random access to words of data, but instead require that data be read and written in blocks of a fixed size (e.g. 512 bytes).

## The File System Abstraction

A **File** is a named collection of data in a file system. Files are made of metadata and data. I won't go into what those are. Files can be "*executable*", and executable files on Linux begin with a magic number that tells the OS how to run the file. Scripts can also be executable, and they begin with a "shebang" (`#!`), following by the interpreter which tells the OS how to run the script.

Traditional files can be thought of as a signle logical stream of bytes. However, MacOS's Extended File System (HFS+) and Windows NTFS support multiple streams (forks) for a signle file. In these contexts, you need to specify which stream you want to read from/write to in the corresponding system calls.

I won't define them, but you should also know and understand the following terms:

- **Directory**
- **Root Directory**
- **Home Directory**
- **Current Working Directory**
- **Path**
- **Absolute Path**
- **Relative Path**

#### Links

The mapping between a name and file is called a **hard link**. File systems that allow multiple hard links aren't a tree, and are instead usually a directed acyclic graph (DAG). A **symbolic link** is a mapping from a name to another file name. These are useful since they allow you to reference files that are stored on other systems/volumes. Some OS's support features managed outside of the file system. Windows has **shortcuts**, which are really just files that Windows recognizes and redirects from. MacOS has **aliases**, which are similar to symbolic links, but also refactor themselves when the target file is moved.

#### Volumes

A **volume** is a collection of physical storage resources that form a logical storage device. In the simplest case, a volume is a single disk. However, a disk can be partitioned into multiple volumes, and a single volume can be made of multiple disks.∂