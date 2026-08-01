---
title: Syscall API Reference
aliases:
  - operating-systems/v1-kernels-and-processes/3-the-programming-interface
category: Operating Systems
tags:
  - operating systems
  - syscall
  - process management
  - i/o operations
date: 2024-01-10
updated: 2026-07-30
status: evergreen
description: Chapter notes on OSPP chapter 3. The UNIX process management and I/O syscall interface, how fork/exec/wait compare to Windows CreateProcess, pipes and dup2 for inter-process communication, and where OS functionality should live (monolithic vs. microkernel).
sources:
  - title: "Operating Systems: Principles and Practice (2nd ed.), Anderson and Dahlin, chapter 3"
    url: https://ospp.cs.washington.edu/
    type: textbook
---

## Purpose

Notes on chapter 3 of [Operating Systems: Principles and Practice](https://ospp.cs.washington.edu/). The chapter covers the interface the OS exposes to applications, with a focus on process management and I/O in UNIX. The syscall tables up front are the reference I come back to; the rest explains why the interface is shaped the way it is.

## Syscall API Reference

### Creating and managing processes

| Function                  | Description                                                                                                     |
| ------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `fork()`                  | Create a child process as a clone of the current process. The `fork` call returns to both the parent and child. |
| `exec(prog, args)`        | Run the application `prog` in the current process.                                                              |
| `exit()`                  | Tell the kernel the current process is complete, and its data structures should be garbage collected.           |
| `wait(processID)`         | Pause until the child process has exited.                                                                       |
| `signal(processID, type)` | Send an interrupt of a specified type to a process.                                                             |

### I/O operations

| Function                                 | Description                                                                                                                                                                                           |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fileDesc open(name)`                    | Open a file, channel, or hardware device, specified by `name`; returns a file descriptor that can be used by other calls.                                                                             |
| `pipe(fileDesc[2])`                      | Create a one-directional pipe for communication between two processes. `pipe` returns two file descriptors, one for reading and one for writing.                                                      |
| `dup2(fromFileDesc, toFileDesc)`         | Replace the `toFileDesc` file descriptor with a copy of `fromFileDesc`. Used for replacing `stdin` or `stdout` or both in a child process before calling `exec`.                                      |
| `int read(fileDesc, buffer, size)`       | Read up to `size` bytes into `buffer`, from the file, channel, or device. `read` returns the number of bytes actually read.                                                                           |
| `int write(fileDesc, buffer, size)`      | Analogous to `read`, write up to `size` bytes into kernel output buffer for a file, channel, or device. `write` normally returns immediately but may stall if there is no space in the kernel buffer. |
| `fileDesc select(fileDesc[], arraySize)` | Return when any of the file descriptors in the array `fileDesc[]` have data available to be read. Returns the file descriptor that has data pending.                                                  |
| `close(fileDescriptor)`                  | Tell the kernel the process is done with this file, channel, or device.                                                                                                                               |

## Overview

What does an OS need to provide for applications?

| Function                           | Description                                                                                                                                                                                               |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Process management                 | Create, destroy, and manage processes. This includes the ability to create new processes, terminate existing processes, wait for processes to complete, and send asynchronous notifications to processes. |
| Input/Output                       | Communicate with devices and files, as well as other processes.                                                                                                                                           |
| Thread management                  | Create, manage and destroy threads, aka tasks that share memory and other resources within a process.                                                                                                     |
| Memory management                  | Allocate and deallocate memory for processes.                                                                                                                                                             |
| File management                    | Create, delete, and manipulate files and directories. Users should be able to persist named data on disk.                                                                                                 |
| Networking and Distributed Systems | Processes should be able to communicate with other processes on different machines over the network. Processes should also be able to coordinate their actions, despite faults and delays.                |
| Graphics/Window Management         | Processes control pixels on their portion of the screen. Should utilize hardware acceleration to draw graphics quickly.                                                                                   |
| Authentication and Security        | Permissions system to control access to resources. Processes should be able to authenticate themselves to other processes and to the OS.                                                                  |

This chapter focuses on the first two.

### Design Choices

Any given piece of functionality could live in several places:

| Component                                   | Description                                                              |
| ------------------------------------------- | ------------------------------------------------------------------------ |
| User-level programs                         | Programs for logging in and managing processes in both UNIX and Windows. |
| User-level library                          | User interface widgets in MacOS and Windows.                             |
| Kernel, accessed via system calls           | File system and network stack in UNIX and Windows.                       |
| Standalone server process invoked by kernel | Window manager in MacOS and Windows.                                     |

The UNIX philosophy is to implement as much as possible in user-level programs, keeping a "thin waist" in the system architecture. The network stack follows the same design principle. The key interface between the highest and lowest levels of the system stays simple, and any program that complies with the syscall interface runs on most UNIX systems.

Some things do need to go in particular places, though:

- **Safety**: resource management and protection belong to the OS. They cannot live in user-level programs or libraries because they could be bypassed there.
- **Reliability**: kernel programs are not protected from each other, so a small and simple kernel means fewer bugs. If it can be done at user level, it should be done at user level. The extreme version of this is the **micro-kernel architecture**, where the kernel is a small set of primitives for inter-process communication, and everything else runs in user-level server processes.
- **Performance**: transferring control between user level and the kernel is expensive, so the design should minimize syscall crossings. Windows NT started out as a microkernel and moved many responsibilities back into the kernel for performance.

## Process Management

### Windows Process Management

Windows has a syscall to create a process, plus others for various process management operations. The idea sounds simple. In an ideal world it would be:

```c
boolean CreateProcess(char* prog, char* args);
```

which would:

- Create and init a process control block (PCB) in the kernel
- Create and init a new address space
- Load program `prog` into the address space
- Copy arguments `args` into memory in the address space
- Inform the scheduler the new process is ready to run

In practice the parent often wants to control aspects of the child's runtime, so the real signature carries ten parameters:

```c
 if (!CreateProcess(NULL, // No module name (use command line)
     argv[1], // Command line
     NULL, // Process handle not inheritable
     NULL, // Thread handle not inheritable
     FALSE, // Set handle inheritance to FALSE
     0, // No creation flags
     NULL, // Use parent's environment block
     NULL, // Use parent's starting directory
     &si, // Pointer to STARTUPINFO structure
     &pi ) // Pointer to PROCESS_INFORMATION structure
 )
```

### UNIX Process Management

UNIX splits process creation into two syscalls:

```c
pid_t fork(void);
int exec(char* prog, char* args);
```

`fork` creates a copy of the calling process, the child. The child is almost identical to the parent, except for its pid and the return value of `fork`: the child sees 0, the parent sees the child's pid. The child inherits the parent's context, adjusts whatever it needs (open files, redirections), and then calls `exec` to replace itself with a new program. This split is what makes the shell's redirection and piping tricks possible, since the child gets a window to rewire its own file descriptors before the new program starts.

#### fork

- Create and init a process control block (PCB) in the kernel
- Create and init a new address space
- Copy the parent's address space into it
- Inherit the parent's execution context (e.g., open files)
- Inform the scheduler the new process is ready to run

##### Browsers and fork

Chrome creates a new process per tab, which isolates tabs from each other: a crashing or malicious page takes down only its own tab. Chrome on Windows does not even use `CreateProcess` for new tabs directly, it draws from a pool of pre-created processes.

#### exec

- Load program `prog` into the address space
- Copy arguments `args` into memory in the address space
- Init the hardware context to start execution

Note that `exec` does not create a new process!

#### wait

The parent can wait for a child to complete with `wait(pid)`. The call blocks until the child exits and returns its exit status, or returns immediately if the child already exited. `wait` is optional in UNIX, and the naming is a little ambiguous. Windows arguably did this better with `WaitForSingleObject`.

### Kernel Handles and Garbage Collection

A UNIX process terminates itself by calling `exit`, which releases its user stack, heap, and code segments. The PCB needs more care. Even after the child exits, the parent may still call `wait` on it, so the PCB cannot be reclaimed until both parent and child have exited.

More generally, syscalls in both Windows and UNIX return handles to kernel objects (a pid, a file descriptor, and so on). Handles are process-local identifiers rather than pointers, and the kernel validates them on every use. The kernel keeps a reference count per object and garbage collects the object when the count hits zero.

#### Signals

Asynchronous notifications between processes go through `signal`:

```c
typedef void (*sig_t) (int);
sig_t signal(int sig, sig_t func);
```

You register a handler function for a signal type, and the handler runs when that signal arrives. This is how `ctrl-c` stops a program in a shell. `signal` returns the previous handler, so handlers can be chained. `sigaction` is the more modern and flexible replacement:

```c
int sigaction(int sig,
              const struct sigaction *restrict act,
              struct sigaction *restrict oact);
```

## Input/Output

The key ideas behind UNIX I/O:

- **Uniformity**: all I/O devices use the same set of system calls: `open`, `close`, `read`, `write` (and `seek`, `ioctl`). Adding support for a new device requires no change to the OS interface.
- **Open before use**: you must open a device before reading or writing it, and you access it through the returned **file descriptor**. This lets the OS check permissions and track which processes use which devices. For convenience, UNIX starts shell applications with three open file descriptors: stdin, stdout, and stderr.
- **Byte-oriented**: every device is treated as a stream of bytes. This makes pipes easy to implement and gives a uniform interface even to devices that are not naturally byte-oriented.
- **Kernel-buffered reads**: the kernel buffers reads so streamed sources and block devices look the same. Buffering also enables read-ahead, where the kernel fetches more than was asked for and serves future reads from memory.
- **Kernel-buffered writes**: writes are buffered too. `write` returns as soon as the data is copied into the kernel buffer and the transfer happens asynchronously. If the buffer is full, `write` blocks until space opens up.
- **Explicit close**: `close` releases the resources tied to a file descriptor, flushes any buffered writes, and decrements the descriptor's reference count.

## Inter-Process Communication

### Pipes

A **UNIX pipe** is a kernel buffer with two file descriptors, one for reading and one for writing. Data comes out in the order it went in, and the buffer decouples producer from consumer. The pipe terminates when the last process closes its descriptors or exits. TCP sockets behave much like pipes between machines.

### Replace file descriptors

`dup2(from, to)` replaces file descriptor `to` with a copy of `from`. A child process calls it before `exec` to redirect its stdin, stdout, or stderr to a file or pipe.

### Wait for multiple reads

A server with pipes open to multiple clients wants to read from whichever client has data ready. `select` blocks until data is available on one of a set of descriptors, then returns which one:

```c
int select(int nfds, fd_set *readfds, fd_set *writefds,
           fd_set *exceptfds, struct timeval *timeout);
```

`select` is a pain to use, so `poll` came later as a more convenient interface for synchronous I/O multiplexing:

```c
int poll(struct pollfd *fds, nfds_t nfds, int timeout);
```

## Case Study: The UNIX Shell

The core of a shell is a fork/exec/wait loop:

```c
//                    [!!!] pseudocode [!!!]
main() {
    char *prog = NULL;
    char **args = NULL;
    // Read the input a line at a time, and parse each line into the program
    // name and its arguments. End loop if we've reached the end of the input.
    while (readAndParseCmdLine(&prog, &args)) {
        // Create a child process to run the command.
        int child_pid = fork();
        if (child_pid == 0) {
            // I'm the child process.
            // Run program with the parent's input and output.
            exec(prog, args);
            // NOT REACHED
        } else {
            // I'm the parent; wait for the child to complete.
            wait(child_pid);
            return 0;
        }
    }
}
```

Since commands read and write file descriptors, programs are decoupled from their input and output. That buys:

- **A file of commands is a program**: the shell can read commands from a file and execute them as if typed. A script names its _interpreter_ on the first line with a shebang, e.g. `#!/bin/sh`.
- **Input/output to files**: `<` and `>` redirect stdin and stdout. The shell implements them with `dup2` in the child before `exec`.
- **Input/output to other programs**: `|` chains programs. The shell creates a `pipe`, wires it up with `dup2`, and each program in the chain runs in parallel in its own process.

## Case Study: Inter-Process Communication

### Producer/Consumer

```txt

    Producer                            Consumer
    --------                            --------
       |                                   | ^
       | write                        read | |
       |                                   | |
       |                                   v |
       |
       |                                    ^
  _____|____________________________________|_________________
KERNEL |                                    |
       |                                    |
       |       _____________                |
       +-------|||||||||||||----------------+
               _____________
             Pipe/Kernel Buffer
```

The producer writes to the pipe without any coordination with the consumer. If the buffer fills, the producer's writes block until the consumer drains some data. If the buffer empties, the consumer's reads block until the producer writes more.

In UNIX, the producer closes its side of the pipe when done. The consumer reads until the buffer drains, at which point `read` hits EOF and returns 0. The consumer closes its side and the kernel garbage collects the buffer.

### Client/Server

```txt
         Client                              Server
       ----------                          ----------
       |      ^ |                             |     ^ |
     write    | |                             |     | |
       |      | |                       write |     | |
       |      | v read                        |     | v read
User   |       ^                              |      ^
_______|_______|______________________________|______|__________
Kernel |       |                              |      |
       |       |                              |      |
       |       |       _______________        |      |
       |       +-------||||||||||||||| <------+      |
       |               ---------------               |
       |                                             |
       |               _______________               |
       +-------------->|||||||||||||||---------------+
                       ---------------
                       Pipe/Kernel Buffer
```

Client/server uses two pipes, one per direction. The client writes a request into one pipe and reads the response from the other. The server reads a request, validates and handles it, and writes the response back.

```c
//                   [!!!] pseudocode [!!!]

Client:
    char request[RequestSize];
    char reply[ReplySize];

    // ..compute..

    // Put the request into the buffer.
    // Send the buffer to the server.
    write(output, request, RequestSize);

    // Wait for response.
    read(input, reply, ReplySize);

    // ..compute..

Server:
    char request[RequestSize];
    char reply[ReplySize];

    // Loop waiting for requests.
    while (1) {
        // Read incoming command.
        read(input, request, RequestSize);

        // Do operation.

        // Send result.
        write(output, reply, ReplySize);
    }
```

#### Streamlining Client/Server Communication

Both sides issue a write followed by a read, so the two could be combined into a single system call, eliminating a context switch at the cost of widening the syscall interface. The client always waits on the server, so a further optimization, done in microkernel Windows in the early 1990s, is to donate the client's processor to run server code, reducing latency. This only pays off when the code and data of both client and server fit in cache simultaneously. On a multicore system where client and server have their own processors, the kernel can instead set up a shared memory region and let them communicate without involving the kernel at all.

A server often needs to accept a request from any of many clients (a print queue, for example), which is what `select` is for:

```c
Server:
    char request[RequestSize];
    char reply[ReplySize];
    FileDescriptor clientInput[NumClients];
    FileDescriptor clientOutput[NumClients];
    // Loop waiting for a request from any client.
    while (fd = select(clientInput, NumClients)) {
        // Read incoming command from a specific client.
        read(clientInput[fd], request, RequestSize);
        // Do operation.
        // Send result.
        write(clientOutput[fd], reply, ReplySize);
    }
```

## Operating System Structures

Kernel subsystems lean on each other heavily:

- Much of the OS depends on synchronization primitives for coordinating access to shared kernel data structures.
- The virtual memory system depends on processor-specific hardware support for address translation.
- The file system and virtual memory system share a pool of physical memory blocks, and both depend on the disk device driver.
- The file system can depend on the network stack when the disk lives on another machine.

There is a real tradeoff between maintainability and performance in kernel design. Tightly coupling functionality inside the kernel is fast and messy.

### Monolithic Kernels

Monolithic kernels keep most functionality inside the kernel, with modules that depend on each other freely. Designers structure the code however they want, so systems vary a lot, but two patterns show up consistently.

#### Hardware Abstraction Layer (HAL)

A portable interface to machine configuration and processor-specific operations. For an OS to move between processor families (ARM to Intel, 32 to 64 bit), the processor-specific pieces (context switches, interrupts, exceptions, traps) sit behind platform-independent "virtual" procedures. Porting the OS then means implementing the HAL for the new architecture.

##### Windows HAL

Windows uses a two-pronged strategy. The kernel is dynamically linked at boot time with library routines specific to the hardware configuration, and Microsoft ships a different kernel binary per processor architecture, each with conditional execution for closely related processor designs.

#### Dynamically Installed Device Drivers

The same consideration applies to the huge variety of I/O devices. **Dynamically loadable device drivers** get added to a running kernel. Device manufacturers write drivers against a standard OS interface, and the kernel calls those routines when the device is used.

At boot, a small set of drivers is already present (the disk driver, at minimum). Drivers for physically attached devices are bundled in a file stored with the bootloader; the OS queries the I/O bus at startup to find attached devices and loads the matching drivers from disk. Drivers for network-attached devices load over the network.

Drivers are a huge reliability and security liability. Anderson and Dahlin report drivers cause roughly 90% of OS crashes. Mitigations:

- **Code inspection**: OS vendors require drivers to be submitted for inspection and testing before they are allowed in the kernel.
- **Bug tracking**: after every crash, the OS collects the system configuration and kernel stack and ships it to a central database for analysis.
- **User-level device drivers**: Apple and Microsoft push new drivers to run at user level, which keeps them away from kernel data structures at some performance cost.
- **VM device drivers**: old drivers that must run in kernel mode can run inside a guest OS, so their bugs only corrupt the guest.
- **Driver sandboxing**: run drivers in a restricted execution environment inside the kernel, cheaper than full virtualization.

### Microkernels

Run as much of the OS as possible in user mode; the window manager on most modern systems is the familiar example. The difference between micro and monolithic kernels is mostly transparent to applications, since user-level libraries either call a server process directly or make syscalls that the kernel redirects. In practice, the context switching cost between user and kernel mode is high enough that most modern systems settle on a hybrid.

## Exercises

Unanswered chapter exercises, kept here for practice.

1. Can UNIX fork return an error? Why or why not?

2. Can UNIX exec return an error? Why or why not?

3. What happens if we run the following program on UNIX?

   ```c
   main() {
       while (fork() >= 0)
           ;
   }
   ```

4. Explain what must happen for UNIX wait to return immediately (and successfully).

5. Suppose you were the instructor of a very large introductory programming class. Explain (in English) how you would use UNIX system calls to automate testing of submitted homework assignments.

6. What happens if you run "exec csh" in a UNIX shell? Why?

7. What happens if you run "exec ls" in a UNIX shell? Why?

8. How many processes are created if the following program is run?

   ```c
   main(int argc, char ** argv) {
       forkthem(5);
   }
   void forkthem(int n) {
       if (n > 0) {
           fork();
           forkthem(n-1);
       }
   }
   ```
9. Consider the following program:

   ```c
   main (int argc, char ** argv) {
       int child = fork();
       int x = 5;

       if (child == 0) {
           x += 5;
       } else {
           child = fork();
           x += 10;
           if(child) {
               x += 5;
           }
       }
   }
   ```

   How many different copies of the variable x are there? What are their values when their process finishes?
10. What is the output of the following programs? (Please try to solve the problem without compiling and running the programs.)

    - Program 1:

      ```c
      main() {
          int val = 5;
          int pid;

          if (pid = fork())
              wait(pid);
          val++;
          printf("%d\n", val);
          return val;
      }
      ```

    - Program 2:
      ```c
      main() {
          int val = 5;
          int pid;
          if (pid = fork())
              wait(pid);
          else
              exit(val);
          val++;
          printf("%d\n", val);
          return val;
      }
      ```
11. Implement a simple Linux shell in C capable of executing a sequence of programs that communicate through a pipe. For example, if the user types ls | wc, your program should fork off the two programs, which together will calculate the number of files in the directory. For this, you will need to use several of the Linux system calls described in this chapter: fork, exec, open, close, pipe, dup2, and wait. Note: You will to replace stdin and stdout in the child process with the pipe file descriptors; that is the role of dup2.
12. Extend the shell implemented above to support foreground and background tasks, as well as job control: suspend, resume, and kill.

## Related notes

- [[systems/operating-systems/v1-kernels-and-processes/2-the-kernel-abstraction|the kernel abstraction]]
- [[systems/operating-systems/lecture-notes/handle-tables|Handle Tables]]
- [[systems/operating-systems/lecture-notes/components|Components of an OS]]
- [[systems/research/unix-timesharing-system|The Unix Timesharing System]]
- [[systems/operating-systems/lecture-notes/windows-objects-handles-refcounts|Objects Handles and Reference Counts]]
- [[systems/networks/sockets|Socket Reference]]
