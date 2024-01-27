# Obects Handles and Reference Counts

## Object Manager

Windows was written in C, which doesn't have a notion of "objects". Early Windows had its own **Object Manager**, which was responsible for defining object types, naming objects, handling handles for users etc. 

For example, there were objects for threads, processes, files, semaphores, etc.

Each object had a **handle count**, the number of handles the user has to the object, and the **ref count**, the number of references to the object within the kernel (which also includes handles).

