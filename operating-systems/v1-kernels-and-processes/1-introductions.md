# Introduction

## What is an Operating System?

**Referee.** Manages the resources of a computer shared between applications.

**Illusionist.** Makes the computer's resources appear to be dedicated to each application through abstraction.

**Glue.** Binds the hardware, software, and users through services that facilitate communication/sharing.

### Virtualization
- Creates the illusion of extra resources through abstraction.
- Some examples of virtualization are:
    - **Virtual Memory.** Creates the illusion of more memory than is physically available.
    - **Virtual Machines.** Creates the illusion of multiple computers on one computer.
    - **Virtual Processors.** Creates the illusion of multiple processors on one processor.

### Services

Services are provided by the operating system so applications can adapt to a single interface (like POSIX) instead of the hardware. Some examples of services are:

- **File System.** Create, delete, read, and write files through read, write, open, close, seek, etc.
- **Network.** Access the network through sockets with read, write, bind, and connect, etc.
- **Process Management.** Create and manage processes through fork, exec, wait, etc.
- **GUI** Windows, cut and paste, etc.


## Evolution of Operating Systems

**Reliability and Availability.** Does what it is expected without crashing. At scale, an OS must be invulnerable to failure, even in edge cases. Availability, the percentage of time a system is available, is influecned by **Mean Time To Failure** (MTTF) and **Mean Time To Repair** (MTTR). Increasing MTTF and decreasing MTTR increases availability.

**Security.** Prevents compromise from malicious users. Privacy is an aspect of security; data is only accessible to authorized users. Strong fault isolation is necessary for security.

**Portability.** Code can be run independently of the hardware. This is achieved through abstraction. **Abstract Virtual Machine** (AVM) is the interface between the OS and applicatons. **Hardware Abstract Layer** (HAL) is the interface between the OS and hardware.

**Performance.** Must be fast and efficient for users' sake. Performance is measured by...
- **overhead.** the cost of abstraction.
- **efficiency.** the ability to minimize overhead.
- **fairness.** the ability to allocate resources fairly.
- **response time.** the time between a request and a response.
- **throughput.** the number of requests per unit time.
- **predictability.** the ability to provide consistent performance.

**Adoption.** Also important

### Design Tradeoffs

Sometimes, it is better to sacrifice one aspect for another. For example, losing some performance to fit an interface. The tradeoff of performance and complexity is common.

Early (single user) operating systems would let the CPU wait idle for I/O. Later, when multi-user systems were introduced, the CPU would switch to another process while waiting for I/O. This is called **multiprogramming**. In a **bath operating system**, the CPU reads from a queue of jobs, loading, running, and unloading each job.

While one job is running, the OS may set up IO devices for another in the background through direct memory access (DMA). Through interrupts, the OS can then switch to the new job when it is ready. From the point of view of the original job, there was just a short delay. This is called **time sharing**.

When the OS directly controls multiple concurrent processes, (**multiprocessing**), debugging becomes difficult, and developers need to essentially stop the system to debug. **Virtualization** solves this problem by creating the illusion of multiple processors on one processor. This allows developers to debug one virtual processor while the others continue to run. Instead of debugging directly on the hardware, developers can debug on a virtual machine that is being run as an application.



# Ch. 1 Exercises

## Introduction

1. What is an example of an operating system as:
    - **Referee?**

    The OS manages the running processes and their access to resources.

    - **Illusionist?**

    The OS creates the illusion of dedicated resources through abstraction, like with malloc.

    - **Glue?**

The OS provides services like the file system and network.

2. What is the difference, if any, between the following terms:

    - **Reliability** vs. **availability?**

    Reliability is the ability to do what is expected without crashing. Availability is the percentage of time a system is available. More reliable systems have higher availability.

    - **Security** vs. **privacy?**

    Security is the ability to prevent compromise from malicious users. Privacy is the ability to prevent unauthorized users from accessing data.

    - **Security enforcement** vs. **security policy?**

    Security enforcement is the mechanism that prevents compromise. Security policy is the rules that define what is allowed and what is not.

    - **Throughput** vs. **response time?**

    Throughput is the number of requests per unit time. Response time is the time between a request and a response.

    - **Efficiency** vs. **overhead?**

    Efficiency is the ability to minimize overhead. Overhead is the cost of abstraction.

    - **Application programming interface (API)** vs. **abstract virtual machine (AVM)**?

        API is the interface between client applications and the software they're consuming. AVM is the interface between the OS and the applications running on it.

    - **Abstract virtual machine (AVM)** vs. **hardware abstraction layer (HAL)**?

        AVM is the interface between the OS and the applications running on it. HAL is the interface between the OS and the hardware.

    - **Proprietary** vs. **open operating system**?

        Proprietary operating systems are owned by a company and are not open source. Open operating systems are open source and free to use.

    - **Batch** vs. **interactive operating system**?

        Batch operating systems read from a queue of jobs, loading, running, and unloading each job. Interactive operating systems allow users to interact with the system while it is running.

    - **Host** vs. **guest operating system**?

        Host operating systems run on the hardware and typically manage guest operating systems. Guest operating systems run on top of the host operating system.

    - **Multiprogramming** vs. **multiprocessing**?

        Multiprogramming allows the CPU to switch to another process while waiting for I/O. Multiprocessing allows multiple processes to run concurrently.

3. Define the term, direct memory access (DMA).

DMA allows the OS to set up IO devices for another process in the background while the CPU is running another process. Through interrupts, the OS can then switch to the new process when it is ready.

4. Before there were operating systems, someone needed to develop solutions without being able to look them up! How would you have designed the first operating system?

Albeit relying on what I just read...

Users need to be able to execute arbitrary code on hardware. Although security is important, I won't focus on it for now.

First, I would need a way to load and run code. Assuming I can use a preexisting compiler (GCC?), I would first create a set of "kernel" modules that interact directly with the hardware. These modules would be written in C and assembly, and would cover the very basics of interacting with IO devices and any other hardware I need to control. In particular:

- CPU
- Disk Storage
- Memory Management
- Network
- Monitoring


Next, I would write a few services that users can interact with, as an interface to the above hardware drivers. In fact, users should NOT be able to interact with the preceding drivers directly, instead using the services I provide. These services would be written in C and assembly, and would cover the following:

- File System and Disk IO (read, write, open, close, seek, etc.)
- Memory Allocator (malloc, free, etc. to access heap memory)
- Network Communication (read, write, bind, connect, etc.)
- Process Management (fork, exec, wait, etc.)
- Terminal/Shell (stdin, stdout, stderr, etc.)
- GUI (windows, cut and paste, etc.)

My file system would be a simple tree structure, with directories and files. Similar to the UNIX filesystem, I would use file descriptors to refer to all IO devices, including files, directories, and network sockets. Currently open file descriptors would be stored in a table, and would be passed to the kernel modules to perform IO operations. Disk IO would be buffered in memory for writes to make logging efficient. Reading can be done directly from disk with our storage device drivers.

My memory allocator would be a basic implementation of malloc using a linked list. Simple compaction running periodically would be used, with heap sweeping on process termination. No virtual memory yet...

Network communication would be done entirely through reads/writes over sockets. TPC/IP would be used for communication, assuming a modern network stack is available. If not, then machines would need to be connected directly to each other and would read/write directly to each other's open sockets using whatever protocol is available (or a new one I would design).

Process management would be done through fork/exec/wait. I would need to implement a way to handle interrupts, so that processes can be interrupted and switched to when IO is ready. Callbacks would be used to handle this, where processes register a callback with the OS when blocked on IO. When the IO is ready, the OS would call the callback and the process would resume (or be added to the ready queue if it is not the highest priority process). An event driven model would be used for all IO, so that processes can be interrupted when IO is ready. Each event should contain the nessessary information to stop and resume work, and then I can just use a producer/consumer model to handle events off of an event queue. I would use a simple round robin scheduler to switch between processes, and would keep both a log of events, and streaming statistics to try and schedule events fairly. Although limited, this would allow for some concurrency since processes can be interrupted while waiting for IO.


## System Design

5. Suppose a computer system and all of its applications were completely bug-free and everyone in the world were completely honest and trustworthy. In other words, we need not consider fault isolation.
    - **How should an operating system allocate time on the processor?**

    Round robin

    - **How should the operating system allocate physical memory to applications?**

    Ideally, each application would have its own memory space. This requires implementing some sort of virtual memory abstraction.

    - **How should the operating system allocate its disk space?**

    Applications should access disk through the file system, which has an interface for creating, deleting, reading, and writing files. The OS keeps a table of open files, and uses this table to perform IO operations on files in a consistent/safe way. Simply blocking access to files while they are being written to would be sufficient, although more complex buffering and locking could be used to improve performance.

6. Now suppose the computer system needs to support fault isolation. What hardware and/or operating support do you think would be needed to do the following?
    - **Protect an application’s data structures in memory from being corrupted by other applications.**
    - **Protecting one user’s disk files from being accessed or corrupted by another user.**
    - **Protecting the network from a virus trying to use your computer to send spam.**

    Permissions ^^^ and virtualization. Each process has its own memory space, and each user has its own file system. The OS can then use permissions to control access to resources for individual users. Network access should be mutually consentual, and the OS should prevent unauthorized access to the network.

7. How should an operating system support communication between applications?
    - **Through the file system?**

    Each application can independently request access to a file, getting an entry on the currently open file table. If two processes want to read from the same file this is fine, but writing to the same file should be prevented from being overleaved. There should be multiple levels of locking, so that processes can lock a file to keep it for themselves, to prevent writes but allow reads, to prevent reads but allow writes, to only allow atomic reads/writes, but allow concurrent ownership, etc.

    - **Through messages passed between applications?**

    Similar to network communication and file io, should be able to read/write to sockets. Pipes could be used to pass messages between processes, and io streams could be used to compose programs together.

    - **Through regions of memory shared between the applications?**

    Reentrant locking service that thinly wraps a piece of shared memory owned in the kernel.

Essentially all of the above, but programmers need to understand the tradeoffs and correcness of each approach.

8. How would you design combined hardware and software support to provide the illusion of a nearly infinite virtual memory on a limited amount of physical memory?

Analogy of cache to memory, we would use main memory as a temporary space to hold the data of running processes. Then, when another process needs time on the CPU, the context of main memory is switched to another process, and the previously occupying memory is loaded to disk.

The process management service would handle this "paging" of memory by keeping a table of processes and the location and metadata for their memory. As tasks are pulled from the job queue, they are loaded into memory and added to the ready queue. When a process is blocked on IO, the OS can switch to another process and load the blocked process's memory to disk. When the process is ready again, the OS can load the process's memory from disk and resume execution.

9. How would you design a system to run an entire operating system as an application on top of another operating system?

The hardware modules that the host OS run on all follow an interface, so by mocking the interface of these hardware systems, we can simulate the hardware. Then, simply running the guest OS on top of this simulated hardware would allow us to run the guest OS as an application on top of the host OS. This should all be done in an isolated environment, so that the guest OS cannot access the host resources directly.

10. How would you design a system to update complex data structures on disk in a consistent fashion despite machine crashes?

I would use a write ahead log (buffered in memory for high throughput events, but also flushed to disk in the background as often as possible to aid in recovery) that keeps track of all disk writes. Each record in the log would correspond to an event that happend regarding our data structure, and each event would have an id. We keep track of an atomic counter that keeps track of the last event executed on our structure. In the event of a crash, we can simply replay the log from the last event executed to the end of the log, and our data structure will be in a consistent state. We can also use this log to recover from a crash during a write, by simply replaying the log from the beginning.

11. Society itself must grapple with managing resources. What ways do governments use to allocate resources, isolate misuse, and foster sharing in real life?

Taxes, laws, and regulations. Taxes are used to allocate resources, and laws are used to prevent misuse and foster sharing. For example, public services (firefighters) are funded by taxes, and laws are *supposed* to help ensure people can faily access these services.

12. Suppose you were tasked with designing and implementing an ultra-reliable and ultra-available operating system. What techniques would you use? What tests, if any, might be sufficient to convince you of the system’s reliability, short of handing your operating system to millions of users to serve as beta testers?

Extensive testing like in other forms of software (unit, integration, fuzzing, fault injection), as well as monitoring and telemetry of real devices. Formal verification would be nice, but is probably not feasible. A microkernel would be a good start, since it would allow me to isolate "trusted" code.

13. For the computer you are currently using, how should the operating system designers prioritize among reliability, security, portability, performance, and adoption? Explain why.

As a user of a macbook pro, security, performance, and adoption are extremely important. However, as a developer it would be nice to also have a portable and (less importantly) a reliable system. Something that I think the OS designers were less concerned about is portability (Apple hardware only), but this is also a question of adoption of the Sillicon based chips in Apple's hardware.