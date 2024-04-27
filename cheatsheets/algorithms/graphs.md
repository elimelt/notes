# Graphs

## Lemmas to Know and Use

### Undirected Graphs

- $|E| = \frac{1}{2} \sum_{v \in V} deg(v)$
- The number of odd degree vertices is even
- If a graph is acyclic, there is a vertex of degree $\le 1$

### Trees

For any graph $G = (V, E)$, if two of the following are true, then all three are and $G$ is a tree

- $|E| = |V| - 1$
- $G$ is connected
- $G$ is acyclic

### BFS

- $BFS(s)$ visits $v$ iff there is a path from $s \to v$
- Edges into then-undiscovered vertices define the BFS-tree of $G$
- Level $i$ of the BFS-tree contains all vertices with shortest path $i$ from the root
- **All non-tree edges** join vertices on the same, or adjacent levels of the tree
- If $G$ contains edges between vertices in the same layer, it is not bipartite, nor a tree

### Bipartite Graphs

- $G$ is bipartite iff you can partition $V$ into $V_1$ and $V_2$ such that all edges are between $V_1$ and $V_2$, i.e. no edges between vertices in different sets
- $G$ is bipartite iff $G$ has no odd cycles
