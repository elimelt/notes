---
title: Synchronizing Access to Shared Objects
category: Operating Systems
tags:
  - mutual exclusion
  - locks
  - thread-safe
  - bounded queue
  - atomic operation
date: 2024-02-21
updated: 2026-07-30
status: incomplete
description: Chapter notes on OSPP chapter 5. Lock semantics and properties, a thread-safe bounded queue, spinlock and queuing lock implementations, the Linux 2.6 mutex fast path, and a short introduction to condition variables. Does not yet cover the full condition variable pattern or memory ordering.
sources:
  - title: "Operating Systems: Principles and Practice (2nd ed.), Anderson and Dahlin, chapter 5"
    url: https://ospp.cs.washington.edu/
    type: textbook
---

## Purpose

Notes on chapter 5 of [Operating Systems: Principles and Practice](https://ospp.cs.washington.edu/). The subject is how threads safely share data: what a lock guarantees, how locks are actually built from atomic instructions, and how the scheduler gets involved when waiting takes too long to spin through. Condition variables get a short introduction at the end; the rest of that material still needs to be filled in.

## Locks: Mutual Exclusion

Locks enable mutual exclusion with two operations: `acquire` and `release`.

- A lock can be in one of two states: `BUSY` or `FREE`.
- Initially, the lock is `FREE`.
- `acquire` waits until the lock is `FREE`, then sets it to `BUSY`. Checking the state and setting it must be a single atomic operation, which is why hardware support is needed.
- `release` sets the lock to `FREE`. If any threads are waiting to acquire the lock, one of them gets to proceed.

### Formal Properties

| Property         | Description                                                                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Mutual Exclusion | At most one process can hold the lock at a time.                                                                                     |
| Progress         | If no process holds the lock and some process wants to acquire it, then some process will eventually acquire the lock.               |
| Bounded Waiting  | There is a bound on the number of times that other processes can acquire the lock after a process has requested to acquire the lock. |

### Case Study: Thread-Safe Bounded Queue

The pattern to notice: one lock protects all of the queue's state, every public method acquires it on entry and releases it on exit, and the methods return success flags rather than blocking when the queue is full or empty.

```cpp
// Thread-safe queue interface
const int MAX = 10;
class ConcurrentQueue {
  // Synchronization variables
  Lock lock;
  // State variables
  int items[MAX];
  int front;
  int nextEmpty;

  public:
    ConcurrentQueue();
    ~ConcurrentQueue(){};
    bool tryInsert(int item);
    bool tryRemove(int *item);
};

// Initialize the queue to empty
// and the lock to free.
ConcurrentQueue::ConcurrentQueue() {
  front = nextEmpty = 0;
}

// Try to insert an item. If the queue is
// full, return false; otherwise return true.
bool ConcurrentQueue::tryInsert(int item) {
  bool success = false;
  lock.acquire();

  if ((nextEmpty - front) < MAX) {
    items[nextEmpty % MAX] = item;
    nextEmpty++;
    success = true;
  }

  lock.release();
  return success;
}
// Try to remove an item. If the queue is
// empty, return false; otherwise return true.
bool ConcurrentQueue::tryRemove(int *item) {
  bool success = false;
  lock.acquire();

  if (front < nextEmpty) {
    *item = items[front % MAX];
    front++;
    success = true;
  }

  lock.release();
  return success;
}
```

A simple test program that exercises the queue:

```cpp
int main(int argc, char **argv) {
  ConcurrentQueue *queues[3];
  sthread_t workers[3];
  int i, j;
  // Start worker threads to insert.
  for (i = 0; i < 3; i++) {
    queues[i] = new ConcurrentQueue();
    thread_create_p(&workers[i],
    putSome, queues[i]);
  }

  // Wait for some items to be put.
  thread_join(workers[0]);

  // Remove 20 items from each queue.
  for (i = 0; i < 3; i++) {
    printf("Queue %d:\n", i);
    testRemoval(&queues[i]);
  }
}

// Insert 50 items into a queue.
void *putSome(void *p) {
  ConcurrentQueue *queue = (ConcurrentQueue *)p;
  for (int i = 0; i < 50; i++)
    queue->tryInsert(i);

  return NULL;
}
// Remove 20 items from a queue.
void testRemoval(ConcurrentQueue *queue) {
  int item;
  for (int i = 0; i < 20; i++) {
    if (queue->tryRemove(&item))
      printf("Removed %d\n", item);
    else
      printf("Nothing there.\n");
  }
}
```

## Spinlocks

A spinlock makes the acquiring thread wait in a loop, repeatedly checking whether the lock is available. The thread burns CPU cycles the whole time it waits, so spinlocks only make sense when the lock is held for less time than a context switch would take.

### Implementing Multiprocessor Spinlocks

Most processor architectures provide atomic `read-modify-write` instructions that take an exclusive copy of a physical memory location, using the same machinery that keeps caches coherent between processors. The `test-and-set` instruction, for example, atomically sets a memory location to 1 and returns its previous value. That is enough to build a lock:

```cpp
struct spinlock {
  int held = 0;
}
void acquire(lock) {
  while(test_and_set(&lock->held));
}

void release(lock) {
  lock->held = 0;
}
```

If `test_and_set` returns 0, the lock was free and the caller now holds it. If it returns 1, someone else held it, and the loop tries again.

## Queuing Locks

Sometimes you want to accommodate both short and long critical sections while keeping overhead low. Busy waiting cannot be eliminated entirely on a multiprocessor, but a queuing lock minimizes it: the lock's own bookkeeping is guarded by a spinlock held only for a few instructions, and threads that must wait get suspended instead of spinning.

On `acquire`, if the lock is `FREE`, the caller proceeds. If it is `BUSY`, the caller adds itself to a wait queue and suspends. On `release`, the next thread in the queue gets woken.

Suspending a thread here is delicate. The thread must disable interrupts so it cannot be preempted while holding the scheduler's spinlock, acquire that scheduler spinlock, release the queuing lock's spinlock, and then switch to the next thread on the ready list. The handoff of spinlocks is what prevents the lost wakeup where a release happens between "decided to sleep" and "actually asleep".

```cpp
class Lock {
 private:
  int value = FREE;
  SpinLock spinLock;
  Queue waiting;
 public:
  void acquire();
  void release();
};

Lock::acquire() {
  spinLock.acquire();
  if (value != FREE) {
    waiting.add(runningThread);
    scheduler.suspend(&spinLock);
    // scheduler releases spinLock
  } else {
    value = BUSY;
    spinLock.release();
  }
}

void Lock::release() {
  TCB *next;
  spinLock.acquire();
  if (waiting.notEmpty()) {
    next = waiting.remove();
    scheduler.makeReady(next);
  } else {
    value = FREE;
  }
  spinLock.release();
}

class Scheduler {
 private:
  Queue readyList;
  SpinLock schedulerSpinLock;
 public:
  void suspend(SpinLock *lock);
  void makeReady(Thread *thread);
}

void Scheduler::suspend(SpinLock *lock) {
  TCB *chosenTCB;
  disableInterrupts();
  schedulerSpinLock.acquire();
  lock->release();
  runningThread->state = WAITING;
  chosenTCB = readyList.getNextThread();
  thread_switch(runningThread, chosenTCB);
  runningThread->state = RUNNING;
  schedulerSpinLock.release();
  enableInterrupts();
}

void Scheduler::makeReady(TCB *thread) {
  disableInterrupts();
  schedulerSpinLock.acquire();
  readyList.add(thread);
  thread->state = READY;
  schedulerSpinLock.release();
  enableInterrupts();
}
```

Note that on `release`, when a waiter exists, the lock value stays `BUSY` and ownership passes directly to the woken thread.

### Case Study: Linux 2.6 Kernel Mutex Lock

In Linux, most locks are `FREE` most of the time, and even a `BUSY` lock usually has no other waiters. The Linux mutex optimizes this common case with a fast path that acquires and releases the lock without touching the spinlock or disabling interrupts, using x86 atomic instructions directly. The mutex has three states:

```c
struct mutex {
  /* 1: unlocked, 0: locked, negative: locked, possible waiters */
  atomic_t count;
  spinlock_t wait_lock;
  struct list_head wait_list;
};
```

The `acquire` code is a macro, avoiding even a function call on the fast path:

```asm
      lock decl (%eax)      // atomic decrement of a memory location
                            // address in %eax is pointer to lock->count
      jns 1f                // jump if not signed (if value is now 0)
      call slowpath_acquire
```

The slow path keeps retrying with an atomic exchange, sleeping between attempts:

```c
 for (;;) {
  /*
  * Lets try to take the lock again - this is needed even if
  * we get here for the first time (shortly after failing to
  * acquire the lock), to make sure that we get a wakeup once
  * it's unlocked. Later on, if we sleep, this is the
  * operation that gives us the lock. We xchg it to -1, so
  * that when we release the lock, we properly wake up the
  * other waiters:
  */
  if (atomic_xchg(&lock->count, -1) == 1)
    break;

  /* didn't get the lock, go to sleep: */
  ...
 }
```

## Condition Variables

Locks handle mutual exclusion; condition variables handle waiting for state to change. A condition variable is a queue of threads waiting for some condition over shared state to become true, and it is always paired with a lock that protects that state. The API:

- `wait(lock)`: atomically release the lock and suspend on the queue. When woken, reacquire the lock before returning.
- `signal()`: wake one waiting thread, if any.
- `broadcast()`: wake all waiting threads.

The caller must hold the lock when calling any of these. The standard usage pattern re-checks the condition in a loop:

```cpp
lock.acquire();
while (!condition)
  cv.wait(&lock);
// ... use the shared state ...
lock.release();
```

The `while` (rather than `if`) matters because under Mesa semantics, which is what practical systems implement, `signal` only moves a waiter to the ready list. Between the wakeup and the waiter actually reacquiring the lock, another thread can run and change the state, so the condition has to be re-checked.

This section only scratches the surface. The full chapter treatment (bounded buffer with condition variables, readers/writers, design patterns for shared objects) still needs to be written up.

## Related notes

- [[operating-systems/v2-concurrency/4-concurrency-and-threads|concurrency and threads]]
- [[operating-systems/benchmarks/false_sharing|false sharing]]
