---
title: Finding Connected Components in Undirected Graphs Using BFS/DFS
category: Algorithms
tags: graph theory, connected components, breadth-first search, depth-first search
description: Explains how to partition an undirected graph into connected components using BFS or DFS algorithms in O(|V| + |E|) time complexity. Includes Python implementation using adjacency lists and demonstrates how to create a data structure that enables O(1) time queries for path existence between vertices.
---

# Connected Components

Given an undirected graph $G = (V, E)$, you can find partition $V$ into sets of connected components $C_1, C_2, \ldots$ in $O(|V| + |E|)$ using breadth-first search (BFS) or depth-first search (DFS).

In other words, we can create a data structure from $G$ such that given two vertices $u, v \in V$, we  we answer whether there exists a path from $u \to v$ in $O(1)$ time and $O(|V|)$ space.

The basic idea is to run a BFS/DFS starting at every vertex, and to assign a label to each vertex we visit during this traversal. We can use an array (if vertices are numbered) or hash map to store the vertex to component set mapping $V \to C_i$

```python
import networkx as nx
import random
from collections import deque, defaultdict

def connected_components(graph):
  a = [None] * len(graph)

  def bfs(label, G, src):
    q = deque()
    vis = set()

    q.append(src)
    while q:
      curr = q.popleft()
      vis.add(curr)
      a[curr] = label
      for v in G[curr]:
        if v not in vis:
          q.append(v)

  curr_label = 0

  for v in range(len(graph)):
    bfs(curr_label, graph, v)
    curr_label += 1
  return a

def component_sets(G):
  n = len(G)
  comp = connected_components(G)
  component_dict = defaultdict(lambda: set())
  for v, c in enumerate(comp):
    component_dict[c].add(v)

  return list(component_dict.values())
```

## Strategy for Unconnected Graph

In general, if you are solving a graph problem you should first assume your graph is fully connected, and then after you've found a solution for connected graphs, you can run your algorithm on all the connected components of your graph.
