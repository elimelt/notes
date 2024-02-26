# Synchronizing Access to Shared Objects

## Locks: Mutual Exclusion

Locks enable mutual exclusion with two operations: `acquire` and `release`.

- A lock can be in one of two states: `BUSY` or `FREE`.
- Initially, the lock is `FREE`.
- `acquire` waits until the lock is `FREE`, then sets it to `BUSY`.
  - This needs to be an atomic operation, and is typically implemented to be so in hardware.
- `release` sets the lock to `FREE`. If there are processes waiting to acquire the lock, one of them is able to proceed after the lock is released.

### Formal Properties

| Property         | Description                                                                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Mutual Exclusion | At most one process can hold the lock at a time.                                                                                     |
| Progress         | If no process holds the lock and some process wants to acquire it, then some process will eventually acquire the lock.               |
| Bounded Waiting  | There is a bound on the number of times that other processes can acquire the lock after a process has requested to acquire the lock. |

### Case Study: Thread-Safe Bounded Queue

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


And here is a simple test program that uses the queue:

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
  for (int i = 0; i < 20; j++) {
    if (queue->tryRemove(&item))
      printf("Removed %d\n", item);
    else
      printf("Nothing there.\n");
  }
}
 ```

## Spinlocks

A spinlock is a lock that causes a process trying to acquire it to simply wait in a loop while repeatedly checking if the lock is available. They should be used only when the lock is expected to be held for a short period of time, ie. when the time to acquire the lock is less than the time to context switch. While waiting for the lock, the process continues to run and waste CPU cycles.

### Implementing Multiprocessor Spinlocks

Most processor architectures provide atomic `read-modify-write` instructions that acquires an exclusive copy of a given physical memory location, similar to underlying mechanisms for cache coherence among multiple processors. These instructions are used to implement spinlocks. For example, the `test-and-set` instruction atomically sets a memory location to 1 and returns its previous value. This can be used to implement a lock as follows:

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

## Queuing Locks

Sometimes want to accommodate both short and long critical sections while still minimizing overhead. It is not possible to completely avoid busy waiting on a multiprocessor, but you can minimize it by using a queuing lock.

With a queuing lock, access to the underlying data structure is controlled by a spinlock. On `acquire`, if the lock is `FREE`, the process can proceed. If the lock is `BUSY`, the process is added to a queue and suspended. When the lock is released, the next process in the queue is resumed.

To suspend a thread on a multiprocessor using this type of lock, first need to disable interrupts so it isn't preempted while holding the ready lists spinlock. Then, acquire the ready list spinlock, and then release the queuing lock's spinlock. Finally, switch to the next thread in the ready list and release the ready list spinlock.

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

 ### Case Study: Linux 2.6 Kernel Mutex Lock

 In Linux, most locks are `FREE` most of the time. Additionally, if a lock is `BUSY`, it is still likely that no other locks are waiting for it. THe Linux implementation of a mutex lock optimizes for this commone case by providing a fast path for the case where threads don't need to wait.

 Linux utilizes x86 specific instructions that allow the lock to be acquired and released on the fast path *without* first acquiring the spinlock or disabling interrupts. Mutexes have 3 possible states:

 ```c
 struct mutex {
  /* 1: unlocked, 0: locked, negative: locked, possible waiters */
  atomic_t count;
  spinlock_t wait_lock;
  struct list_head wait_list;
 };
 ```

 The Linux lock `acquire` code is a macro to avoid the overhead of a function call on the fast path.

```asm
      lock decl (%eax)      // atomic decrement of a memory location
                            // address in %eax is pointer to lock->count
      jns 1f                // jump if not signed (if value is now 0)
      call slowpath_acquire
```

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

Condition variables are used to wait for a particular condition to become true. They are used in conjunction with locks to provide a way for a thread to be woken up when a condition becomes true. The condition variable is associated with a lock, and the lock must be held when waiting on the condition variable.