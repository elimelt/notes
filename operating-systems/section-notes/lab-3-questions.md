# Lab 3 Questions

## Question #1

*Q:* Why might an application prefer using `malloc` and `free` instead of using `sbrk` directly?

*A:* Malloc and free are higher-level and don't require the user to think about the details of the heap. Instead of needing to consider the current top of the heap, and how the memory you request is laid out contiguously, malloc and free handle all of that for you. Thus, user programs are able to apply more complex optimizations/strategies for memory allocation like first and best fit, as well as coalescing free blocks to reduce fragmentation, without having to manage the added complexity.

## Question #2

*Q:* What is the relationship between `malloc`/`free` and `sbrk`?

*A:* When malloc lacks the space nessesary to fulfill an allocation request, it calls sbrk to expand its heap region and increase the memory available to the process. With the current implementation of `malloc` in `umalloc.c`, `sbrk` only ever expands the heap (through `morecore`), but we never shrink the heap. In a real system, we would probably also want to shrink the heap once we have enough free space that it would be unlikely to be used in the near future.

## Question #3:

*Q:* How many child processes are created by the shell program in order to run the command `ls | wc`? (This mirrors real OS'es).

> Hint: the shell will go into the `case PIPE` case in `user/sh.c:runcmd` when it receives a cmd with the pipe operator `|`.

> Fun fact: the `|` operator behaves this way in most UNIX shells, and is why the infamous forkbomb command `:(){ :|:& };:` _forks_. [More on the forkbomb LINK](https://en.wikipedia.org/wiki/Fork_bomb).

*A:* The shell will create two child processes, one for `ls` and one for `wc`. The `ls` process will write to the pipe, and the `wc` process will read from the pipe.

## Question #4:

*Q:* The shell will call `pipe()` when the command `ls | wc` is run. What does the shell do with the read end? What does the shell do with the write end? (~1-2 sentences).

> Hint: once again look at `case PIPE` in `user/sh.c:runcmd`.

*A:* The shell's process (ie the parent) closes both ends of the pipe. However, the child process created for ls closes its own stdout and then immediately duplicates the write end of the pipe, replacing its stdout with the write end of the pipe. The child process created for `wc` similarly closes its own stdin and then duplicates the read end of the pipe, replacing its stdin with the read end of the pipe. Both child processes then close both file descriptors of the pipe, and execute their commands using the newly duplicated file descriptors for the pipe (which are stdin/out from their perspectives).

## Question #5:

*Q:* When a syscall completes, user-level execution resumes with the instruction immediately after the syscall. When a page fault exception completes, where does user-level execution resume? (~1 sentence).

It resumes at the instruction that caused the page fault. The processor exception saves the state of the program, and then the kernel handles the page fault. Once the kernel has resolved the page fault, it restores the state of the program and resumes execution at the instruction that caused the page fault (not the one after it).

## Question #6:

*Q:* How should your `xk` implementation decide whether an unmapped reference is a normal stack operation versus a stray pointer dereference that should cause the application to halt?

> Hint: keep in mind that your stack grower in `xk` should allow the user stack to grow to 10 pages, and no more than 10 pages.

The faulting address needs to be within `stack->va_base >= addr >= stack->va_base - (PGSIZE * 10)`. If the faulting address is within the stack region, then it is a normal stack operation. If the faulting address is outside the stack region, then it is a stray pointer dereference and the application should halt.

## Question #7:

*Q:* Is it possible to reduce the user stack size at run-time (i.e., to deallocate the user stack when a procedure with a large number of local variables goes out of scope)? If not, explain why. If so, sketch how that might work. (~1-3 sentences).

## Question #8:

*Q:*  The TLB caches the page table entries of recently referenced pages. When you modify the page table entry to allow write access, which function in `vspace.c` should you use to ensure that the TLB does not have a stale version of the page table entry you modified?

> Hint: in x86-64 modifying the `CR3` register changes what page table the CPU uses and flushes the TLB. Look for a function that modifies the `CR3` register.

## Question #9

*Q:* For each member of the project team, how many hours did you spend on this lab?

## Question #10

*Q:* What did you like or dislike about this lab? Is there anything you wish you knew earlier?









# Debugging

- fork (user) triggers trap to call fork (kernel)
- return to fork_ret, which returns to trap, which returns to trap_ret
- iretq from trap_ret triggers kernel/vectors.S: vector14 (ie page fault)
- jumps to alltraps and calls trap with an addr 0x7fffff52 of a COW page
- allocate seperate copy for COW page and return from trap to trapret
- iretq from trapret returns to bad_mem_access, reading pid which has &pid == 0x7fffff52



- child runs user/lab3test.c:83    printf(stdout, "bad_mem_access: oops could read kernel addr %lp = %lx\n", a, *a);
- traps with page fault addr == 0xffffffff80000000
- struct vpage_info* vpi = va2vpage_info(vr, addr) in trap causes another page fault trap, this time with addr == 24
- infinite loop on above line with addr == 24

