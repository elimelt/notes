---
title: Breadth First Search Pattern
category: Algorithms
tags:
  - breadth-first-search
  - graph-algorithms
  - graph-traversal
  - shortest-path
date: 2024-04-14
updated: 2026-07-30
status: draft
description: Why BFS visits vertices in order of shortest-path distance, and the problems that property solves.
---

## Purpose

BFS shows up constantly in graph problems. This note pins down the one property that makes it useful, the level-by-level visit order, and lists the problems that property solves.

## Core idea

BFS explores vertices in order of the length of their shortest path from the starting vertex. Any time you have an unweighted graph and need the shortest path between two vertices, start with BFS.

## Intuition

BFS runs on a queue. The start vertex goes in first, and each dequeued vertex enqueues its undiscovered neighbors. Every vertex at distance $1$ enters the queue before any vertex at distance $2$, and so on, so the traversal processes the graph one distance ring at a time. The first time BFS discovers a vertex, it got there through a shortest path.

## Level sets

You can describe the traversal as producing level-wise sets of vertices. Let $s$ be the start vertex and define

$$
L_0 = \{s\}
$$

$$
L_i = \{ v \notin L_0 \cup L_1 \cup \cdots \cup L_{i-1} : (u, v) \in E \text{ for some } u \in L_{i-1} \}
$$

Each level $L_i$ is exactly the set of vertices at distance $i$ from $s$. A quick induction shows why. Suppose every vertex in levels $L_0$ through $L_{i-1}$ sits at distance equal to its level index. A vertex $v \in L_i$ has a neighbor in $L_{i-1}$, so its distance is at most $i$. Its distance can't be smaller than $i$ either, because a vertex at distance $j < i$ has a neighbor at distance $j - 1$, and that neighbor's level would have pulled $v$ into $L_j$.

## What it solves

- Shortest paths in unweighted graphs.
- Connected components, by running BFS from every unvisited vertex.
- Bipartiteness checks, since an edge between two vertices in the same level implies an odd cycle.

## Related notes

- [[reference/cheatsheets/algorithms/graphs|Graph Theory]]
- [[algorithms/patterns/sliding-window|Sliding Window Pattern]]
