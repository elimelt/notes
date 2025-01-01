---
title: Breadth First Search Algorithm Implementation and Analysis
category: algorithms
tags:
  - graph-traversal
  - shortest-paths
  - graph-theory
  - complexity-analysis
description: A comprehensive explanation of the Breadth First Search (BFS) algorithm, including implementation, complexity analysis, and mathematical proofs. The document covers the algorithm's properties for finding shortest paths in graphs and includes Python implementations with detailed theoretical foundations and lemmas about level ordering.
---
# Breadth First Search

Completely explore the vertices of a graph in order of their distance from the starting node.

There are three states of a vertex in BFS:
- **Undiscovered**: The vertex has not been seen yet.
- **Discovered**: The vertex has been seen, but its neighbors have not been explored yet.
- **Explored**: The vertex has been seen and its neighbors have been explored.

### Algorithm

```plaintext
BFS(G, s):
  mark all vertices as undiscovered

  mark s as discovered
  q = queue({s})
  while q is not empty:
    u = poll(q)
    for each edge (u, v) in G:
      if v is undiscovered:
        mark v as discovered
        add v to q
    mark u as explored
```

### Analysis

The outer while loop runs once for each vertex in the graph, and the inner for loop runs once for each edge of the current node. Remembering that the sum of the degrees of all vertices is equal to twice the number of edges in the graph, we have...

$$
O(|V|) + O(\sum_{v \in V} deg(v)) = O(|V| + |E|)
$$

### Lemmas


1. $BFS(s)$ visits a vertex $v$ if and only if there is a path from $s$ to $v$.
2. Edges into then-unexplored vertices form a tree rooted at $s$ (the **BFS spanning tree**).
3. Level $i$ in the tree are exactly all vertices $v$ stuch that the shortest path from $s$ to $v$ has $i$ edges.
4. All non-tree edges from $G$ connect vertices in the same level or adjacent levels.


### Difference in levels

Let $L(v)$ be the level of vertex $v$ in a BFS tree of interest.

Claim:
$$
\forall (x, y) \in E, |L(x) - L(y)| \le 1
$$

Proof:
Suppose $L(x) = i$ and $L(y) = j$. Without loss of generality, assume $x$ is explored before $y$.

Consider the iteration where we process $x$.

Case 1: $y$ is still undiscovered. Since there is an edge between $x$ and $y$, we will discover $y$ in the next iteration, and so $L(y) = i + 1$.

Case 2: $y$ is discovered. Then $y$ is already in the queue, somewhere before $x$. We know $L(y) \ge i$ because $x$ was discovered before $y$. Since the levels are non-decreasing, and $L(x) = i$, we have $L(y) \le i + 1$.

Thus, $|L(x) - L(y)| \le 1$.


### Shortest paths

Claim:

For every vertex $v \in V$ reachable from $s$, $L(v)$ is the length of the shortest path from $s$ to $v$.

Proof:

Let $l(v)$ be the length of the shortest path from $s$ to $v$.

We have that $L(v) \ge l(v)$, since $L(v)$ is the length of a valid path from $s$ to $v$, so the shortest path must be at least as short.

Next, we must show that $L(v) \le l(v)$.

Let $v_0, v_1, \ldots, v_k$ be the shortest path from $s$ to $v$ (with $v_0 = s$).







$$
\forall v \in BFS(G, s), L(v) = \text{length of the shortest path from } s \text{ to } v
$$



```python
from collections import deque

def bfs(graph, start):
    visited = set()
    queue = deque([start])
    visited.add(start)
    while queue:
        vertex = queue.popleft()
        print(vertex)
        for neighbor in graph[vertex]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
```

Or a reusable level-order iterator over a graph using BFS:

```python
from collections import deque

def level_order_traversal(graph, start):
    queue = deque([(start, 0)])
    while queue:
        vertex, level = queue.popleft()
        yield vertex, level
        for neighbor in graph[vertex]:
            queue.append((neighbor, level + 1))
```