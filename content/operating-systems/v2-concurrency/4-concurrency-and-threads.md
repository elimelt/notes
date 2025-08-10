---
title: Concurrency and Threads
category: Operating Systems
tags: concurrency, threads, operating systems, I/O devices, CPU utilization, parallel processing
description: Covers the implementation of kernel-level threads, including thread abstraction, life cycle, and data structures. Discusses use cases for threads, such as improving CPU utilization and enabling parallel processing. Examines POSIX thread API and alternatives to threads, including asynchronous I/O and event-driven programming.
---

# Chapter 4: Concurrency and Threads

## 4.1 Thread Use Cases

- **Program structure: expressing logically concurrent tasks.** Many applications are naturally concurrent, and using threads lets you naturally model this concurrency in your code.
- **Responsiveness: shifting work to run in the background.** You can use threads to move slow or blocking operations to a background thread, so that the main event loop of your application stays responsive to users.
- **Performance: exploiting multiple processors.** Do more work in the same amount of time.
- **Performance: managing I/O devices.** Idle CPUs are a waste of resources. If one thread is blocked waiting for I/O, another thread can run on the CPU instead.

Processors are much faster than I/O devices. Latency for disk I/O is measured in milliseconds, which is enough for a CPU to execute millions of instructions. Furthermore, unpredictable latency with I/O like user input or network requests make it nessary to have non-blocking I/O.

A common pattern in I/O bound applications is to have multiple threads fetching different quality or levels of resources simultaneously. For example, a media player might have one thread fetching the highest quality video, another fetching the highest quality audio, and a third fetching the lowest quality video for previewing.

#### Threads vs. Processes

##### Some scenarios:

- **One thread per process.** One sequence of instructions, executing from beginning to end. Kernel runs those instructions in user mode. The process uses system calls to request privileged operations.
- **Many threads per process.** Several concurrent threads, each executing within the restricted rights of the process. A subset of the process's threads running, while rest are suspended. Any thread running in a process can make system calls into the kernel, blocking itself but no other threads. When the processor gets an I/O interrupt, it preempts one of the running threads so the kernel can run the interrupt handler; when the handler finishes, the kernel resumes that thread.
- **Many single-threaded processes.** Each process looks like a thread: a separate sequence of instructions, executing sometimes in the kernel and sometimes at user level. Concurrent processes can have concurrent system calls, even parallel on multiprocessor systems.
- **Many kernel threads.** The operating system kernel itself implements the thread abstraction for its own use. Runs seperate threads, each of which are running in kernel mode.

## 4.2 Thread Abstraction

- **Single execution sequence.** Each thread has its own set of instructions it is executing.
- **Seperately schedulable.** The kernel can run, suspend, and resume each thread independently of the others.

### 4.2.1 Running, Suspending, and Resuming Threads

Threads provide the illusion of infinite processors. OS uses a _thread scheduler_ to switch between threads to run. How threads are interleaved and scheduled should be transparent to the application.

#### Cooperative vs. preemptive multithreading

Early versions of MacOS used cooperative multithreading, where the kernel would only switch threads when the running thread made a system call relinquishing control. This is a bad idea because a thread can hog the CPU and starve other threads.

Modern operating systems use preemptive multithreading, where the kernel can preempt a thread at any time, even in the middle of a single instruction.

### 4.2.2 Why "Unpredictable Speed"?

**Always avoid** reasoning about the relative speed of threads when trying to evaluate the correctness of your code. The speed of threads is unpredictable for many reasons.

## 4.3 POSIX Thread API

| Function Signature                                                                                          | Description                   |
| ----------------------------------------------------------------------------------------------------------- | ----------------------------- |
| `pthread_create(pthread_t *thread, const pthread_attr_t *attr, void *(*start_routine) (void *), void *arg)` | Create a new thread.          |
| `pthread_join(pthread_t thread, void **retval)`                                                             | Wait for a thread to finish.  |
| `pthread_detach(pthread_t thread)`                                                                          | Detach a thread.              |
| `pthread_self()`                                                                                            | Get the current thread.       |
| `pthread_exit(void *retval)`                                                                                | Terminate the current thread. |
| `pthread_cancel(pthread_t thread)`                                                                          | Cancel a thread.              |

Threads enable **asynchronous procedure calls**, which means the function called runs in the background

```c
 #include <stdio.h>
 #include "thread.h"
 static void go(int n);
 #define NTHREADS 10
 static thread_t threads[NTHREADS];

 int main(int argc, char **argv) {
    int i;
    long exitValue;
    for (i = 0; i < NTHREADS; i++){
       pthread_create(&(threads[i]), &go, i);
    }

    for (i = 0; i < NTHREADS; i++){
        exitValue = pthread_join(threads[i]);
        printf("Thread %d returned with %ld\n",
        i, exitValue);
    }

    printf("Main thread done.\n");
    return 0;
 }

 void go(int n) {
    printf("Hello from thread %d\n", n);
    pthread_exit(100 + n);
    // Not reached
 }
```

### Fork-Join Parallelism

Example program to zero a block of memory using multiple threads. In operating systems, often times need to zero a block of memory (like after a process exits to prevent leaking information). This is a good example of a task that can be parallelized.

For reference, zeroing 1 GB of memory takes about 50 ms on modern hardware. The overhead of creating a thread however is on the order of 10 microseconds, so it can be worth it to parallelize.

```c
 // To pass two arguments, we need a struct to hold them.
 typedef struct params {
    unsigned char *buffer;
    int length;
 };

 #define NTHREADS 10
 void go (struct params *p) {
    memset(p->buffer, 0, p->length);
 }
 // Zero a block of memory using multiple threads.
 void blockzero (unsigned char *p, int length) {
    int i;
    thread_t threads[NTHREADS];
    struct params params[NTHREADS];

    // For simplicity, assumes length is divisible by NTHREADS.
    assert((length % NTHREADS) == 0);

    for (i = 0; i < NTHREADS; i++) {
        params[i].buffer = p + i * length/NTHREADS;
        params[i].length = length/NTHREADS;
        thread_create_p(&(threads[i]), &go, &params[i]);
    }

    for (i = 0; i < NTHREADS; i++)
        thread_join(threads[i]);
 }
```

You can also lazily zero out blocks of memory with a background thread that zeros out memory while another process runs. Then, if you need to reuse the memory, you can just call join on the background thread.

## Thread Data Structes and Life Cycle

Important to differentiate between shared and individual state of a thread. Shared state consists of code, global variables, and heap-allocated memory. Individual state consists of the thread's stack, registers, and metadata, all of which is stored in the **thread control block (TCB)** in each thread.

### Thread Control Block

For every thread the OS creates, it creates a TCB to store the thread's individual state. It must store both the state of the computation, and the metadata needed to manage the thread.

#### Per-thread Computation State

The thread needs a pointer to the top of its stack, which works the same as a single threaded program's stack (ie one frame per function call). Each frame contains the local variables, parameters, and the return address to jump back to when the function returns. **When a new thread is created, the OS allocates a new stack for it**.

Additionally, needs to store the processor registers. Some systems just put them on the top of the thread's stack, but others have dedicated space in the TCB.

#### How big of a stack?

Kernel stacks allocated in physical memory, so good to keep small. The max procedure call nesting in kernel code is usually small, so the kernel stacks are usually small. This works solely because of the convention to allocate all large data structures on the heap. Small stacks can cause problems if you allocate large structures locally.

User level stacks typically allocated in virtual memory, so less constrained. However, multithreaded programs can't grow their stacks indefinitely (except in languages like Go where stacks are automatically grown). Very easy to overflow the stack in multithreaded programs, but POSIX let's you configure stack size. Most implementations try to detect stack overflow with known values at the top and bottom of the stack, but this is not foolproof.

#### Per-thread Metadata

Things like thread id, scheduling priority, status, etc.

Also includes thread local variables, which are similar to global variables in that they span multiple function calls. However, they are private to each thread, and are stored in the TCB. For example, `errorno` is a macro that expands to a thread local variable holding the error code of the last system call. Additionally, many details of the heap allocator are stored in thread local variables to make parallel allocation in the heap easier (ie subdivide the heap into regions, and each thread has a region).

### Shared State

Program code, statically allocated global variables, dynamicallty allocated heap variables. Note that the kernel doesn't enforce any protection between threads for per-thread state, so it is important know which variables are designed to be shared across threads (global variables, objects on the heap) and which are designed to be private (local/automatic variables).

## Thread Life Cycle

| State    | Location of TCB                         | Location of registers |
| -------- | --------------------------------------- | --------------------- |
| INIT     | Being created (stack)                   | TCB                   |
| READY    | Ready list                              | TCB                   |
| RUNNING  | Running list                            | CPU                   |
| WAITING  | Synchronization variable's waiting list | TCB                   |
| FINISHED | Finished list then deleted              | TCB or deleted        |

### INIT

- Put thread into INIT state and allocate/initialize per-thread data structures.
- Put thread into READY state and add it to the _ready list_ (some sort of queue usually, maybe a priority queue).

### READY

- Thread is ready to run, but not currently running. TCB is stored in the _ready list_.
- At any point, the scheduler can copy the thread's register values from its TCP and move it to the RUNNING state.

### RUNNING

- Thread is currently running on a processor.
- Registers are stored in CPU instead of TCB.
- At any point, can be moved to READY state by the scheduler (ie preempted, saves registers to TCB and loads new thread's registers), or by the thread itself (ie voluntarily relinquishes control with thread_yield).
- Note that some OSes (Linux) keep RUNNING threads in the ready list (at the front).

### WAITING

- Thread is waiting for some event to occur (ie I/O, thread_join).
- Stored in the _wait list_ (ie queue) for the event it is waiting for (some synchronization variable). When the event occurs, the thread is moved to the READY state.

### FINISHED

- Thread has finished executing and will never run again.
- Some resources are freed, but the TCB is kept on the _finished list_ so that its exit status can be retrieved if a parent calls thread_join.
- After the parent calls thread_join, the TCB can be fully freed.

#### The idle thread

If a system has k processors, it will ensure that there are exactly k threads in the RUNNING state at all times. If there is nothing to run for a given CPU, the idle thread is run instead. On modern systems, the idle thread is just a loop that calls `hlt` to put the CPU into a low power state that doesn't execute instructions until an interrupt occurs and the processor is woken up.

The low-power mode is especially nice for virtualization, because the host operating system can allocate those resources to a different VM while that VM is idle.

#### Where is the TCB stored?

On a multiprocessor system, this is a non-trivial implementation issue. x86 has hardware support for fetching the ID of the current processor. In this case, the TCB could be stored in a global array, where the ith entry is the TCB for the thread running on the ith processor.

For systems without hardware support, you can use the stack pointer (which is always unique to each thread). You can store a pointer to the TCP at the bottom of the thread's stack under the procedure frames, and then use the stack pointer to find the TCB.

## Implementing Kernel Threads

```c
 // func is a pointer to a procedure the thread will run.
 // arg is the argument to be passed to that procedure.
 void thread_create(thread_t *thread, void (*func)(int), int arg) {
   // Allocate TCB and stack
   TCB *tcb = new TCB();
   thread->tcb = tcb;
   tcb->stack_size = INITIAL_STACK_SIZE;
   tcb->stack = new Stack(INITIAL_STACK_SIZE);
   // Initialize registers so that when thread is resumed, it will start running at
   // stub. The stack starts at the top of the allocated region and grows down.
   tcb->sp = tcb->stack + INITIAL_STACK_SIZE;
   tcb->pc = stub;
   // Create a stack frame by pushing stub's arguments and start address
   // onto the stack: func, arg
   *(tcb->sp) = arg;
   tcb->sp--;
   *(tcb->sp) = func;
   tcb->sp--;
   // Create another stack frame so that thread_switch works correctly.
   // This routine is explained later in the chapter.
   thread_dummySwitchFrame(tcb);
   tcb->state = READY;
   readyList.add(tcb); // Put tcb on ready list
 }

 void stub(void (*func)(int), int arg) {
   (*func)(arg); // Execute the function func()
   thread_exit(0); // If func() does not call exit, call it here.
 }
```

Creating a thread should run the code within `func` asynchronously with the calling thread. To create a thread, you must:

1. **Allocate per-thread state**. Allocate space for the new thread's TCB and stack.
2. **Initialize per-thread state**. Initialize TCB by setting machine specific registers to what is needed for RUNNING state. Must set up `func` to return to a stub that also calls `thread_exit`.
3. **Put TCB on running list**. Set state to READY and put on running list, enabling it to be scheduled.

### Deleting a thread

When a thread calls `thread_exit`, must remove it from ready lists so it stops being scheduled, and then free the per-thread state.

**NOTE**: a thread cannot free its own resources because if interrupted, it would be a memory leak (since it will never be scheduled again to finish cleanup). Instead, thread changes its state to FINISHED, and then puts itself on the finished list for some _other_ thread to clean it up,

### Thread Context Switch

When a thread is moved from RUNNING to READY, the OS must save the thread's register values to its TCB, and then load the register values of the next thread to run from its TCB.

Note that interrupts must be disabled during a context switch (OSSP 47). This is because the if a low priority thread voluntarily yields to a high priority thread, but then gets stuck in the ready list, the high priority thread will be stuck waiting.

```c
// We enter as oldThread, but we return as newThread.
 // Returns with newThread's registers and stack.
 void thread_switch(oldThreadTCB, newThreadTCB) {
   pushad; // Push general register values onto the old stack.
   oldThreadTCB->sp = %esp; // Save the old thread's stack pointer.
   %esp = newThreadTCB->sp; // Switch to the new stack.
   popad; // Pop register values from the new stack.
   return;
 }
 void thread_yield() {
   TCB *chosenTCB, *finishedTCB;
   // Prevent an interrupt from stopping us in the middle of a switch.
   disableInterrupts();
   // Choose another TCB from the ready list.
   chosenTCB = readyList.getNextThread();
   if (chosenTCB == NULL) {
      // Nothing else to run, so go back to running the original thread.
   } else {
      // Move running thread onto the ready list.
      runningThread->state = ready;
      readyList.add(runningThread);
      thread_switch(runningThread, chosenTCB); // Switch to the new thread.
      runningThread->state = running;
   }
   // Delete any threads on the finished list.
   while ((finishedTCB = finishedList->getNextThread()) != NULL) {
      delete finishedTCB->stack;
      delete finishedTCB;
   }
   enableInterrupts();
 }
 // thread_create must put a dummy frame at the top of its stack:
 // the return PC and space for pushad to have stored a copy of the registers.
 // This way, when someone switches to a newly created thread,
 // the last two lines of thread_switch work correctly.
 void thread_dummySwitchFrame(newThread) {
   *(tcb->sp) = stub; // Return to the beginning of stub.
   tcb->sp--;
   tcb->sp -= SizeOfPopad;
 }
```

#### Seperating mechanism from policy

It is useful to seperate the mechanics of performing an action from the rules for deciding when to perform that action. For example, the `thread_switch` function is a mechanism for switching threads, but the policy for deciding when to switch threads is in the scheduler. This allows different systems to take their own approach to scheduling.

Another example of this is with virtual memory. The mechanism for translating virtual addresses to physical addresses is in the MMU, but the policy for deciding which pages to keep in memory is in the page replacement algorithm.

- **Voluntary Switch**: The thread can call a library function that triggers the switch (ie `thread_yield`). Similar approach to `thread_exit` and `thread_join`.
- **Involuntary Switch**: The OS can preempt the thread (interrupt, exception, etc). Interrupt hardware saves state of current thread and then the interrupt handler is invoked (ie timer interrupt, switches to another thread). This also happens for user I/O like keyboard input.

## Combining Kernel Threads and Single-Threaded User Processes

### Switching between kernel threads and kernel handlers

- **Entering the handler**: Checks if already kernel in eflags register. If it is, just push instruction pointer and eflags (not the stack pointer) onto stack. If not, also push the stack pointer, and change the stack pointer to the interrupt stack.
- **Returning from the handler**: Inspect current eflags to see if we are switching back to user mode. If so, pop the stack pointer and eflags, and then return. If not, just pop the instruction pointer and eflags.

## Implementing Multi-threaded Processes

### Multithreaded Processes with Kernel Threads

A thread in a process has a user level stack, a kernel interrupt stack, and a kernel TCB. To create a new thread from the user's perspective, the process calls a library function that allocates a user-level stack and then makes a system call to create a new kernel thread and then returns a thread id. The kernel allocates a TCB and kernel stack, and then places the thread on the ready list.

Thread `join`, `exit`, and `yield` are all system calls that the kernel handles in a similar way, by manipulating the TCBs and the ready list.

### User-Level Threads without Kernel Threads

Added to OS's to support concurrency without any kernel support. Early versions of the JVM used this approach with _green threads_. The running process essentially implements all of the kernel data structures and scheduling policies in user space, allowing threading operations to be simple procedure calls instead of system calls.

A limitation is the lack of awareness of the OS's scheduling policies, and the inability to take advantage of multiple processors. For instance, if the process is blocked on I/O, all threads are blocked.

### Preemptive User-Level Threads

Similar to **upcalls** or **signals**, but for user-level threads. To preempt some process **P**:

1. The user-level thread library makes a system call to register a timer signal handler and signal stack with the kernel.
2. When a hardware timer interrupt occurs, the hardware saves P's register state and runs the kernel's handler.
3. Instead of restoring P's register state and resuming P where it was interrupted, the kernel's handler copies P's saved registers onto P 's signal stack.
4. The kernel resumes execution in P at the registered signal handler on the signal stack.
5. The signal handler copies the processor state of the preempted user-level thread from the signal stack to that thread's TCB.
6. The signal handler chooses the next thread to run, re-enables the signal handler (the equivalent of re-enabling interrupts), and restores the new thread's state from its TCB into the processor. execution with the state (newly) stored on the signal stack.

### User-Level Threads with Kernel Support

Process using $M$ kernel thrreads, each with their own user-level scheduler that schedules $N$ user-level threads. The kernel threads are scheduled by the OS, and the user-level threads are scheduled by the user-level scheduler.

However, there is still an issue of one of your kernel threads being blocked for the entirety of an I/O operation. Solution:

#### Scheduler Activations

Let the user and kernel level schedulers coordinate with eachother. Involves system call and upcalls (2-way communication), and thus overhead, but doesnt require the kernel to be aware of the user-level threads, and is able to optimize the uncommon case.

- User-level scheduler makes system calls to request or free processors.
- Kernel upcalls user-level scheduler to notify it of events. Examples include:
  - Processor becomes available or unavailable.
  - Transition to `WAITING` state (ie for I/O).
  - Transition from `WAITING` to `READY` state.
  - Transition from `RUNNING` to idle.

**Scheduler Activations** replace kernel threads. It has a seperate stack and CPU context, and it can be scheduled the same as a kernel thread. However, if the kernel interrups it, processor restarts execution in the user-level scheduler. Then the user-level scheduler can decide which user-level thread to run next.

## Alternatives to Threads

### Asynchronous I/O and Event-Driven Programming

Instead of using threads to manage I/O, you can use asynchronous I/O. This is especially useful for I/O bound applications, where the CPU is idle while waiting for I/O to complete. Instead of blocking on I/O, the program can continue to run and be notified when the I/O is complete.

- Process makes a system call to issue an I/O request
- Call returns immediately, and the process continues to run
- When the I/O is complete, the process is notified by the kernel through one of the following
  - calling a signal handler (callback)
  - placing the result in a queue in the processes address space
  - placing the result in a queue in the kernel's address space and letting the process poll through a system call

A common design pattern is to have a single thread interleave different I/O bound tasks by waiting for multiple different I/O events. For example, a web server that has 10 active clients might have a single thread that issues a `select` call to wait for any of the 10 clients to have data ready to read. Then, when the `select` call returns, the thread can read from the client and it will immediately (non-blocking).

#### Event-Driven Programming

A natural extension of this pattern is to be able to handle requests that involve a sequence of I/O operations. For instance, handling a web request can involve (1) accepting a connection, (2) reading the request, (3) processing the request, (4) locating and reading the requested data on disk or in a database, (5) writing the response back to the client.

**Event-driven programming** using the notion of a **continuation**, a data structure that keeps track of a task's current state and next step.

#### Event-Driven Programming vs. Threads

Very similar in practice. In either case, program blocks until next task can proceed, restores state of the task, executes the next step, and then blocks again. The main difference is whether the state is stored in a continuation and managed by the program, or in a thread and managed by the OS.

For example, a web server that reads from multiple clients and stores the data in a table of buffers

```c

 Hashtable<Buffer*> *hash;

 while(1) {
   connection = use select() to find a
                  readable connection ID
   buffer = hash.remove(connection);
   got = read(connection, tmpBuf, TMP_SIZE);
   buffer->append(tmpBuf, got);
   buffer = hash.put(connection, buffer);
 }

 // Thread-per-client
 Buffer *b;
 while(1) {
   got = read(connection, tmpBuf, TMP_SIZE);
   buffer->append(tmpBuf, got);
 }
```

##### Performance

The common argument for event-driven programming is that it is faster for two reasons:

1. **No context switch overhead**. Context switches are expensive, and the more threads you have, the more context switches you have. Context switches are also unpredictable, and can cause cache misses and TLB misses.
2. **No memory overhead**. The thread system itself comes with a non-negligible memory overhead. This is less of a problem with modern systems, but it is still a consideration. For example, allocating 1000 threads with an 8 KB stack size on a machine with 1 GB of memory would require less than 1% of the memory to be allocated to the thread stacks.

On the other hand, event driven programs by themselves don't take advantage of multiple processors, and in practice are combined with threads. A process with $N$ threads can multiplex tasks seperately using an event-driven model, and then use threads to run those tasks in parallel.

Furhtermore, the event-driven model can be more complex and harder to reason about, and if there is a reasonable amount of work to be done in the background, it is often easier to use threads.

### Data Parallel Programming

Can use SIMD instructions to perform the same operation on multiple pieces of data at the same time. For example, the `addps` instruction in x86 can add 4 single precision floating point numbers at the same time. This is useful for things like image processing, where you can apply the same operation to every pixel in an image.

In general, with data parallel programming you specify the operation to be performed on a single piece of data, and then the hardware takes care of applying that operation to multiple pieces of data at the same time.

This is useful in a wide variety of areas, and is often a source of major optimizations within programs. For instance, SQL databases can take in a query and then identify which parts of the query can be parallelized, leading to a significant speedup. This is also often used in combination with specialized hardware, like GPUs. Multimedia streaming, for example, uses SIMD instructions to decode and encode video.

A large scale example of this is the MapReduce programming model, which is used by Google and Hadoop. The idea is to split a large dataset into smaller pieces, and then apply a function to each piece in parallel. The results are then combined together.