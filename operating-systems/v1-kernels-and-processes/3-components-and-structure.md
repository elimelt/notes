# Chapter 3 - The Programming Interface

What functions do we need an OS to provide for applications?

- **Process management**: create, destroy, and manage processes. This includes the ability to create new processes, terminate existing processes, wait for processes to complete, and send asynchronous notifications to processes.
- **Input/Output**: Communicate with devices and files, as well as other processes.
- **Thread management**: create, manage and destroy threads, aka tasks that share memory and other resources within a process. 
- **Memory management**: allocate and deallocate memory for processes.
- **File management**: create, delete, and manipulate files and directories. users should be able to persist named data on disk.
- **Networking and Distributed Systems**: processes should be able to communicate with other processes on different machines over the network. processes should also be able to coordinate their actions, despite faults and delays.
- **Graphics/Window Management**: Processes control pixels on their portion of the screen. Should utilize hardware acceleration to draw graphics quickly.
- **Authentication and Security**: Permissions system to control access to resources. Processes should be able to authenticate themselves to other processes and to the OS.