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