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

Threads provide the illusion of infinite processors. OS uses a *thread scheduler* to switch between threads to run. How threads are interleaved and scheduled should be transparent to the application.

#### Cooperative vs. preemptive multithreading

Early versions of MacOS used cooperative multithreading, where the kernel would only switch threads when the running thread made a system call relinquishing control. This is a bad idea because a thread can hog the CPU and starve other threads.

Modern operating systems use preemptive multithreading, where the kernel can preempt a thread at any time, even in the middle of a single instruction.

### 4.2.2 Why "Unpredictable Speed"?

**Always avoid** reasoning about the relative speed of threads when trying to evaluate the correctness of your code. The speed of threads is unpredictable for many reasons.

## 4.3 POSIX Thread API

| Function Signature | Description |
| ----------------- | ----------- |
| `pthread_create(pthread_t *thread, const pthread_attr_t *attr, void *(*start_routine) (void *), void *arg)` | Create a new thread. |
| `pthread_join(pthread_t thread, void **retval)` | Wait for a thread to finish. |
| `pthread_detach(pthread_t thread)` | Detach a thread. |
| `pthread_self()` | Get the current thread. |
| `pthread_exit(void *retval)` | Terminate the current thread. |
| `pthread_cancel(pthread_t thread)` | Cancel a thread. |
