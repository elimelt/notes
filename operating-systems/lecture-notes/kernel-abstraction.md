---
title: Hardware Modes
category: Operating Systems
tags: hardware modes, kernel mode, user mode, dual mode operation, EFLAGS register, MIPS status register
description: Covers the implementation of hardware modes in operating systems, including kernel mode and user mode. Discusses the concept of dual mode operation, where the processor switches between privileged kernel mode and restricted user mode to provide protection with restrictions. Explains the use of the EFLAGS register in x86 systems and the status register in MIPS architectures to control and monitor the current hardware mode.
---

# Lecture 2 -

## Hardware Modes

*Who actually gets to control the hardware?*

*The application*? It would be simple and quick, but isn't safe at all.

*The OS*? Can act on behalf of the application, which gives us protection.

### Challenge: Protection with Restrictions

*How do we execute code with restricted privileges?*

**Hardware Support: Dual Mode Operation**

-  Kernel mode - privileged. Execution with full access to the hardware
-  User mode - restricted. Only able to execute instructions granted by OS (ie non privileged). Limits on memory accesses, only allowed to access own memory. There is a timer interrupt that regularly gives the kernel the ability to take control from a user process.

On x86, mode stored in EFLAGS register. On MIPS, mode stored in status register.
