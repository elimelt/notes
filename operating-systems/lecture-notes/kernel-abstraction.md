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
