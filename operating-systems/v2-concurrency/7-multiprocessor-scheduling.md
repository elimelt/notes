# Multiprocessor Scheduling

Modern systems usually have multiple processors, each with multiple cores that all have hyperthreading. Scheduling algorithms for multiprocessor systems need to make use of the parallelism that these systems offer.

### Scheduling Sequential Applications on Multiprocessors

Consider a server application that needs to process a large number of requests. A simple approach would be to maintain a single MFQ, as well as a lock on it so only one processor can access it at a time. When a request needs to do something like I/O, it can reenter the MFQ and let another request run. However, this approach has a few problems:

- **Contention for MFQ lock**: As the number of processors increases, the contention for the MFQ lock also increases. This can lead to a lot of time being spent waiting for the lock.
- **Cache Coherence Overhead**: When a processor modifies a queue, it needs to invalidate the cache of all other processors that have a copy of the queue. This means that each processor will need to fetch the queue either from memory or a remote cache, which can take orders of magnitude longer than fetching from a local cache. Not to mention this needing to happen while the queue is locked.
- **Limited Cache Reuse**: Threads will run on random queues, so they won't be able to reuse the cache of the previous thread that ran on that processor.

For these reasons, common practice is to have a separate MFQ for each processor. Each processor uses **affinity scheduling**, where once a thread is scheduled on a processor, it will stick to only being scheduled there. Rebalancing load between processors is done by moving threads between MFQs.

### Scheduling Parallel Applications on Multiprocessors

Although there often exists a logical mapping between work and processors, it's often not possible to know this mapping at compile time. The number of threads and processors available can change at runtime, and the work may not be evenly divisible among the processors.

**Oblivious Scheduling** is when the scheduler operates without knowledge of the intent of the program. Each thread schedules completely independently of the others. This can be simple and effiient, but also has some problems:

- **Bulk synchronous delay**: In sequential pipelines of parallel work (like MapReduce), the slowest thread determines the speed of the entire pipeline.
- **Producer-consumer delay**: In a chain of producer consumer threads (like a bash pipeline), the slowest thread in a chain determines the speed of the entire pipeline.
- **Critical path delay**: In a DAG of parallel work (like a fork-join parallel program), if a thread performing work on the critical path is preempted, the entire program will be delayed.
- **Preemption of lock holder**: If a thread holding a lock is preempted, the lock will be held for longer than necessary, and other threads will be delayed while waiting for the lock.
- **I/O**: If a read/write request is blocked in the kernel, the thread blocks as well. In order to make use of the processor, there should be more threads than processors, but this can lead to the above problems.

#### Gang Scheduling

The application picks some decomposition of the work into some set of threads, and those threads are always either running togther or not at all. This can be especially useful for specialized servers that need fine-grained control over the scheduling of their threads (like a DBMS). Windows, Linux and MacOS all support mechanisms for gang scheduling.

It is usually more efficient to run two parallel programs, each with half the number of processors, than to time slice two programs, each gang scheduled onto all processors.

Allocating different processors to different tasks is called **space sharing**, and is useful for minimizing context switches and cache invalidations. Space sharing is straightforward if tasks start and stop at the same tie. However, with a dynamic number of available processors, it's less trivial.

#### Scheduler Activations

Applications are given an *execution context*, or **scheduler activation**, on each processor assigned to the application. Via upcalls, the application is informed whenever the number of processors changes. Blocking on I/O operations also triggers an upcall to allow the application to repurpose the processor.

Scheduler activations only define the mechanism for informing an application of its processor allocation, but not the policy for scheduling.

## Real Time Scheduling

If responsiveness is more important than throughput, we can use real-time scheduling. For instance, in control systems, or with a user interface, we want to ensure tasks are completed by a **deadline**.

- **Over-provisioning**: Only schedule a fraction of the resources on a system. Like not signing up for too many classes in college.
- **Earliest Deadline First (EDF)**: The task with the earliest deadline is scheduled next. This is optimal for minimizing the number of missed deadlines for CPU-bound tasks. However, mixed workloads can complicate this, since it might be more efficient to start a task with a later deadline to request I/O, and then start a task with an earlier deadline.
- **Priority Donation**: *priority inversion* can lead to infinite waiting times for lower priority tasks. To avoid this, when a high-priority task is waiting for a lock held by a lower priority task, the higher priority task "dontates" some of its priority to the lower priority task. This allows the low priority task to be scheduled to complete the critical section and release the lock, at which point it will return to its original priority and the processor can be given to the high priority task.