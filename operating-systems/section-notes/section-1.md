# Section 1 - C and GDB review


## C Review
**static**: has different meanings

-  static functions indicate it can't be used outside of the file (like private)
-  static variables are similar to other. ie only one

**extern**: declares variable without allocating any memory for it

-  variables must be defined somewhere else
-  allows you to use variables from other files



```c

void change(char** s) { *c = "class"; }

int main() {
   char* s = "hello";
   char* w = s;

   change(&w);
}
```

When you use an uninitialized pointer, the address that the pointer stores is the uninitialized part, and will probably lead to errors when it is interpreted as an address.


## GDB Review

`printf` debugging are useful, but limited when it comes to debugging concurrent code

Enter `GDB`

`run <...args>`: start execution

`n`: next instruction

`bt`: backtrace

`watch <variable>`:  breakpoint when it changes

`p <opt> <arg>`: print arg

`x <opt> <arg>: dereference and print arg




