---
title: Finding Connected Components in Undirected Graphs Using BFS/DFS
category: Algorithms
tags:
  - graph theory
  - connected components
  - breadth-first search
  - depth-first search
date: 2024-04-14
updated: 2026-07-30
status: evergreen
description: How to partition an undirected graph into connected components in O(|V| + |E|) with BFS or DFS, producing a labeling that answers path-existence queries in O(1).
---

## Purpose

Given an undirected graph $G = (V, E)$, you can partition $V$ into connected components $C_1, C_2, \ldots$ in $O(|V| + |E|)$ using [[algorithms/BFS|breadth-first search (BFS)]] or [[algorithms/DFS|depth-first search (DFS)]]. The payoff is a data structure built once from $G$ that answers whether a path exists between two vertices $u, v \in V$ in $O(1)$ time and $O(|V|)$ space: two vertices are connected exactly when they carry the same component label.

## Algorithm

Scan the vertices in order. Each time you hit a vertex that has no label yet, it starts a new component: run BFS (or DFS) from it and stamp every vertex you reach with the current label, then increment the label. Each traversal stays inside one component because BFS only follows edges, and it covers the whole component because BFS reaches everything connected to its source. Store the labels in an array (if vertices are numbered) or a hash map.

```python
from collections import deque, defaultdict

def connected_components(graph):
    a = [None] * len(graph)

    def bfs(label, src):
        q = deque([src])
        a[src] = label
        while q:
            curr = q.popleft()
            for v in graph[curr]:
                if a[v] is None:
                    a[v] = label
                    q.append(v)

    curr_label = 0
    for v in range(len(graph)):
        if a[v] is None:
            bfs(curr_label, v)
            curr_label += 1
    return a

def component_sets(G):
    comp = connected_components(G)
    component_dict = defaultdict(set)
    for v, c in enumerate(comp):
        component_dict[c].add(v)
    return list(component_dict.values())
```

The label array doubles as the visited set, so every vertex enters the queue at most once and the total work over all traversals is $O(|V| + |E|)$.

## Strategy for Unconnected Graphs

When solving a graph problem, first assume the graph is connected. Once you have a solution for connected graphs, run it separately on each connected component.

## Related notes

- [[algorithms/BFS|breadth-first search]]
- [[algorithms/DFS|depth-first search]]
- [[algorithms/graphs-intro|graph fundamentals]]
