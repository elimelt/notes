---
title: Depth First Search Algorithm and Tree Properties
category: algorithms
tags:
  - graph theory
  - depth first search
  - spanning trees
  - graph traversal
description: A technical explanation of Depth First Search (DFS) algorithm and its tree properties, including both recursive and iterative implementations. The document covers key properties of DFS trees, including the ancestor-descendant relationship of non-tree edges, and includes a formal lemma and proof about DFS tree characteristics.
---

# Depth First Search (DFS)

Running DFS on a graph produces a DFS tree (or depth-first spanning-tree). The DFS tree contains all the vertices of the graph and the edges of the DFS tree are a subset of the edges of the original graph.

Unlike the BFS tree, DFS trees aren't minimum depth, and its levels don't really tell you much. However, the property holds that sub-trees of a DFS tree must not contain any edges connecting them.

**Lemma**: For a DFS tree of graph $G = (V, E)$ $T = (V_t, E_t)$,  $\forall e = (x, y) \in E$, if $e \notin E_t$, then one of $x$ or $y$ is an ancestor of the other in the tree.

**Proof**: Without loss of generality, assume $x$ is discovered first.

Call $dfs(x)$. At this time, $y$ is still undiscovered. By observation, it is enough to say $y$ will be discovered before finishing $dfs(x)$. This is true because $y$ is a neighbor of $x$, so DFS will eventually visit $y$. If $y$ is still undiscovered when $x$ we visit $x$'s neighbors, it will at least be discovered then.


```python

def dfs_recursive(G, src, vis = set(), f=print):
  if src in vis:
    return
  vis.add(src)
  f(src)
  for v in G[src]:
    dfs_recursive(G, v, vis)

def dfs_iterative(G, src, vis=set(), f=print):
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

DFS visits every vertex within the starting vertex's connected component, so you can use it to find all connected components of a graph similar to BFS.

However, unlike BFS, the DFS tree has the property that every non-tree edge joins a vertex to one of its ancestors/decedents in the tree. We can thus still use DFS to find cycles in a graph.

