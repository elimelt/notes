# Chapter 2  |  The Kernel Abstraction

"A central role of operating systems is protection - the isolation of potentially misbehaving applications and users so that they do not corrupt other applications or the operating system itself."

**Kernel**: The lowest level of software running on the operating system. It is the first program loaded on boot, and it remains in memory until the system is shut down. It is responsible for all interactions with the hardware, and it is the only program that runs in privileged mode.

**Process**: The execution of an application program with restricted access to the operating system and hardware. Processes are managed by the kernel, and they need to request access to resources from the kernel.

## The Process Abstraction

In the same way an object instantiates a class in OOP, a process instantiates a program. In most OS's, a programs instructions are stored once in a file on disk. The user edits the file, then compiles the file into a binary executable. When a user runs the executable, the OS creates a new process including program data, heap, and stack, loads the executable into memory, and starts the process.

The OS keeps track of all processes in a process control block (PCB). The PCB contains the process ID, the process state, the program counter, the stack pointer, the memory management information, and the accounting information. The OS uses the PCB to keep track of all processes, and it uses the program counter to keep track of the next instruction to execute.

*Digging Deeper:* in Linux, the PCB is called the `task` struct, and is a doubly linked list of processes, starting off with the `init task` which has a `pid` of 0. Users can view processes using the `ps` command, or could view the data directly in `/proc` for the system, or `/proc/<pid>` for a specific process.

## Dual-Mode Operation

There is a single bit in the CPU that determines whether the CPU is in user mode or kernel mode. When the CPU is in user mode, checks for privileged instructions are enabled that stop the program from executing anything that could harm the system. When in kernel mode, these checks are turned off.

The **principal of least privilege** states that a process should only have access to the resources it needs to do its job. This is enforced by the CPU by only allowing processes to access resources in user mode. Some operating system code runs in their own user-level processes, for example the window manager. Code that runs in Kernel mode *needs* to be trusted, because it has access to all of the hardware.

The hardware must be able to switch between user and kernel mode safely, and must support the following restrictions for user mode:

- **privileged instructions**: some instructions are prohibited
- **memory protection**: processes should not be able to access memory that does not belong to them
- **timer interrupts**: the CPU should be able to stop executing a process at will

This "kernel bit" is just one of many flags set in the CPU. These flags aren't directly accessible to application code, but the **process status register** (PSR) is has corresponding flags that are set when the processor switches between user and kernel mode. This register works similarly to other registers (like arithmetic condition codes in assembly).

Intel x86 processors actually support 4 privilege levels, but none of MacOS, Windows or Linux make use of the extra 2 levels.


## Virtual Memory

In a naiive implementation (like MS-DOS), the OS directly loads the program into memory and gives it access to the entire memory space. This is problematic for a few reasons, including security, fragmentation of memory, difficulty in growing the stack/heap. **Virtual memory** solves these problems by giving each process its own virtual address space in which their memory starts at 0. The OS maps the virtual address space to physical memory, usually in fixed size chunks called **pages**. The OS can then swap pages in and out of memory as needed for each process. Modern OS's often also use address randomization to prevent attacks.

## Timer Interrupts

The CPU's **hardware timer** is a timer that runs periodically (either by time or number of instructions) sends an interrupt to the CPU to switch back to kernel mode. Each core has its own timer. Usually, processes will only be stopped by a timer if the user signals the OS to stop the process.

Older versions of MacOS lacked the ability to forcibly stop a process, so if a process was stuck, the user would have to reboot the system. This was due to their **preemtive scheduling** algorithm, that instead of using an interrupt at the hardware level, would instead rely on processes to voluntarily poll the OS to see if they should stop. When a runaway process was stuck in a loop, it would never poll the OS, and the OS would never stop it, leading to those forever spinning beach balls.

## Types of Mode Transfer

In a high performance server, the CPU may switch from kernel to user mode thousands of times every second. It is thus important for this switch to be fast and secure.

### User to Kernel

There are three main ways: **system calls**, **exceptions**, and **interrupts**. *Trapping* is the process of syncronously switching from user to kernel mode.

**Interrupts** are the most common way to switch from user to kernel mode. They are triggered by an external event, like a hardware device or another process signal. The CPU finished any user instructions, saves the state, and then switches to kernel mode and calls the corresponding interrupt handler. On a multicore system, only one core will handle the interrupt. An alternative to interrupts would be the kernel **polling** IO devices, but this is inefficient.

To enable high performance IO, the OS uses **direct memory access** (DMA), and a circular queue of requests for each IO device to handle. Each entry in the queue is called a **buffer descriptor**.

**Exceptions** are triggered by internal events, like a page fault or a divide by zero error. The CPU finishes any user instructions, saves the state, and then switches to kernel mode and calls the corresponding exception handler. Another common use case is in debuggers. A breakpoint is just a modified instruction that traps into kernel mode when it is executed. The kernel then reloads the instruction and transfers control to the debugger.

Exceptions are extremely useful for virtualization, and are often used as a signal for the host OS to emulate some hardware functionality, or to execute an operation of behalf of the guest OS. In this way, a VM can run in user mode, and the host OS can handle all of the privileged instructions.

**System Calls** allow the user program to voluntarily request the OS to execute something on its behalf. Most processors have a special `syscall` or `trap` instruction to do this. Each call invokes some code at a *pre-defined* address in the kernel. To see a table of system calls on Linux, run `man syscalls`.

### Kernel to User

There are several reasons why the kernel would want to switch to user mode.

- **New Process**: When the kernel creates a new process, it needs to switch to user mode to start executing the process.
- **Resume Process**: After interrupting a process, the kernel needs to switch back to user mode to resume the process.
- **Switching to a Different Process**: The kernel may want to switch to a different process, for example if the current process is waiting for IO.
- **User-Level Upcall**: Similar to interrupts, for the user program to handle asynchronous events, the kernel needs to be able to switch to user mode to call the user-level handler.

## Implementing Safe Mode Transfer


**Limited Entry Into Kernel**

The kernel needs to be able to switch to user mode at any time, but the user program should not be able to switch to kernel mode. User programs should only be able to request privileged operations through paths defined by the OS/kernel. If the user program violates any built in rules, the kernel should be able to stop the program and switch back to user mode by returning an error code.

**Atomic Changes to Processor State**

When switching between modes, there needs to be distinction between the state of memory; kernel code has access to its local memory and registers as well as the program's memory and registers, whereas user code should be isolated. The switch between these two contexts needs to be atomic.

**Transparent, Restartable Execution**

The kernel needs to be able to stop a user program in the middle of execution at any point, and to resume execution with *exactly* the same state later. User processes shouldn't need to know that they are being interrupted. On interrupt, the processor saves the current state to memory, defers further events, changes to kernel mode, then jumps to the correct handler. After execution of the handler, the same is done in reverse to resume the user program.

### Interrupt Vector Table

**Interrup handlers** are stored in kernel memory as a table of function pointers called the **interrupt vector table**. Each entry in the table corresponds to a specific interrupt. Although the format is processor specific, on x86, entries are broken into:

- 0-31: **processor exceptions** (divide by zero, page fault, etc.)
- 32-255: **interrupts** (hardware interrupts, system calls, etc.)
- 64: **system call/trap** (syscall instruction)

On modern, multicore systems, interrup routing has become increasingly programmable at the kernel level. This is especially important for IO-heavy systems like web servers. The kernel can route interrupts to the core that is handling the IO, helping to avoid cache misses.

### Interrupt Stack

Each core has its own **interrupt stack**. When an interrupt occurs, the processor pushes the current state onto the interrupt stack, and then switches to kernel mode. The interrupt handler then runs on the interrupt stack. When the handler is finished, the processor pops the state off the interrupt stack and resumes execution of the user program.

Most OS's allocate a **kernel interrupt stack** (KIS) for every user process. When a process is running, the hardware interrupt stack points to the processes' kernel interrupt stack (which should be empty if being run in User Mode). This makes it easy for the kernel to switch between processes inside an interrupt or syscall handler.

- when running in user mode, KIS is empty
- when preempted (ready but not running), KIS contains the state of the process when it was interrupted
- when waiting for IO in syscall, KIS contains the process state as well as the syscall handler and IO Driver

### Interrupt Masking

Hardware provides a privileged instruction to disable interrupts. This is useful for critical sections of code that should not be interrupted. On X86, disable interrupts defers interrupts until an enable interrupt instruction is executed. While they are deferred, interrupts are queued, but will be lost if this queue fills up. Generally, hardware will buffer one interrupt of each type, and will drop any additional interrupts of that type.

### Hardware Support for Saving and Restoring Registers

For x86...

- If processor in user mode, push interrupted process's stack pointer onto kernel interrupt stack, then switches to kernel stack
- Pushes interrupted process's instruction pointer
- Pushes x86 *processor status word*, which includes control bits and condition codes (which are needed to restore state of current execution)


## Putting It All Together: x86 Mode Transfers

"First, we provide some background on the x86 architecture. The x86 is segmented, so
pointers come in two parts: (i) a segment, a region of memory such as code, data, or stack,
and (ii) an offset within that segment. The current user-level instruction is a combination of
the code segment (cs register) plus the instruction pointer (eip register). Likewise, the
current stack position is the combination of the stack segment (ss) and the stack pointer
within the stack segment (esp). The current privilege level is stored as the low-order bits of
the cs register rather than in the processor status word (eflags register). The eflags register
has condition codes that are modified as a by-product of executing instructions; the eflags
register also has other flags that control the processor's behavior, such as whether
interrupts are masked or not"

