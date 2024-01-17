# Chapter 3 - The Programming Interface

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

What features/functions do we need an OS to provide for applications?

| Function                           | Description                                                                                                                                                                                               |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Process management                 | Create, destroy, and manage processes. This includes the ability to create new processes, terminate existing processes, wait for processes to complete, and send asynchronous notifications to processes. |
| Input/Output                       | Communicate with devices and files, as well as other processes.                                                                                                                                           |
| Thread management                  | Create, manage and destroy threads, aka tasks that share memory and other resources within a process.                                                                                                     |
| Memory management                  | Allocate and deallocate memory for processes.                                                                                                                                                             |
| File management                    | Create, delete, and manipulate files and directories. Users should be able to persist named data on disk.                                                                                                 |
| Networking and Distributed Systems | Processes should be able to communicate with other processes on different machines over the network. Processes should also be able to coordinate their actions, despite faults and delays.                |
| Graphics/Window Management         | Processes control pixels on their portion of the screen. Should utilize hardware acceleration to draw graphics quickly.                                                                                   |
| Authentication and Security        | Permissions system to control access to resources. Processes should be able to authenticate themselves to other processes and to the OS.                                                                  |

This chapter will focus on the first two.

### Design Choices

For any bit of functionality, there are several possible places it could be implemented in an OS.

| Component                                   | Description                                                              |
| ------------------------------------------- | ------------------------------------------------------------------------ |
| User-level programs                         | Programs for logging in and managing processes in both UNIX and Windows. |
| User-level library                          | User interface widgets in MacOS and Windows.                             |
| Kernel, accessed via system calls           | File system and network stack in UNIX and Windows.                       |
| Standalone server process invoked by kernel | Window manager in MacOS and Windows.                                     |

However, UNIX philosophy is to implement as much as possible in user-level programs and hardware, maintaining a "thin waist" in the system architecture. Same design principle behind network stack, the key interface between the highest and lowest levels of the system follows a very simple but powerful design. So long as a program complies to the system call interface, it can run on most UNIX systems.

However, some things really do need to go in particular places. We want the following:

- **Safety**: resource management and protection are the responsibility of the OS. Cannot do these things in user-level programs/libraries becaues they can be bypassed.
- **Reliability**: kernel programs aren't protected from each other, so keeping the kernel small and simple minimizes the chance of bugs. "If it can be done in user-level, it should be done in user-level". Extreme of this is a **micro-kernel architecture**, where the kernel is a small set of primitives for inter-process communication, and everything else is implemented in user-level processes/servers, accessed though user-level programs via inter-process communication.
- **Performance**: transferring control from user-level to kernel is expensive, so we want to minimize the number of system calls. Windows NT started out as a micro-kernel, but moved many responsibilities back into the kernel to improve performance.

## Process Management

### Windows Process Management

Has a syscall to create a process, and others for various process management operations. Turns out to be simple in theory, but complicated in practice. In an ideal world, it would be as simple as:

```c
boolean CreateProcess(char* prog, char* args);
```

- Create and init process control block (PCB) in kernel
- Create and init new address space
- Load program `prog` into address space
- Copy arguments `args` into memory in address space
- Inform scheduler new process is ready to run

However, the parent process may want to control various aspects of the child process runtime, so instead we have:

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

UNIX takes an approach that is complex in theory, but simple in practice. `CreateProcess` is replaced by two system calls:

```c
pid_t fork(void);
int exec(char* prog, char* args);
```

`fork` creates a copy of the calling process, called the child process. It is almost identical to the parent, except for the return value of `fork` and the pid. The child process has a new pid, and the return value of `fork` is 0. The parent process gets the pid of the child process as the return value of `fork`. The child process sets itself up the the same as the parent, and once the context is set, the child process calls `exec` to replace itself with a new program. `exec` loads the program into the address space, and starts it running.

#### fork

- Create and init process control block (PCB) in kernel
- Create and init new address space
- Copy parent address space to child address space
- Inherit execution context from parent (e.g., open files)
- Inform scheduler new process is ready to run

##### Browsers and fork

Browsers use new processes to create a new tab. When you click on a link, Chrome forks a process to fetch and render the web page at the link in a new tab. This also gives the browser seperation between tabs, so that if one tab crashes or contains anything harmful, the others are unaffected. Interestingly, Chrome on Windows doesn't even use `CreateProcess` for new tabs, and relies on a pool of pre-created processes.

#### exec

- Load program `prog` into address space
- Copy arguments `args` into memory in address space
- Init hardware context to start execution

Note that `exec` does not create a new process!

#### wait

Parent process can wait for child process to complete with `wait(pid)`. This is a blocking call, and returns the exit status of the child process. If the child process has not yet exited, the parent process is blocked until it does. If the child process has already exited, the parent process is not blocked.

`wait` is optional in UNIX, but a little ambiguous in terminology and use. Windows arguably did it better with `WaitForSingleObject`.

### Kernel Handles and Garbage Collection

UNIX processes call `exit` to terminate themselves. This releasing various resources, including user stack, heap, code segments. Has to be careful with PCB though. Even if the child exits, the parent still has access to the PCB and can still call wait. Thus, PCB can't be GC's until both parent and child have exited.

In general, both the Windows and UNIX kernels have various syscalls that return a handle to a kernel object (e.g. pid of a process, fd of an I/O device, etc.). Thense are **not** pointers, and are instead specific to a given process, and should be validated as such. The kernel maintains a reference count (important) for each object, and when the reference count reaches 0, the kernel can GC the object.

#### Signals

Sending async notifications to processes done with `signal`.

```c
typedef void (*sig_t) (int);
sig_t signal(int sig, sig_t func);
```

You can register a handler function for a given signal, and when the signal is sent to the process, the handler function is called. This is how `ctrl-c` works to stop a shell. `signal` returns the previous handler function, so you can chain them together. `sigaction` is a more modern version of `signal` that is more flexible.

```c
int sigaction(int sig,
              const struct sigaction *restrict act,
              struct sigaction *restrict oact);
```

## Input/Output

The key ideas behind UNIX I/O are:

- **Uniformity**: all I/O devices use the same set of system calls: `open`, `close`, `read`, `write` (and `seek`, `ioctl`). This makes it real easy to add new device support without changing the OS or system call interface.
- **Open before use**: before you can read or write to a device, you must open it, and then access it through the returned **file descriptor**. This allows the OS to check permissions and track which processes are using which devices. For convenience, UNIX starts shell applications with three open file descriptors: stdin, stdout, and stderr.
- **Byte-oriented**: all I/O devices are treated as a stream of bytes. This makes it easy to implement pipes, and allows for a uniform interface to devices that are not byte-oriented (e.g. terminals, printers, etc.).
- **Kernel-buffered reads**: the kernel buffers reads from devices to create a uniform interface for reading both streamed data sources and block devices. This also allows the kernel to implement read-ahead, which can improve performance by reading more data than requested and buffering it for future reads.
- **Kernel-buffered writes**: the kernel similarly buffers writes to devices. Before the buffer is full, the `write` syscall returns immediately after copying the data into the kernel buffer, allowing the data to be transferred to the device asynchronously. If the buffer is full then the `write` syscall blocks from the kernel until there is space in the buffer.
- **Explicit close**: the `close` syscall is used to release resources associated with a file descriptor. This allows the kernel to flush any buffered data to the device, and to release any other resources associated with the file descriptor, as well as decrementing the reference count on the file descriptor.

## Inter-Process Communication

### Pipes

A **UNIX pipe** is a kernel buffer with two file descriptors, one for reading and the other for writing. Data is read from the pipe in the same order as it is written, but the buffer allows the decoupling of the consumer and producer processes. The pipe terminates when the last process closes the file descriptors or exits. TCP sockets are similar to pipes.

### Replace file descriptors

`dup2(from, to)` replaces the file descriptor `to` with `from` in a child process. This is useful for redirecting stdin/stdout/stderr to files or pipes.

### Wait for multiple reads

In a client/server context, a server might have a pipe open to multiple clients, and want to read from whichever client has data available. `select` allows the server to wait for data to be available on any of the pipes, and then read from the pipe that has data available. This is a blocking call, and returns when data is available on one of the pipes.

```c
int select(int nfds, fd_set *readfds, fd_set *writefds,
           fd_set *exceptfds, struct timeval *timeout);
```

`select` is a bit of a pain to use, so `poll` was introduced as a more convenient alternative for synchronous I/O multiplexing.

```c
int poll(struct pollfd *fds, nfds_t nfds, int timeout);
```

## Case Study: The UNIX Shell

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

Since commands read and write to file descriptors, the programs are decoupled from their input and output. This allows for...

- **file of commands == program**: the shell can read commands from a file, and execute them as if they were typed in. Files can specify the _interpreter_ to use, which is a program that reads commands from a file and executes them. This is how shell scripts work. `#!/bin/sh` is an example.
- **input/output to file**: the shell can redirect input and output to files using `<` `>` respectively. Uses `dup2` to replace stdin/stdout/stderr with the file descriptors of the files to read/write to.
- **input/output to other programs**: the shell can redirect input and output to other programs using `|`. Uses `pipe` to create a pipe, and `dup2` to replace stdin/stdout/stderr with the file descriptors of the pipes to read/write to. This allows for chaining of programs together, where each program runs in parallel in its own process.

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

When the producer writes to the pipe (kernel buffer), they can do so entirely decoupled from the consumer. If the buffer is ever full, then writes are blocked by the producer until the consumer reads some data from the buffer. Similarly, if the buffer is ever empty, then reads are blocked by the consumer until the producer writes some data to the buffer.

WIn UNIX, when the producer is done it usually closes its side of the buffer. The consumer can then read until the buffer is empty, at which point the read syscall will hit EOF and return 0. The consumer can then close its side of the buffer, and the kernel will GC the buffer.

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

In client/server, there are two pipes, one for each direction of communication. To make a request, the client writes data into one pipe, and then reads data from the other. The server does the opposite, reading from the first pipe, validating and handling the request, and then writing to the second pipe the response.

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

Since both issue a write followed by a read, one could combine these into a single system call (at the expense of adding a system call...) in order to eliminate a context switch.

Furthermore, the client always needs to wait for the server, so an even further optimization that was done in microkernel Windows in the early 1990s is to donate the client processor to run server code, reducing latency. However, this requires that code and data for both client and server are in cache simultaneously.

Even further, on a multi-core system where the client and server have their own processors, the kernel can set up a shared memory region between them so that they can (safely) communicate directly without involving the kernel at all.

Often, the server process needs to select one of many processes to accept a request from (ie in a print queue). This can be done with the `select` system call.

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

- Many parts of the operating system depend on synchronization primitives for
  coordinating access to shared data structures with the kernel.
- The virtual memory system depends on low-level hardware support for address
  translation, support that is specific to a particular processor architecture.
- Both the file system and the virtual memory system share a common pool of blocks of
  physical memory. They also both depend on the disk device driver.
- The file system can depend on the network protocol stack if the disk is physically
  located on a different machine.

There is a fundamental tradeoff between maintainability and performance when it comes to designing kernels. Keeping functionality tightly coupled and integrated with kernel code makes it more performant, but also messy.

### Monolothic Kernels

Monolith kernels usually have everything tightly coupled within the kernel itself. Modules often have dependencies that span multiple other modules within the kernel. Not ALL functionality is built directly into the kernel, but much of it is.

Since OS designers are free to structure their code however they want with a monolith, there is a lot of variation between systems. However, two emerging patterns are usually present:

#### Hardware Abstraction Layer (HAL)

Portable interface to machine configuration and processor specific operations.

For an OS to be portable between processor families (ex ARM -> Intel or 32 -> 64 bit), there needs to be a layer over the processor specific code that handles things like context switches, interrupts, exceptions, and traps.

All of these hardware specific instructions need to be mapped to the platform independent "virtual" procedure. Porting an OS to a new platform is really just a matter of implementing this layer for a new architecture/hardwarep

##### Windows HAL

Windows uses two-pronged strategy for portability. Kernel is dynamically linked at boot time with a set of libaray routines that are specific to the hardware configuration. Also runs a different kernel binary accross different processor architectures, each of which contains conditional execution for closely related processor designs.

#### Dynamically Installed Device Drivers

Similar considerations for supporting wide variety of IO devices. **Dynamically loadable device drivers** are provided as the kernel is already running in order to handle new devices. Device manufacturers write drivers that follow a stardard interface for the OS, and these routines are called by the kernel when the device needs to be used.

When the OS boots, there are a small number of drivers that are already loaded, e.g. disk drivers. All devices physically attached to the computer have corresponding drivers usually bundled into a file that is stored along with the boot loader. When the OS starts up, it queries the I/O bus to find out what devices are attached, and then loads the corresponding drivers from disk. Any network-attached devices (like network printers) are loaded from over the internet.

Drivers have been found to be responsible for ~90% of OS crashes, and are a potential source of corruption, as well as a security risk. Mitigated with...

- **code inspection**: OS vendors typically require submission of drivers in advance for inspection and testing before they are allowed in the kernel.
- **bug tracking**: after every crash, OS collections info about system config and the current kernel stack. Sends this data to a central database for analysis.
- **user-level device drivers**: both Apple and Microsoft strongly encourage new device drivers to run at user-level. This prevents them from modifying and corrupting kernel data structures, but comes at a performance cost.
- **VM device drivers**: to handle old drivers that need to run in kernel mode, one approach is to run device driver inside guest OS. This way, bugs can only corrupt the guest OS. This is what Apple does with their Rosetta 2 emulator for running old Intel apps on new ARM Macs.
- **driver sandboxing**: to address performance issues with full virtualization, run drivers in a restricted execution environment that prevents them from accessing kernel data structures

### Microkernels

Run as much of the OS as possible in user mode. The window manager on most modern OS's is a good example of this.

The difference between micro and monolithic kernels is often transparent to application programs. User level libraries can either directly make requests to the server process, or make system calls that are then redirected by the kernel.

Generally, microkernels provide little benefit beyond the ease of development. The performance cost of context switching between user and kernel mode is high enough that most modern systems take on a hybrid approach.

## Exercises

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
