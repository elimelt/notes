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
- **Many threads per process.** Several concurrent threads, each executing within the restricted rights of the process. A subset of the process’s threads running, while rest are suspended. Any thread running in a process can make system calls into the kernel, blocking itself but no other threads. When the processor gets an I/O interrupt, it preempts one of the running threads so the kernel can run the interrupt handler; when the handler finishes, the kernel resumes that thread.
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
   // Create a stack frame by pushing stub’s arguments and start address
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

**NOTE**: a thread cannot free its own resources because if interrupted, it would be a memory leak (since it will never be scheduled again to finish cleanup). Instead, thread changes its state to FINISHED, and then puts itself on the finished list for some *other* thread to clean it up,

### Thread Context Switch

When a thread is moved from RUNNING to READY, the OS must save the thread's register values to its TCB, and then load the register values of the next thread to run from its TCB.

Note that interrupts must be disabled during a context switch (OSSP 47). This is because the if a low priority thread voluntarily yields to a high priority thread, but then gets stuck in the ready list, the high priority thread will be stuck waiting.

```c
// We enter as oldThread, but we return as newThread.
 // Returns with newThread’s registers and stack.
 void thread_switch(oldThreadTCB, newThreadTCB) {
   pushad; // Push general register values onto the old stack.
   oldThreadTCB->sp = %esp; // Save the old thread’s stack pointer.
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

