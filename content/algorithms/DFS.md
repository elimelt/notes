---
title: Depth First Search Algorithm and Tree Properties
category: Algorithms
tags:
  - dfs
  - graph theory
  - depth first search
  - spanning trees
  - graph traversal
  - acyclic graphs
date: 2024-04-14
updated: 2026-07-30
status: evergreen
description: Recursive and iterative DFS implementations, and a proof that every non-tree edge of a DFS tree connects a vertex to one of its ancestors.
sources:
  - https://www.cs.princeton.edu/~wayne/kleinberg-tardos/
---

## Purpose

Running DFS on a graph produces a DFS tree (a depth-first spanning tree of the starting vertex's component). The tree contains every vertex DFS reaches, and its edges are a subset of the graph's edges. This note gives the implementations and proves the one structural property that makes DFS trees useful.

## Core idea

Unlike the [[algorithms/BFS|BFS]] tree, a DFS tree has no minimum-depth guarantee, and its levels say nothing about distance. What it does guarantee: no edge of the graph connects two different subtrees. Every non-tree edge climbs between a vertex and one of its ancestors. That is why DFS finds cycles: any non-tree edge closes a cycle through the tree path between its endpoints.

**Lemma**: Let $T = (V_t, E_t)$ be a DFS tree of graph $G = (V, E)$. For every edge $e = (x, y) \in E$ with $e \notin E_t$, one of $x$ or $y$ is an ancestor of the other in $T$.

**Proof**: Without loss of generality, assume $x$ is discovered first. When $dfs(x)$ is called, $y$ is still undiscovered. The call $dfs(x)$ does not return until every neighbor of $x$ has been discovered, since it visits each neighbor and recurses on the undiscovered ones. So $y$ is discovered during $dfs(x)$, which places $y$ somewhere in the subtree rooted at $x$, making $x$ an ancestor of $y$. $\blacksquare$

## Implementation

```python
def dfs_recursive(G, src, vis=None, f=print):
    if vis is None:
        vis = set()
    if src in vis:
        return
    vis.add(src)
    f(src)
    for v in G[src]:
        dfs_recursive(G, v, vis, f)

def dfs_iterative(G, src, f=print):
    vis = set()
    stack = [src]
    while stack:
        curr = stack.pop()
        if curr in vis:
            continue
        vis.add(curr)
        f(curr)
        for v in G[curr]:
            stack.append(v)
```

## Properties of DFS Spanning Trees

DFS visits every vertex in the starting vertex's connected component, so it finds [[algorithms/connected-components|connected components]] just like BFS does.

The ancestor property is what sets DFS apart. Since every non-tree edge joins a vertex to an ancestor or descendant, DFS gives a clean way to detect cycles, and it underlies algorithms on [[algorithms/DAGs|directed acyclic graphs]] like topological sorting.

## Related notes

- [[algorithms/graphs-intro|Graph fundamentals]]
- [[algorithms/BFS|breadth-first search]]
- [[algorithms/DAGs|directed acyclic graphs]]
