# Graphs Introduction

## Undirected Graphs

An undirected graph is defined by a set of vertices and a set of edges.

$$
G = (V, E)
$$

### Terminology

- **Connectedness**: A graph is connected if there is a path between every pair of vertices.
- **Isolated vertex**: A vertex with no edges.
- **Planar graph**: You can draw the graph on a plane such that no two edges cross.
- **Degree of vertex**: $deg(v) = $ Number of edges that touch said vertex.
- **Connected components**: maximal set of components within a graph. Partition your set of vertices
- **Path**: A sequence of distinct vertices s.t. each vertex is connected to the next vertex with an edge. `length(path) = # edges`
- **Cycle**: Path of length > 2 that has the same start and end
- **Tree**: A connected graph with no cycles.

### Degree Sum

#### Claim 
In any undirected graph, the number of edges is half the sum of all vertices degrees.

$$
\text{edges } = \frac{1}{2} \sum_{v \in V} deg(v)
$$

#### Proof: 
The sum counts each edge twice.

### Odd Degree Vertices

#### Claim
In any undirected graph, the number of odd degree vertices is even.

#### Proof
Adding any two odd numbers results in an even number. Adding an odd and even number is odd. With this in mind, knowing that the sum of all vertex degrees is even,there must be even number of odd degree vertices, because sum of odd number of odd numbers is odd.

### Degree 1 vertices

#### Claim

Suppose $G$ is an acyclic graph. Then $G$ must have a vertex of degree less than or equal to 1.

$$
G = (V, E) \text{ is acyclic} \to \exists v \in V, deg(v) \le 1
$$

#### Proof

Proof by contradiction.

Assume $\forall v \in V, d(v) \ge 2$.

Consider a path from $v_1$ to $v_n$. At $v_i$, we choose the next vertex such that isnt an edge to $v_{i - 1}$, which is possible because $deg(v_i) \ge 2$. The first time we see a repeated vertex $v_j = v_i$, we get a cycle. Since $G$ has finitely many edges, at some point you need to either terminate your traversal, or loop back and repeat a node.

### Number of edges

Let $G = (V, E)$ be a graph with $n = |V|$ vertices and $m = |E|$ edges.

Claim: $m \le (n \choose 2) = \frac{n(n - 1)}{2} = O(n^2)$

Proof: Each vertex can be connected to at most $n - 1$ other vertices. Thus, the total number of edges is at most $n(n - 1)/2$.

### Sparsity

A graph is called sparse if $|E| << |V|^2$, and dense otherwise. Sparse graphs are common in applications like social networks, the web, planar graphs, etc.

Technically, $O(n + m) = O(n^2)$, but in practice, $O(n + m) = O(n)$ for sparse graphs.

### Storing Graphs

#### Adjacency Matrix

A matrix $A$ where $A_{ij} = 1$ if there is an edge between $v_i$ and $v_j$, and $0$ otherwise.

- Pro: $O(1)$ time to check if there is an edge between two vertices.
- Con: $O(n^2)$ space.
- Con: $O(n)$ time to find all neighbors of a vertex.

Good for dense graphs.

#### Adjacency List

A list of lists, where each vertex has a list of its neighbors.

- Pro: $O(1)$ time to find all neighbors of a vertex.
- Pro: $O(n + m)$ space.
- Con: $O(n)$ time to check if there is an edge between two vertices.

Good for sparse graphs.

```python

def build_adjacency_list(n: int, edges: List[Tuple[int, int]]) -> List[List[int]]:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj

def build_adjacency_matrix(n: int, edges: List[Tuple[int, int]]) -> List[List[int]]:
    adj = [[0] * n for _ in range(n)]
    for u, v in edges:
        adj[u][v] = 1
        adj[v][u] = 1
    return adj

```
