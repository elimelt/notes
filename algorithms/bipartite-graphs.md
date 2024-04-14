# Bipartite Graphs

- **Definition**: An undirected graph $G = (V, E)$ is bipartite if there exists a partition of $V$ into two sets $V_1$ and $V_2$ such that every edge in $E$ has one endpoint in $V_1$ and the other in $V_2$.
- **Applications**:
  - Scheduling (machines = $V_1$, jobs = $V_2$)
  - Stable matching (men = $V_1$, women = $V_2$)

You can tell if a graph is bipartite if there is a proper coloring of vertices, i.e., you can assign one of two colors to each vertex such that no two adjacent vertices have the same color. Many problems become easier if the underlying graph is bipartite graphs.

## Odd-Length Cycles

**Lemma**: If $G$ is bipartite, then it does not contain an odd-length cycle.
**Proof**: You cannot 2-color an odd cycle, let alone $G$.

**Lemma**: Let $G$ be a connected graph, and let $L_0, \ldots, L_k$ be the layers produced by $BFS(s)$. Then exactly one of the following holds:

1. No edges of $G$ joins two nodes of the same layer, and $G$ is bipartite.
2. An edge of $G$ joins two nodes of the same layer, and $G$ contains an odd cycle (and is thus not bipartite).

**Proof**: If an edge joins two nodes of the same layer, then the path from the lowest common ancestor of the two nodes to each node forms an odd length cycle. This must be the case, since any edges between two vertices of the same level connects two paths of the same length back to their LCA of the BFS tree. The length of this cycle is thus $2k + 1$, where $k$ is the length of back to the LCA, and the $1$ comes from the edge between the two nodes in the same level.


## Algorithm

**Problem**: Given a graph $G$, output `true` if it is bipartite, `false` otherwise.

