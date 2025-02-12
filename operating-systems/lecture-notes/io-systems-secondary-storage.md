---
title: I/O Systems and Secondary Storage
category: Operating Systems
tags: I/O systems, secondary storage, device controllers, DMA, system bus, PCI bus, programmed I/O, device drivers
description: Covers the implementation of I/O systems and secondary storage in operating systems. Discusses the hardware environment of I/O systems, their role and structure, the memory hierarchy, and performance considerations for hard disk drives (HDDs) and solid-state drives (SSDs). Explores topics such as device controllers, direct memory access (DMA), system and PCI buses, programmed I/O, and device drivers.
---

# I/O Systems and Secondary Storage


## I/O System Hardware Environment

I/O devices are typically either **block devices**, which transfer data in fixed-size blocks, or **character devices**, which transfer data one character at a time in a stream.

**Device controllers** are the hardware (a mini-computer) that connects the CPU to the I/O devices. They are responsible for sending commands to the device, and for receiving and sending data to and from the device.

The I/O devices communicate via controller registers/memory-mapped I/O, or direct memory access (DMA).

Old computers typically had a single bus (the **system bus**) that connects the CPU, memory, and I/O devices. The topology of the computer was similar to old ethernet networks with a single broadcast domain.

More modern and performant systems have multiple buses. The **PCI** bus is a high-speed backbone that all the other busses branch off of (**memory**, **SCSI**, **USB**, etc.).

The I/O system needs to be able to handle a wide variety of devices with different data transfer rates, data formats, and control mechanisms.

## I/O System's Role and Structure

Needs to provide:

- A uniform interface to many devices, as well as device specific interfaces when necessary.
- Device-system communication and interaction through device drivers.
- Every device is given a unique id so it can be referenced by applications.

### Organization

- **Programmed I/O with polling**: CPU issues an I/O command for the process, and the process busy waits until the I/O is complete. Inefficient because the CPU is tied up waiting for the I/O to complete.
- **Interrupt-driven I/O**: CPU issues an I/O command and continues to execute. When the I/O is complete, the device sends an interrupt to the CPU, which then handles the I/O completion. The process may or may not be blocked while waiting for the I/O to complete, but the processor is not tied up waiting for the I/O to complete.
- **Direct Memory Access (DMA)**: The DMA module controls exchange of data between I/O module and main memory using physical addresses. The processor requests transfer of a block of data from DMA, and is interrupted when the transfer is complete. This saves the processor from having to handle the data transfer.

## Secondary Storage

Anything outside of *primary memory* (RAM) is considered **secondary storage**. This includes hard drives, SSDs, and other storage devices. SS doesn't allow direct execution of instructions or data access via load/store instructions, and is instead accessed via I/O operations.

Secondary storage is...
- **Non-volatile**: Data is retained even when the power is off.
- Very slow compared to primary storage.
- Failure-prone.
- Giant and relatively cheap compared to primary storage. 2024 numbers:
    - 2 TB HDD for $73 ($0.04/GB)
    - 30 TB HDD for $700
    - 500 GB SSD for $50 ($10/GB)
    - 100 TB SSD for $40,000



### Memory Hierarchy

| Level | Speed | Cost | Size | Volatility |
|-------|-------|------|------|------------|
| Registers | Fastest | Most Expensive | Smallest | Volatile |
| L1 Cache | Fast | Expensive | Small | Volatile |
| L2 Cache | Fast | Less Expensive | Still not a lot | Volatile |
| Main Memory | Slower | Less Expensive | Larger | Volatile |
| Secondary Storage | Slow | Cheap | Largest | Non-Volatile |
| Tertiary Storage | Slowest | Least Expensive | Largest | Non-Volatile |


### HDDs and SDDs

**HDDs** are mechanical devices that store data on spinning disks. They have a read/write head that moves across the disk to read and write data. They are slow, but have a large capacity and are relatively cheap.

**SSDs** are solid-state devices that store data on flash memory. They are much faster than HDDs, but are more expensive. They are also more reliable and consume less power.

### Disks and the OS

Disks are messy, slow, error-prone, horrible devices, and its the OS's job to make them look like a nice, clean, fast, reliable, and easy-to-use device.

The OS typically provides different levels of disk access to different clients, including:
- **physical block access**: the ability to read and write blocks of data to the disk.
- **disk logical block access**: the ability to read and write to a disk block number, without needing to know the physical location of the block.
- **file system**: the ability to read and write files at a specified offset, block, or byte.

With old disks, only physical block access was available. With modern disks, the controller provides a higher-level interface that maps physical regions on disk (cylinders, sectors, ect.) to logical block numbers from $[0, n]$, (ie a contiguous range of blocks to the OS).

### Performance Issues

The HDD's performance is affected by its mechanically moving parts. Limiting the amount of seeking and **defragmenting** help, but only to an extent.