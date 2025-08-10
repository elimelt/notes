---
title: Graph Theory
category: Algorithms
tags: Graphs, Trees, DFS, BFS, Topological Sort, Minimum Spanning Tree, Disjoint Sets
description: A comprehensive overview of graph theory, including concepts such as nodes, edges, trees, and minimum spanning trees, as well as algorithms like depth-first search and breadth-first search.
---

# Graphs

## Undirected Graphs

- $|E| = \frac{1}{2} \sum_{v \in V} deg(v)$
- The number of odd degree vertices is even
- If a graph is acyclic, there is a vertex of degree $\le 1$

## Trees

For any graph $G = (V, E)$, if two of the following are true, then all three are and $G$ is a tree

- $|E| = |V| - 1$
- $G$ is connected
- $G$ is acyclic

## Breadth-First Search

- $BFS(s)$ visits $v$ iff there is a path from $s \to v$
- Edges into then-undiscovered vertices define the BFS-tree of $G$
- Level $i$ of the BFS-tree contains all vertices with shortest path $i$ from the root
- **All non-tree edges** join vertices on the same, or adjacent levels of the tree
- If $G$ contains edges between vertices in the same layer, it is not bipartite, nor a tree

## Bipartite Graphs

- $G$ is bipartite iff you can partition $V$ into $V_1$ and $V_2$ such that all edges are between $V_1$ and $V_2$, i.e. no edges between vertices in different sets
- $G$ is bipartite iff $G$ has no odd cycles

## Depth First Search

- $DFS(s)$ visits $x$ iff there is a path from $s \to x$ (so you can find C.C.s)
- DFS Spanning Tree formed by edges into then-undiscovered vertices
  - DFS tree not minimum depth, nor do its levels reflect the min distance
  - Non-tree edges never join vertices on the same or adjacent level. Always join a vertex with one of its ancestors or descendants
  - All vertices visited during $DFS(s)$ are a descendant of $s$ in the DFS tree
    - For every edge $(u, v) \notin T_{DFS(s)}$, either $x$ is an ancestor of $y$ or $y$ is an ancestor of $x$

## Directed Acyclic Graphs

- **Source**: vertex with no incoming edges
- **Sink**: vertex with no outgoing edges
- Every DAG has a source and a sink
- Every DAG has a topological order, and every graph with a topological order is a DAG

### Topological Order

An ordering of nodes $v_1, v_2, \ldots, v_n$ so that for every edge $(v_i, v_j)$, $i < j$.

- To find, initialize map of in-degrees for each vertex, and a queue of vertices with in-degree 0.
- Then, while the queue isn't empty, remove a vertex, adding it to the ordering, and decrement its neighbors in-degree.
- If any of them become 0, add them to the queue.

## Cuts

- A cut of $G = (V, E)$ is a bipartition of $V$ into $S, V - S$ for some $S \subseteq V$
- $e = (u, v) \in (S, V - S)$ if exactly one of $u, v \in S$
- If $G$ is connected, then there is at least one edge in every cut
- Every cycle crosses a cut an even number of times
- *Cut property*: Let $(S, V - S)$ be any cut, and let $e$ be the **min** cost edge with exactly **one** endpoint in $S$. Then **every** MST contains $e$.
- *Cycle property*: Let $C$ be any cycle, and $f$ be the **max** cost edge belonging to $C$. Then **no** MST contains $f$.

## Minimum Spanning Tree

- **Algorithm**: $O(m\log(n))$
  - Sort edges by increasing weight, initialize an empty tree $T$, and add each vertex to its own set.
  - Then, for each edge $e = (u, v)$, if $u$ and $v$ are currently in different sets, add $e$ to $T$ and merge the sets containing $u$ and $v$.
- **Proof**:
  - Show that it is a tree
    - Initially start with $|V| = n$ sets, and only add an edge if you are connecting two of them. Therefore, we end with $n - 1$ sets to add an edge between each original set
    - Only add edges between disconnected components, so it must be acyclic, since each additional edge $e$ connecting $C_1$ and $C_2$ (two disconnected components) is the only edge between them. This means $C_1 + e + C_2$ has an odd number of edges in its cut, so there are no cycles formed.
  - Must be an MST
    - Considered edges in increasing order of cost. Taking the first edge where the optimal and Kruskal's differ, we can exchange them for an equal or better solution.

### Disjoint Sets

- **Implementation**:
  - Maintain a tree of pointers, where every vertex is labeled with the longest path ending at that vertex. To check set membership of $u$ and $v$, traverse to root and check if $root(u) = root(v)$. This is $O(\log(n))$
  - To merge two sets, point root with smaller label to root with larger label, adjusting labels of the new root if necessary. This is $O(1)$.
- **Properties**:
  - If the label of a root is $k$, there are at least $2^k$ elements in the set.