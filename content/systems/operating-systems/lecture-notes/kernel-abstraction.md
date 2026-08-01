---
title: Hardware Modes
aliases:
  - operating-systems/lecture-notes/kernel-abstraction
category: Operating Systems
tags:
  - hardware-modes
  - kernel-mode
  - user-mode
  - dual-mode-operation
date: 2024-01-08
updated: 2026-07-30
status: evergreen
description: Why the CPU has a privileged kernel mode and a restricted user mode, and where the current mode is stored on x86 and MIPS.
sources:
  - title: Operating systems course lecture notes
    type: lecture
---

The question behind this note is who gets to control the hardware. The application could drive it directly, which would be simple and quick. It would also be completely unsafe. So the OS acts on the application's behalf, which gives us protection.

## Dual-mode operation

That raises the follow-up question of how to execute application code with restricted privileges. The hardware answers with two modes.

- **Kernel mode** is privileged. Code executes with full access to the hardware.
- **User mode** is restricted. Code can only execute the instructions the OS grants it (the non-privileged ones), and memory access is limited to the process's own memory.

```mermaid
flowchart TD
    subgraph UM[User mode]
        APP[Application code]
    end
    subgraph KM[Kernel mode]
        H[Kernel handler]
    end
    APP -- system call --> H
    APP -- interrupt --> H
    APP -- exception --> H
    H -- return to user mode --> APP
    style APP fill:#e3f2fd
    style H fill:#e8f5e9
```

A timer interrupt fires regularly, which guarantees the kernel gets a chance to take control back from a user process.

Per lecture, x86 stores the current mode in the EFLAGS register, and MIPS stores it in the status register.

> [!tip] Mode switch vs. context switch
> A syscall, interrupt, or exception switches the CPU's *mode*, but the same process stays on the CPU the whole time. A *context switch* swaps which process the CPU runs, and is a separate, more expensive operation (see [[systems/operating-systems/lecture-notes/handle-tables|handle tables]]). Mode switches happen far more often than context switches.

## Related notes

- [[systems/operating-systems/lecture-notes/processes|processes]]
- [[systems/operating-systems/v1-kernels-and-processes/2-the-kernel-abstraction|the kernel abstraction]]
