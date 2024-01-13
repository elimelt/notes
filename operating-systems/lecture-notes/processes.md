# Processes

## What is a process?

The OS's abstraction of a running program. A process is a program in execution.

Simplest case:

- An address space
- A sinle thread of execution

## What's "in" a process?

Consists of (at least)

- An address space, containing the code (instructions) and data of the running program
- (At least one) CPU state, consisting of the instruction pointer (EIP), stack pointer (ESP), and other general purpose registers.
- A set of OS resources, including open files, open pipes, open network connections, etc.

### Address Space

Remember stack grows down (ie push decrements ESP, pop increments ESP). Stack contains all runtime frames.

A processes address space (idealized):

```txt
+----------------------+ <- 0x7FFFFFFF
|        Stack         |
|   (dynamic memory)   |
+----------------------+ <- ESP
|          |           |
|          v           |
|                      |
|          ^           |
|          |           |
+----------------------+
|        Heap          |
|   (dynamic memory)   |
+----------------------+
|        Data          |
|   (data segment)     |
+----------------------+
|        Code          | <- EIP
|   (text segment)     |
+----------------------+ 0x00000000
```


## OS Process Namespace

- Each process has a unique identifier (PID)
- The PID namespace is global to the OS
- Operations that create processes (e.g. `fork`) returns the pid
- Operations on processes take pid as an argument (e.g. `kill`)