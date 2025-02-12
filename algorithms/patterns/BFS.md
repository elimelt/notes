---
title: Spring Boot Quickstart Guide
category: software-engineering
tags: spring boot, quick start, spring web, rest repositories
description: A step-by-step guide to creating a Spring Boot application with Rest Repositories
---
---
title: Breadth First Search Pattern
category: algorithms
tags: breadth-first search, graph algorithms, graph traversal, shortest path
description: A technical exploration of the Breadth First Search algorithm, focusing on its key properties and applications in graph problems.
---

# Breadth First Search

BFS is an extremely versatile algorithm that comes up a lot in graph problems. The key property of BFS is that it explores vertices in order of the length of their shortest path from the starting vertex. Any time you're dealing with an unwieghted graph and need to find the shortest path between two vertices, BFS is a good place to start. Its usefulness doesn't end there though; BFS can be used to find connected components, detect cycles, and more.

You can think of BFS as producing level-wise sets of vertices in a graph.

$$
L_0 = \{s\}
$$

$$
L_i = \{neighbors(v_j)\ :\ v_j\ \in L_{i\ -\ 1}\setminus L_0\ \cup L_1\ \cup\ldots\cup L_{i\ -\ 2}\}
$$



