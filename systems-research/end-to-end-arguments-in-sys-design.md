---
title: End-to-End Arguments in System Design 
category: System Design
tags: system design, end-to-end, design, networking
description: Paper review of "End-to-End Arguments in System Design" by Saltzer, Reed, and Clark
---

###### [End-to-End Arguments in System Design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf)

---

### What is the Problem?

- Placing functions at lower levels of a system may not be beneficial
    - Functions generally know best, and error checking can therefore be redundant
    - Low level function placement may be costly
- A correct comms system can only be built with endpoints
    - Ex: detecting crashes, delivering/sequencing messages, etc.

### Summary 

#### Low Level Functionality

- Paper argues that low-level functionality is mainly a performance optimization
- If the probability of an error is low, doesn't make sense to add error checking in the middle of the system. Instead, let the endpoints handle it

### Weakness

- Maintainability (checks missing in the middle)
- Certain systems ought to have intermediate checks (e.g. comms over lossy media)
- Catching errors can take longer, needs to make it all the way to an endpoint to detect

### Open Questions

-
-

### Further Reading
