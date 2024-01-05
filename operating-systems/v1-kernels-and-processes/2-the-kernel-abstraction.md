# Chapter 2 - The Kernel Abstraction

"A central role of operating systems is protection - the isolation of potentially misbehaving applications and users so that they do not corrupt other applications or the operating system itself."

**Kernel**: The lowest level of software running on the operating system. It is the first program loaded on boot, and it remains in memory until the system is shut down. It is responsible for all interactions with the hardware, and it is the only program that runs in privileged mode.

**Process**: The execution of an application program with restricted access to the operating system and hardware. Processes are managed by the kernel, and they need to request access to resources from the kernel.

## The Process Abstraction

In the same way an object instantiates a class in OOP, a process instantiates a program. In most OS's, a programs instructions are stored once in a file on disk. The user edits the file, then compiles the file into a binary executable. When a user runs the executable, the OS creates a new process including program data, heap, and stack, loads the executable into memory, and starts the process.

The OS keeps track of all processes in a process control block (PCB). The PCB contains the process ID, the process state, the program counter, the stack pointer, the memory management information, and the accounting information. The OS uses the PCB to keep track of all processes, and it uses the program counter to keep track of the next instruction to execute.

_Digging Deeper:_ in Linux, the PCB is called the `task` struct, and is a doubly linked list of processes, starting off with the `init task` which has a `pid` of 0. Users can view processes using the `ps` command, or could view the data directly in `/proc` for the system, or `/proc/<pid>` for a specific process.

## Dual-Mode Operation

There is a single bit in the CPU that determines whether the CPU is in user mode or kernel mode. When the CPU is in user mode, checks for privileged instructions are enabled that stop the program from executing anything that could harm the system. When in kernel mode, these checks are turned off.

The **principal of least privilege** states that a process should only have access to the resources it needs to do its job. This is enforced by the CPU by only allowing processes to access resources in user mode. Some operating system code runs in their own user-level processes, for example the window manager. Code that runs in Kernel mode _needs_ to be trusted, because it has access to all of the hardware.

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

There are three main ways: **system calls**, **exceptions**, and **interrupts**. _Trapping_ is the process of syncronously switching from user to kernel mode.

**Interrupts** are the most common way to switch from user to kernel mode. They are triggered by an external event, like a hardware device or another process signal. The CPU finished any user instructions, saves the state, and then switches to kernel mode and calls the corresponding interrupt handler. On a multicore system, only one core will handle the interrupt. An alternative to interrupts would be the kernel **polling** IO devices, but this is inefficient.

To enable high performance IO, the OS uses **direct memory access** (DMA), and a circular queue of requests for each IO device to handle. Each entry in the queue is called a **buffer descriptor**.

**Exceptions** are triggered by internal events, like a page fault or a divide by zero error. The CPU finishes any user instructions, saves the state, and then switches to kernel mode and calls the corresponding exception handler. Another common use case is in debuggers. A breakpoint is just a modified instruction that traps into kernel mode when it is executed. The kernel then reloads the instruction and transfers control to the debugger.

Exceptions are extremely useful for virtualization, and are often used as a signal for the host OS to emulate some hardware functionality, or to execute an operation of behalf of the guest OS. In this way, a VM can run in user mode, and the host OS can handle all of the privileged instructions.

**System Calls** allow the user program to voluntarily request the OS to execute something on its behalf. Most processors have a special `syscall` or `trap` instruction to do this. Each call invokes some code at a _pre-defined_ address in the kernel. To see a table of system calls on Linux, run `man syscalls`.

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

The kernel needs to be able to stop a user program in the middle of execution at any point, and to resume execution with _exactly_ the same state later. User processes shouldn't need to know that they are being interrupted. On interrupt, the processor saves the current state to memory, defers further events, changes to kernel mode, then jumps to the correct handler. After execution of the handler, the same is done in reverse to resume the user program.

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
- Pushes x86 _processor status word_, which includes control bits and condition codes (which are needed to restore state of current execution)

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

1. _Mask interrupts_ to prevent the processor from being interrupted while switching modes
2. _Save the current state_ of the user program on the interrupt stack, including the stack pointer, execution flags, and instruction pointer, all to temp hardware registers
3. _Switch onto kernel interrupt stack_ by changing the stack pointer to point to its base address
4. _Push the current state_ of the user program onto the kernel interrupt stack
5. _Optionally save an error code_ if this was an exception with one.
6. _Invoke interrupt handler_ by jumping to the correct entry in the interrupt vector table

The interrupt handle also saves some registers to its own stack before executing any code that might overwrite the processor state (callee-saved registers).

Once finished executing, the callee then pops the registers off the stack, restoring the interrupted process state, excluding the program counter, execution flags, and stack pointer. The interrupt handler then executes a `iret` instruction, which restores those aforementioned elements of state, fully restoring the interrupted process.

_Note..._ for exceptions that signal instructions in the kernel, the handler will modify the program counter to point to the instruction **after** the exception occurred, so as to prevent an infinite loop.

## Implementing Secure System Calls

OS kernel constructs restricted enviornment for process execution. Any time a process needs to execute something outside of its _protection domain_, it requests the OS do so on its behalf using a **system call**.

**System calls** are the primary interface between user programs and the OS. When the user program makes a call, the library code will _trap_ into kernel mode, and the kernel will execute the system call handler. System calls generally try to appear as a normal function call thorughout a library and often use **stubs** to mediate between the user program and the kernel. This allows the following flow:

1. User calls function in library (user stub)
2. Stub fills in code for system call, and traps into kernel mode
3. Hardware transfers control to kernel and finds correct system call handler (kernel stub), which checks args and then executes the correct system call
4. Syscall returns to kernel stub, which returns to user stub's next instruction, which returns to the user program

For example, the user-level library stub for `open` in x86 looks like:

```asm
 // We assume that the caller put the filename onto the stack,
 // using the standard calling convention for the x86.

 open:
 // Put the code for the system call we want into %eax.
    movl #SysCallOpen, %eax

 // Trap into the kernel.
    int #TrapCode

 // Return to the caller; the kernel puts the return value in %eax.
    ret
```

Where `SysCallOpen` is the code for the specific system call to run, and `TrapCode` is the index into the x86 interrupt vector table for the system call handler. Note that `%eax` is overwritten by the return of the syscall, and that `int` saves the user state (program counter, stack pointer, eflags) onto the kernel interrupt stack, beforte jumping to the syscall handler on the IVT. This example is fairly simple stub, so some of the details are implicit, but in general a kernel stub has four main tasks:

**Locate syscall arguments**. Unlike regular kernel procedures, the args of a syscall are in user memory, typically on a user's stack. Stubs need to locate arguments and ensure that any pointers reside in the user's address space. These will be virtual addresses, so the stub needs to translate them to physical addresses.

**Validate parameters**. The stub needs to check that all the arguments are valid, and that there aren't any invalid states. For example, if a syscall is trying to open a file, the kernel stub needs to check that it exists, that the user has permission to open it, etc.

**Copy before check**. To prevent _time of check vs. time of use_ (TOCTOU) attacks, the kernel stub copies the arguments to kernel memory before checking them. This prevents the user from modifying the arguments after they have been checked in order to bypass the checks and supply illegal arguments.

**Copy results back**. The kernel stub copies the results of the syscall back to user memory before returning to the user program. This is necessary because the kernel stub executes in kernel mode, and thus has access to kernel memory, but the user program does not.

```c
int KernelStub_Open() {
    char *localCopy[MaxFileNameSize + 1];
    // Check that the stack pointer is valid and that the arguments are stored at
    // valid addresses.
    if (!validUserAddressRange(userStackPointer, userStackPointer + size of arguments))
        return error_code;
    // Fetch pointer to file name from user stack and convert it to a kernel pointer.
    filename = VirtualToKernel(userStackPointer);
    // Make a local copy of the filename. This prevents the application
    // from changing the name surreptitiously.
    // The string copy needs to check each address in the string before use to make sure
    // it is valid.
    // The string copy terminates after it copies MaxFileNameSize to ensure we
    // do not overwrite our internal buffer.
    if (!VirtualToKernelStringCopy(filename, localCopy, MaxFileNameSize))
        return error_code;
    // Make sure the local copy of the file name is null terminated.
    localCopy[MaxFileNameSize] = 0;
    // Check if the user is permitted to access this file.
    if (!UserFileAccessPermitted(localCopy, current_process)
        return error_code;
    // Finally, call the actual routine to open the file. This returns a file
    // handle on success, or an error code on failure.
    return Kernel_Open(localCopy);
}
```

## Starting a New Process

At a high level, before running a program the kernel must...

- Allocate and initialize the process control block (PCB)
- Allocate memory for the process
- Load the program from disk into memory
- Allocate user-level stack
- Allocate a new kernel-level stack for handling syscalls, interrupts, and exceptions

Then, to actually run it, the kernel must...

- Copy arguments into memory. _For example_, when you click on a file in MacOS or Windows, the window manager calls upon the kernel to start a new process running whatever application is associated with the filetype. To do this, the kernel copies the file name from the window manager's memory into the new process's memory (usually at the base of the new process' stack).
- Transfer control to user mode. When a new process starts, most kernels reuse the same code as for a any other transfer to user mode. User values are saved at the bottom of the initial kernel stack, and then the kernel uses `popad` and `iret` to "return" to the start of the user program.

Finally, there is a level of indirection between program execution in the form of a stub. This ensures that the program calls exit (ie terminates), and is done by the compiler. Conceptually, this looks like:

```c
start(int argc, char** argv) {
    main(argc, argv);
    exit();
}
```

## Implementing Upcalls

**Upcalls** are a way for the kernel to notify the user program of an event. They are similar to interrupts, but are initiated by the kernel rather than hardware. These are called _signals_ in Unix, and _asynchronous events_ in Windows, and are crucial for virtualization.

#### Applications:

- **preeemptive user-level threads**: Enables threading libraries to use a periodic timer upcall to switch and/or terminate threads.
- **asynchronous I/O Notifications**: Applications can make syscalls asynchronously. When the kernel finishes the operation, it notifies the application with an upcall.
- **interprocess communication**: Any time two processes need to communicate in real time, they can use upcalls to notify each other of events. Another example might be when the user logs out, the kernel can send an upcall to all processes to terminate.
- **user-level exception handling**: If application runtimes have their own exception system, they can be notified of processor exceptions with upcalls.
- **user-level resource allocation**: If an application needs to be resource adaptive, it can use upcalls to monitor resource usage and adjust accordingly. The JVM uses upcalls to monitor memory usage and garbage collect.

Upcalls aren't always needed, and many programs get by with an event loop model. In fact, Windows didn't support immediate delivery of upcalls to user-level programs until recently.

### Unix Signals

- The kernel defines a fixed number of signal types that a process can receive.
- Processes define their own handlers for each type, or the kernel invokes a default handler.
- Handlers can either be run on the application stack, or on a seperate signal stack allocated by the user process.
- While a given signal handler is executing, the OS blocks delivery of the same signal to any other process. OS also provides a syscall to mask signals as needed.
- The kernel copies registers onto the signal stack before invoking the handler, and restores them after the handler returns.

## Booting an Operating System Kernel

Systems typically use a special read only memory (Boot ROM) to store boot instructions. On most x86 computers, this is stored in the BIOS (Basic Input/Output System).

ROM memory is relatively slow and expensive, and typically never changes, whereas kernel code needs to be updated often, so it is preferable to keep to BIOS minimal.

BIOS provides indirection between hardware and OS. It reads a fixed-size block of data from a fixed location on disk (or flash RAM) called the bootloader into memory. Some newer bootloaders also store a cryptographic signature to verify the bootloader's integrity.

Then, the bootloader loads the kernel into memory and transfers control to it. The kernel then initializes the hardware, loads the rest of the OS, and starts the first process.

## Virtual Machines

### To Boot

1. Host OS loads guest bootloader from virtual disk into memory and starts running it.
2. Guest bootloader loads guest kernel into memory and starts running it.
3. Guest kernel initializes IVT to point to its own handlers.
4. Guest kernel loads process from virtual disk into its own emulated memory.
5. When the guest kernel starts the process, it issues instructions to resume execution at user level (ie `iret` on x86). This traps into the host kernel.
6. Host kernel validates the request and then simulates the requested mode transfer exactly as if the processor had directly executed it.

### User Level System Call

1. Host kernel saves registers onto interrupt stack of guest operating system.
2. Host kernel transfers control to the guest kernel at start of interrupt handler with guest kernel running in user-mode.
3. Guest kernel performs system call, saving user state and checking arguments.
4. When guest kernel returns from syscall, triggers processor exception, dropping into host kernel.
5. Host kernel restores user state as if guest OS had returned directly.

### Processor Exceptions

Handles them similarly to user level system calls, but the host kernel tracks what privilege level the guest kernel is running at, and delegates exception handling to the guest kernel if it is running in kernel mode.

### Timer Interrupts

Host kernel returns from the interrupt to the interrupt handler for the guest kernel. The guest kernel may in turn switch guest processes; its iret will cause a processor exception, returning to the host kernel, which can then resume the correct guest process.

### I/O Interrupts

Simulation of virtual devices doesn't need to be anything like a real device. For example, when the guest OS writes to a virtual disk (ie writing to the buffer descriptor ring for the device), the host OS can read these and perform the actual write to the real disk however it wants. The guest kernel then receives an interrupt when the write is complete, which is handled similarly to a timer interrupt, but executes the guest disk interrupt handler instead of the guest timer interrupt handler.

```
  ______                   _
 |  ____|                 (_)
 | |__  __  _____ _ __ ___ _ ___  ___  ___
 |  __| \ \/ / _ \ '__/ __| / __|/ _ \/ __|
 | |____ >  <  __/ | | (__| \__ \  __/\__ \
 |______/_/\_\___|_|  \___|_|___/\___||___/

```

1. **Kernel Stack and User Process Interruption**

- When a user process is interrupted or causes a processor exception, the x86 hardware switches the stack pointer to a kernel stack. This is done before saving the current process state to ensure that sensitive kernel data is not overwritten or corrupted by user-level processes.

2. **Screen Buffer Memory Protection**

- The screen’s buffer memory must be protected because if a malicious application could alter any pixel on the screen, it could potentially display misleading information, capture sensitive data, or cause system instability. Protecting the screen buffer ensures the integrity and security of the displayed content.

3. **Dual-mode Operation Mechanisms**

- Without **privileged instructions**: User processes might be able to execute sensitive operations.
- Without **memory protection**: User processes could access and modify kernel memory directly.
- Without **timer interrupts**: User processes could monopolize the CPU, leading to a denial-of-service situation.

4. **Security Checks for Web Browser**

- To ensure executing buggy or malicious scripts cannot corrupt or crash the browser, checks like script sandboxing, code validation, resource limitations, and privilege separation should be implemented.

5. **Types of User-Mode to Kernel-Mode Transfers**

- Software Interrupts
- System Calls
- Exceptions

6. **Types of Kernel-Mode to User-Mode Transfers**

- Returning from an interrupt
- Returning from a system call
- Resuming execution after an exception
- Context switching

7. **IRET Instruction in OS**
a. The `iret` instruction is used in the interrupt service routine (ISR) to return from an interrupt, transitioning the mode from kernel-mode back to user-mode.
b. If an application program executes `iret`, it could potentially disrupt the operating system's internal state, leading to unpredictable behavior or crashes.

8. **Large Number of Registers Design**
a. Having a large number of registers can reduce the need for frequent memory accesses, improving performance.
b. Hardware features like register renaming, out-of-order execution, and branch prediction can be beneficial.
c. Adding a 16-stage pipeline and precise exceptions might increase the overhead of user-kernel switching due to increased complexity and potential stalls.

9. **Virtualization and x86 Architecture**
a. Instructions like `popf` prevent transparent virtualization because they have different behaviors in privileged and unprivileged modes, making it challenging to virtualize without affecting guest OS behavior.
b. Modifying the hardware to provide consistent behavior for instructions like `popf` in both modes can resolve the virtualization issue.

10. **Initial Value in Program Counter**

- The boot ROM is responsible for loading the initial value in the program counter for an application program before it starts running.

11. **Safe Access to Virtualized I/O Devices**

- To enable safe access to virtualized I/O devices, hardware support like I/O MMU, device assignment, and software support like device emulation, device drivers, and hypervisor integration are essential.

12. **System Calls vs. Procedure Calls**

- System calls are generally more expensive than procedure calls due to the overhead of mode switching, trap handling, and potential context switches. A test program can be designed to measure and compare the time required for each type of call.

13. **Substitute for Traps**

- Without a trap instruction, a combination of interrupts and exceptions can be used as a substitute for traps, allowing the operating system to handle events and transitions effectively.

14. **Substitute for Interrupts**

- Without interrupts, a combination of exceptions and traps can be utilized to handle events and transitions within the operating system, although it may introduce additional complexity and overhead.

15. **Steps for CPU Interrupt Handling**

- The operating system typically follows steps like saving the current state, identifying the interrupt source, invoking the appropriate interrupt handler, performing the required processing, and restoring the saved state.

16. **Operating System Stack for System Calls**

- The operating system stack for handling system calls should be separate from the application stack to ensure isolation and prevent potential stack-related vulnerabilities or conflicts.

17. **Verifying Rogue System Calls**
- Writing a program to test the operating system's protection against rogue system calls involves trying various illegal calls and observing the system's response to ensure it handles them correctly.
