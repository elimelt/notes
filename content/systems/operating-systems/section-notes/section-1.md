---
title: C and GDB Review
aliases:
  - operating-systems/section-notes/section-1
category: Operating Systems
tags:
  - c
  - gdb
  - pointers
  - static
  - extern
  - debugging
date: 2024-01-04
updated: 2026-07-31
status: draft
description: Short review notes on C linkage, pointer basics, and a few core GDB commands.
sources:
  - https://sourceware.org/gdb/current/onlinedocs/gdb.html
  - https://en.cppreference.com/w/c/language/storage_duration
---

## Purpose

Capture the small set of C and GDB ideas that came up in section. This is a compact memory aid, not a full language reference.


## C Review
**static**: has different meanings

- static functions cannot be used outside the file where they are defined
- static local variables keep one storage location across function calls

**extern**: declares variable without allocating any memory for it

- variables must be defined somewhere else
- allows you to use variables from other files



```c

void change(char** s) { *s = "class"; }

int main() {
   char* s = "hello";
   char* w = s;

   change(&w);
}
```

When you use an uninitialized pointer, the address that the pointer stores is the uninitialized part, and will probably lead to errors when it is interpreted as an address.


## GDB Review

`printf` debugging is useful, but limited once the program state changes quickly or multiple threads are involved.

Enter `gdb`.

`run <...args>`: start execution

`n`: next instruction

`bt`: backtrace

`watch <variable>`:  breakpoint when it changes

`p <opt> <arg>`: print arg

`x <opt> <arg>`: examine memory at an address



