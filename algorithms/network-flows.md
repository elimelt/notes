---
title: Network Flow Algorithms and Applications in Graph Theory
category: Algorithms
tags: max flow min cut, ford-fulkerson algorithm, bipartite matching, vertex cover, independent set
description: Comprehensive overview of network flow algorithms, including Max Flow/Min Cut and Ford-Fulkerson. Covers applications in bipartite matching, vertex cover, and independent set problems. Includes proofs, algorithms, and problem-solving techniques for graph theory concepts.
---

# Network Flow - Max Flow and Min Cut

## Max Flow/Min Cut

**Max Flow** and **Min Cut** are two important concepts in graph theory with wide reaching applications. Many problems are reduced to either of them, such as...

- **Transportation Networks**: flow of goods, data, or people through a network, i.e. all kinds of traffic flow 
- **Telecommunications**: flow of data through a network. Min cut is exactly the number of edges you need to remove to fully disconnect servers $s$ and $t$
- **Image Segmentation**: partitioning an image into regions
- **Data Mining**: clustering and classification

Typically, you use min cut when you are looking for some partition of objects into two sets such that some cost is minimized. You use max flow typically in problems involving optimal routing. Note that if there is some natural ordering associated with objects, you should also try dynamic programming. Additionally, problems on trees can sometimes be solved with greedy (using induction on the leaves), or dynamic programming on sub-trees.

Given a graph $G$ and vertices $s, t$, the min flow/max cut problem is to find the minimum capacity of a flow from $s$ to $t$ in the graph. This is equivalent to finding the maximum capacity of a cut that separates $s$ from $t$.

We have the following definitions:

- Given a cut $(A, B)$, the capacity, $cap(A, B) = \sum_{u \in A, v \in B, (u, v) \in E} c(u, v)$

## Ford Fulkerson Algorithm

The Ford Fulkerson algorithm is a method for solving the min flow/max cut problem. An **augmenting path** is a path from $s$ to $t$ in the residual graph $G_f$ with positive capacity. The algorithm works by finding augmenting paths and increasing the flow along them until no more augmenting paths exist. Once no more augmenting paths exist, the flow is at its maximum, and the minimum cut is found by finding the set of vertices reachable from $s$ in the residual graph.

A residual graph $G_f$ is a graph that represents the remaining capacity of edges in the original graph. If an edge $(u, v)$ has capacity $c$, and $f(u, v)$ is the flow along that edge, then the residual capacity is $c - f(u, v)$. We represent residual edges as an edge traversable in the opposite direction to the way capacity flows, and keep a forward edge for the remaining capacity.

If all edges along an augmenting path are in the forward direction, we can increase the flow by the minimum capacity of the path, updating the residual graph accordingly.

On the other hand, if an edge is in the reverse direction, we can decrease the flow along that edge by the minimum capacity of the path. This is equivalent to increasing the flow along the reverse edge.

```python
def augment(G, f, c, P):
  min_cap = min(c[u][v] - f[u][v] for u, v in P)
  for u, v in P:
    if v in G[u]:
      f[u][v] += min_cap
      c[u][v] -= min_cap
      c[v][u] += min_cap
    else:
      f[v][u] -= min_cap
      c[v][u] += min_cap
      c[u][v] -= min_cap
  return f

def find_augmenting_path(G, s, t):
  stack = [(s, [s])]
  while stack:
    curr, path = stack.pop()
    if curr == t:
      return path
    for v in G[curr]:
      if v in path:
        continue
      stack.append((v, path + [v]))
  return None

def ford_fulkerson(G, s, t, c):
  Gf = {u: {v for v in G[u]} for u in G}
  f = {u: {v: 0 for v in G[u]} for u in G}

  while True:
    P = find_augmenting_path(Gf, s, t)
    if not P:
      break
    f = augment(G, f, c, P)
  return f
```

### Running Time

Assume that all capacities are integers between $1$ and $C$. Invariantly, every flow value $f(e)$ and every residual capacity $c_f(e)$ remains an integer throughout the algorithm.

**Theorem**: The algorithm terminates after at most $v(f^*) < nC$, if $f^*$ is an optimal flow.

This is because only one vertex ($S$) actually produces flow. Therefore, we have a tight upper bound on $v(f^*)$ of $(n - 1)C$. Each iteration of the algorithm increases the value of the flow by at least $1$ (since flows are integers).

Since at each iteration, we need to find an augmenting path via DFS, we have an overall runtime of $O(mnC)$, or more generally, $O(mv(f^*))$

## Maximum Matching

Given an undirected graph $G = (V, E)$, find the matching $M \subseteq E$ with largest cardinality. Note that in a matching is a set of edges where each vertex touches at most one edge in $M$.

In general, you can solve this in polynomial time, but I won't go into detail. Instead, I cover the case where $G$ is bipartite.

### Bipartite Maximum Matching

Given an undirected bipartite graph $G = (X \cup Y, E)$, find the maximum matching $M$.

Add vertices $s, t$, with edges $(s, v)$ of capacity $1$ for $v \in X$, and $(u, t)$ of capacity $1$ for $u \in Y$. All other edges have weight $\infty$. Orient all edges from $s \to t$, i.e. all edges between $X$ and $Y$ have direction $v \to u$.

Find the maximum flow from $s \to t$. The maximum flow is the maximum matching, and the minimum cut is the minimum vertex cover.

**Proof**: Let $M$ be a matching in $G$, and $f$ be the value of the maximum **integer** flow some $H$ in the constructed graph. We need to prove $|M| = f$.

$|M| \le f$: We need to find some flow that satisfies the preceding constraint. Since all flows are a candidate for max flow, and the max flow must be $\ge$ any other, showing any flow satisfies it is sufficient.

- For every edge $(u, v) \in M$, set $f(s \to u) = f(u \to v) = f(v \to t) = 1$, and the rest to $0$.
- The flow is feasible since $f(e) \le c_e = 1 \forall e$, and the conservation of flow holds.
- $v(f) = l = $ total capacity out of $S$.

$f \le |M|$: We need to use $v(f) = k$ to construct a matching $|M| = k$.

- Since all capacities of edges are integers, such an $f$ exists.
- Since $\forall e, c_e = 1$, $\forall e, f(e) \in \{0, 1\}$. Further, each vertex in $X$ takes at most $1$ unit of flow from $s$, and each vertex in $Y$ can output at most $1$ unit of flow.
- Each path can support up to $1$ unit of flow, and all of them are of the form $s, v_x, v_y, t$, for vertices $v_x \in X, v_y \in Y$. Therefore, with a max flow value $v(f) = k$, we can create a matching $M$, where each edge $(v_i, v_j) \in M$ corresponds to a unique path of our flow.
- So we have a matching with $|M| = k$, meaning $f \le |M|$.

## Foreground/Background Segmentation

Label each pixel of an image as foreground or background. $V = $ set of pixels, and $E =$ neighboring pixels.

- $a_i \ge 0$ is the likelihood of pixel $i$ being in the foreground
- $b_i \ge 0$ is the likelihood of pixel $i$ being in the background
- $p_{i,j} \ge 0$ is the penalty for labeling one of $i$ and $j$ as foreground and the other as background, i.e. the penalty for boundaries of the the two regions

- **Accuracy**: If $a_i > b_i$ in isolation, prefer to label $i$ in the foreground.
- **Smoothness**: If many neighbors of $i$ are labeled foreground, we should be inclined to label $i$ as foreground as well.

Find a partition $(A, B)$ that maximizes...

$$
\sum_{i \in A} a_i + \sum_{j \in B} b_j - \sum_{(i, j) \in E, i \in A, j \in B} p_{i, j}
$$

We proceed to a solution that uses min-cut. Since this is a maximization problem, but min-cut is a minimization problem, we can just multiply our scoring function by $-1$, so we are now trying to minimize...

$$
\sum_{(i, j) \in E, i \in A, j \in B} p_{i, j} - \sum_{i \in A} a_i - \sum_{j \in B} b_j
$$

Additionally, working with negatives sucks, so we can get rid of them by adding a constant value to make our function positive.

$$
\sum_{(i, j) \in E, i \in A, j \in B} p_{i, j} - \sum_{i \in A} a_i - \sum_{j \in B} b_j + \sum_{i \in V} a_i + \sum_{j \in V} b_j
$$

Since $V = A \cup B$ and $A \cap B = \emptyset$, it is equivalent to...

$$
\sum_{(i, j) \in E, i \in A, j \in B} p_{i, j} + \sum_{i \in B} a_i + \sum_{j \in A} b_j
$$

Add vertices $s$ and $t$, with an edge weight of $a_i$ between all edges $(s, i)$, and an edge $(j, t)$ with a weight of $b_j$. Then, make all edges $(i, j)$ have a weight $p_{i, j}$. Then the min-cut of this graph would be the minimization of our objective function, giving us the optimal sets $A, B$.

## P1 - Count Disjoint Paths

Given an undirected graph $G = (V, E)$ and a set of vertices $S \subseteq V$ and a disjoint set of vertices $T \subseteq V$ , i.e., $S \cap T = \emptyset$. Design a polynomial time algorithm that outputs the maximum number of vertex disjoint paths between vertices of $S$ and $T$ (note that every vertex in $S$ and every vertex in $T$ can be in at most one path).

**Algorithm**:

- Given $G = (V, E)$, and $S, T$
  - Construct a directed graph $G'$ with all undirected edges $(u, v) \in E$ corresponding to two directed edges $(u, v), (v, u) \in E$. Additionally, add two vertices $s$, $t$ to $V'$, and an edge $(s, v)$ and $(u, t)$ for all $v \in S$, $u \in T$.
  - Run the algorithm from section for the maximum number of vertex disjoint paths in an unweighted directed graph given $s, t$.

**Correctness**:

Let $G = (V, E)$ be an undirected graph, and $S$, $T$ be disjoint subsets of $V$.

Since we have an algorithm from section to find the number of vertex disjoint paths from $s$ to $t$ in a directed graph containing vertices $s$, $t$, I will just show that I can construct such a directed graph $G'$ from $G$, and that the number of vertex disjoint paths in $G'$ from $s$ to $t$ is equal to the number of vertex disjoint paths in $G$ from vertices in $S$ to vertices in $T$.

My algorithm first adds both a forward and backward directed edge for every edge in $E$, since $G$ is undirected and we therefore need to consider paths taking either direction of each directed edge. Note that the vertices of each path considered by the algorithm from section must be disjoint (not counting $s$ and $t$), so only one of these edges will ever be used in a path counted by the algorithm in section, so it is safe to add these additional edges without ever counting additional paths.

Furthermore, I add two vertices $s$ and $t$ to $V'$, and add a directed edge from $s$ to every vertex in $S$, and a directed edge from every vertex in $T$ to $t$. This is to form a bijection between $A$, the maximal set of vertex disjoint paths I find in $G'$ from $s \to t$, and $B$, the maximal set of vertex disjoint paths that start at a vertex in $S$ and end at a vertex in $T$. In particular, letting $s' \in S$ and $t' \in T$ be arbitrary vertices from their respective sets, we have paths of the following forms:

- $a_i = s, s', \ldots, t', t$ for all paths $a_i \in A$
- $b_i = s', \ldots, t'$ for all paths $b_i \in B$

All paths in $A$ must have some $s'$ as their second vertex, since the only edges leaving $s$ are those going to vertices in $S$. Similarly, all paths in $A$ must have their second-to-last vertex as some $t'$, since the only edges incident to $t$ are those coming from vertices in $T$.

By definition of the algorithm from section, paths in $A$ are vertex disjoint not counting $s$ and $t$, and $A$ contains the maximal number of such existing paths, or in other words, there are no additional vertex disjoint paths from $s \to t$ that can be added, nor other ways to choose vertex disjoint paths to end up with a larger set $A$.

Therefore, by creating the set $B$ by taking each $a \in A$ and removing the starting and ending vertices $s$ and $t$, we also have vertex disjoint paths, since removing elements of disjoint sets will never make them not disjoint. Furthermore, since $A$ is of maximal size, there could not exist any other paths from $s \to t$ that would be vertex disjoint. Therefore, for $B$ to be maximal sized, we must have $|B| = |A|$. To show this more concretely, I will show that $|B| \le |A|$ and $|A| \le |B|$.

- $|B| \le |A|$: Since $A$ is the maximal set of vertex disjoint paths from $s \to t$, there can be no additional paths that are vertex disjoint with the paths in $A$, nor any greater such sets. Suppose for the sake of contradiction that $|B| > |A|$. Then, we can construct a set $A'$ with $|A'| = |B|$ by adding $s$ to the beginning of each path in $B$, and $t$ to the end of each path in $B$. We are able to do this because we added an edge from $s \to s'$ for $s' \in S$ and $t' \to t$ for $t' \in T$. However, we would then have found a set of vertex disjoint paths from $s \to t$ that is larger than $A$, which is a contradiction to $A$ being maximal.

- $|A| \le |B|$: Suppose for the sake of contradiction that $|A| > |B|$. Since we defined $B$ as the maximal set of vertex disjoint paths between vertices in $S$ and $T$, we must not be able to find a greater set $B$. However, if $|A| > |B|$, we could construct a set $B'$ as follows: for each path $a \in A$, remove the first and last vertex to make $a'$. Since each $a$ was vertex disjoint, each $a'$ will also be vertex disjoint, and so we've created a set of vertex disjoint paths from vertices in $S$ to vertices in $T$ (since the second and second to last vertices of $a$ must be in $S$ and $T$ respectively). Therefore, $B$ was not maximal, and we have a contradiction.

**Running Time**: We can construct $G'$ in $O(|V| + |E|)$, since we only need to visit each edge of each vertex in our graph for duplicating/orienting edges, and an additional $O(|S| + |T|) = O(|V|)$ to add $s$, $t$, and edges to vertices in $S$ and $T$. Then, we simply need to run the algorithm from section, which takes $O(|V||E|)$, so our total running time is $O(|V||E|)$, which is polynomial.

## P2 - Number of Disjoint Paths

Given a directed unweighted graph $G = (V, E)$. Suppose that there are $k$ edge disjoint paths from $s$ to $t$ and there are $k$ edge disjoint paths from $t$ to $u$ for vertices $s, t, u \in V$ . Prove that there are $k$ edge disjoint paths from $s$ to $u$.

**Proof**:

Let $G = (V, E)$ be a directed unweighted graph, and $s, t, u \in V$ be vertices such that there are $k$ edge disjoint paths from $s \to t$ and $k$ edge disjoint paths from $t \to u$. We wish to show that there are $k$ edge disjoint paths from $s \to u$.

Construct a graph $G'$ by adding vertices $w, x, y, z$ with edges $(w, s), (t, x), (y, t), (u, z)$, each having capacity $k$, and the rest of the edges having capacity $1$. We have a maximum flow of $k$ from $w \to x$, since each added edge can support a flow of up to $k$, and we can send $1$ unit of the $k$ flow going into $s$ through the $k$ edge-disjoint paths from $s$ to $t$, and then all $k$ units of flow going into $t$ through the edge $(t, x)$. Similarly, we have a max flow from $y \to z$ of $k$, since we can send $k$ units of flow from $y$ into $t$, and then $1$ unit of flow from $t$ into $u$ through the $k$ edge disjoint paths from $t$ to $u$, and then all $k$ units of flow from $u$ into $z$. Notice that the conservation of flow holds for all of these vertices, since $s$ receives and outputs $k$ units of flow, as does $t$ and $u$, and the remaining vertices each receive and output $1$ unit of flow.

Now, in order to show that there are at least $k$ edge disjoint paths from $s \to u$, we need to find a flow that sends $k$ units of flow from $w \to z$, and equivalently, directly from $s \to u$. Since there are at least $k$ edge disjoint paths from $s \to t$, we have at least $k$ edges leaving $s$ and entering $t$, and similarly, we have at least $k$ edges leaving $t$ and entering $u$. Otherwise, we wouldn't have enough outgoing or incoming edges to construct said $k$ edge-disjoint paths, since each path leaving $s$ or $t$ or entering $t$ or $u$ must do so by a unique edge. Therefore, instead of routing $k$ units of flow from $y$ into $t$, and from $t$ into $x$, instead route the $k$ incoming units of flow into $t$ from the $k$ capacity $1$ edges into $t$, and route the $k$ units of flow out of $t$ through the $k$ outgoing edges of capacity $1$ from $t$.

We therefore have a flow from $w \to z$ of capacity $k$. Since $w$ is only connected to $s$ (with an edge of capacity $k$), and $z$ is only connected to $u$ (with an edge of capacity $k$), and all edges in the middle of said flow have capacity $1$, we must route the $k$ units of flow through $k$ edge disjoint paths from $s$ to $u$, since each such path can only support $1$ unit of flow. Note that the edges in paths between $s$ and $t$, and $t$ and $u$ are not necessarily disjoint, but the edges between $s$ and $u$ that we routed the aforementioned flow through must be disjoint, since that is the only way to route $k$ units of flow through edges all with capacity $1$.

## P3 - Minimum Vertex Cover, Maximum Independent Set (Bipartite)

In this exercise we give a polynomial time algorithm to find the minimum vertex cover and maximum independent set in a bipartite graph $G = (X, Y, E)$.

### (a) Construct H

Let $H$ be a directed graph with vertices $X \cup Y$ with each edge $e = (u \to v) \in E$, where $u \in X$ and $v \in Y$ with $c_e = \infty$. Add vertices $s, t$, and edges $e_s = (s \to u)$ $\forall u \in X$, and $e_t = (v \to t)$, $\forall v \in Y$ with $c_{e_s} = c_{e_t} = 1$. Let said edges $e_s$ and $e_t$ form the sets $E_s$ and $E_t$ respectively.

### (b) Construct S

Let $(A, B)$ be a min s-t cut in $H$. I will construct a vertex cover $S \subseteq X \cup Y$ such that $cap(A, B) = |S|$. Define the set $A_X, B_X, A_Y, B_Y$ as $A_X = A \cap X$, $B_X = B \cap X$, $A_Y = A \cap Y$, $B_Y = B \cap Y$ respectively.

The following lemmas will become useful:

- *(1)*: the capacity of the min s-t cut of $H$ is upper bounded by $|X|$
  - This is because the maximum flow introduced into the system by $s$ is $c_{e_s} = 1$ for each vertex in $X$.
- *(2)*: All $e_s \in E_s, e_t \in E_t$ have capacity $1$ (by construction).
- *(3)*: No edges from $A_X \to B_Y$ exist
  - By *(1)*, we know $cap(A, B)$ is finite. Since all edges $e \notin E_s \cup E_t$ have $c_e = \infty$, such an edge would imply an infinite capacity between $A$ and $B$, which contradicts *(1)*.
- *(4)*: $cap(A, B) = |B_X| + |A_Y|$ (proven in lecture)
  - By *(3)*, and the fact that $G$ was bipartite and we therefore have no edges between vertices in $Y$, we have that all edges from $A \to B$ must be from $A_Y \to B_X$.
  - By *(2)*, we have that each $v \in X$ and $u \in Y$ are limited by conservation of capacity, since each have a single incoming and outgoing edge in $E_s$ and $E_t$ respectively.
  - Therefore, we have $cap(A, B) = |B_X| + |A_Y|$, since there are $|B_X|$ many edges of capacity $1$ into $t$, and $|A_Y|$ many edges of capacity $1$ into $s$.

By *(3)*, all edges of $G$ must fall into sets $E_1$ between $A_X, A_Y$, $E_2$ between $A_Y, B_X$, and $E_3$ between $B_X, B_Y$.

We can therefore select a vertex cover of $S = B_X \cup A_Y$, since $A_Y$ covers $E_1$ and $E_2$, and $B_X$ covers $E_2$ and $E_3$. By *(4)*, we have $|S| = |B_X| + |A_Y| = cap(A, B)$. Note that this isn't necessarily the minimum vertex cover, but it is a vertex cover of size $cap(A, B)$.

### (c) Construct (A, B)

Let $S$ be a minimal vertex cover of $G$. I will construct a min s-t cut $(A, B)$ in $H$ such that $|S| = cap(A, B)$.

Since $S$ is a vertex cover, it must contain at least one vertex from each edge in $E$. Let $S_X = S \cap X$, and $S_Y = S \cap Y$. Since $G$ is bipartite, we have that each edge between $X$ and $Y$ in $G$ contains some vertex in $S$.

To construct $(A, B)$ with $cap(A, B) = |S|$, we must choose $|S|$ vertices from $S_X$ to route $1$ unit of flow through. We can then choose $|S|$ distinct arbitrary vertices from $S_Y$ which are neighbors of the previously chosen vertices to route the $|S|$ units of flow through.

We know that $|S| \le |X|$ and $|S| \le |Y|$, since if we were to cover all of either $X$ or $Y$ in $S$, we would have a candidate vertex cover. This argument holds because $G$ is bipartite and therefore only has edges between $X$ and $Y$, and we have an upper bound because $|S|$ is minimal.

Additionally, without loss of generality (since we could just exchange $X$ for $Y$ in $G$ when constructing $H$), suppose $|S_X| \ge |S_Y|$. We can choose all of $S_X$ to route $|S_X|$ units of flow through, and then additionally for each $u \in S_Y$ we can pick a neighbor of $u$, $v' \notin S_X$ to route an additional $|S_Y|$ units of flow through to each $u$. I claim that such a $v'$ always exists, which I will prove by contradiction.

Suppose $\exists u \in S_Y$ such that $N(u) \subseteq S_X$. Then we would have already covered all edges $(v', u)$ for $v' \in N(u)$, and so we could remove $u$ from our set cover to make a smaller set cover $S'$. However, $S$ is a minimal set cover, so this is a contradiction.

Therefore, we can create a set of edges $E_{S_X} = \{(u, v) \in E: u \in S_X, v \in Y \setminus S_Y\}$, and $E_{S_Y} = \{(u, v) \in E: u \in S_Y, v \in X \setminus S_X\}$, and since these edges are both vertex disjoint and edge disjoint by construction, we have $|E_{S_Y}| + |E_{S_X}| = |S|$.

Letting $E_S$ be the set of edges $E_{S_X} \cup E_{S_Y}$ directed from $X \to Y$, we can create an s-t cut by cutting $H$ along all edges in $E_S$, along with edges from $s$ to vertices in $X$ which were not involved with any edge in $E_S$. Note that these two sets of edges we cut disconnect paths which form a partition of paths from $s \to t$, namely those which contain a vertex involved in some $E_S$, and those which don't. Therefore, this is a feasible s-t cut, since all paths from $s$ to $t$ disconnected.

 Taking $(A, B)$ to be the cut described above, we have exactly $|S|$ units of flow leaving $s$, and by extension $A$, and also entering $t$, and by extension $B$. Therefore, $cap(A, B) = |S|$.

 ### (d) Design the algorithm

- Given a bipartite graph $G = (X, Y, E)$
  - Construct $H$ as described in (a), but instead of using edges with capacity $\infty$ between $X$ and $Y$, use edges with capacity $n + 1$
  - Find the min s-t cut $(A, B)$ in $H$ using ford-fulkerson
  - Let $B_X = B \cap X$, $A_Y = A \cap Y$
  - Return $S = B_X \cup A_Y$

**Correctness**:

As mentioned in lecture, adjusting the edge capacities that were originally $\infty$ to $n + 1$ works here, since we still have the desired property that no edges could exist between $A_X \to B_Y$, since this would still respect our upper bound of $|X|$ on the capacity of the min s-t cut.

From (c), we know that given a min s-t cut $(A, B)$, we can construct a vertex $S$ with $|S| = cap(A, B)$. Suppose for the sake of contradiction that $S$ wasn't minimal, i.e. there exists some min vertex cover $S'$ with $|S'| < |S|$. From (b), we know we can construct an s-t cut $(A', B')$ with $cap(A', B') = |S'|$. Then we have $|S'| = cap(A', B') < cap(A, B) = |S|$, and so $cap(A', B') < cap(A, B)$. However, $(A, B)$ could not have been a min s-t cut, which is a contradiction.

Therefore, we have that for any bipartite graph $G = (X, Y, E)$ and $H$ constructed as described in (a), we can find a min s-t cut $(A, B)$ in $H$, and construct a min vertex cover $S$ of $G$ such that $|S| = cap(A, B)$, simply by taking the elements of $B \cap X$ and $A \cap Y$.
 as $S$ as described in (b) and written in my algorithm.

**Running Time**

For a bipartite graph $G = (X, Y, E)$ in adjacency list form with $|X| + |Y| = n$ and $|E| = m$, we can create $H$ in $O(n + m)$, since we only need to add two additional vertices, along with $n$ additional edges between them, also taking into account the extra initialization of edge capacities which would only involve $O(m)$ operations.

Then, since we have integer capacities, we can run ford-fulkerson on $H$ to find the min s-t cut, which will terminate in at most $nC$ iterations, where $C = n + 1$ here, each iteration taking $O(m)$ time to compute the augmenting path, for a total runtime of $O(mn^2)$.

Since ford-fulkerson outputs the min cut $(A, B)$, each of which are sets with size $O(n)$, and additionally $X$ and $Y$ are sets with size $O(n)$, assuming an efficient implementation of intersection using a hash set, we can compute $B_X \cap A_Y$ in $O(n)$, and additionally $S$ in $O(n)$. Even with an inefficient implementation using a linear structure, we could perform the intersections in $O(n^2)$, and the union in $O(n)$.

Therefore, the total runtime is $O(mn^2)$, which is polynomial.

## P4 - Knights

Given an $n \times n$ chess board where some cells are removed. Design a polynomial time algorithm to find the maximum number of knights that can be placed on this board such that no two knights attack each other.

**Algorithm**:

- Given $X$, the set of pairs $(i, j)$ that correspond to the cells that are removed, and $n$ be the size of the chess board.
  - Create an undirected graph $G = (V, E)$, where $V$ is $[n]^2 \setminus X$, i.e. the pairs $(i, j)$ that are not removed
  - Add edges $((i, j), (i', j'))$ to $G$ such that knights placed on cells $(i, j)$ and $(i', j')$ attack each other. To compute this, for each $(i, j) \in [n]^2$, add edges to all cells $(i', j')$ that are $2$ cells away horizontally and $1$ cell away vertically or $2$ cells away vertically and $1$ cell away horizontally, but that satisfy $(i', j') \in V$. Given such a cell $(i, j)$, the cells to add edges between would be those that satisfy the predicate...
    - $(i', j') \in V \land (|i - i'| = 2 \land |j - j'| = 1 \lor |i - i'| = 1 \land |j - j'| = 2)$
  - Find the minimum vertex cover $S$ of $G$ using the algorithm from P3.
  - Return $|V| - |S|$

**Running Time**:

To create $G$, we first create our set of vertices $V$, which can be done in $O(n^2)$ (assuming we can check $(i, j) \in X$ in $O(1) by using an $n \times n$ grid of boolean values).

Next, in order to compute $E$, we once again need to iterate through all $n^2$ cells, and for each cell, we need to check at most $8$ cells that could potentially attack the current cell, only adding an edge between them if we haven't done so before. Checking the $8$ cells is $O(1)$, so it takes a total time of $O(n^2)$ to compute edges.

Our graph therefore has a size of $|V| \le n^2 = O(n^2)$, and $|E| \le 8n^2 = O(n^2)$.

We can then find the maximum independent set of $G$ by first calculating the minimum vertex cover $S$ in $O(|V|^2|E|) = O(n^6)$, and then the M.I.S as $I = V \setminus S$. However, since $S \subseteq V$, and we only need to compute the maximum number of placements, we can return $|V| - |S|$ which can be done in constant time.

Therefore, our total running time is $O(n^6)$, which is polynomial.

**Proof**:

Let $n$ be the size of the chess board, and $X$ be the set of pairs $(i, j) \in [n]^2$ that correspond to the cells that are removed. We construct a graph $G = (V, E)$, with $V = (i, j) \in [n]^2 \setminus X$, and $E$ being the set of edges between each pair of vertices that correspond to cells that are $2$ cells away horizontally and $1$ cell away vertically or $2$ cells away vertically and $1$ cell away horizontally.

By virtue of its construction, $G$ has a vertex for each cell we could place a knight on, since it contains each $(i, j) \in [n]^2$ which wasn't removed. Furthermore, the set of edges corresponds to each pair of cells that would attack each other if knights were placed on them, since the cells that a knight placed in $(i, j)$ would attack are exactly those that are $2$ cells away horizontally and $1$ cell away vertically or $2$ cells away vertically and $1$ cell away horizontally, but that are still within the board and not removed, i.e. pairs $(i', j') \in [n]^2 \setminus X$, or more simply $(i', j') \in V$, and that satisfy either $|i - i'| = 2, |j - j'| = 1$ or $|i - i'| = 1, |j - j'| = 2$.

Let $I \subseteq V$ be the maximum independent set of $G$, and $k$ be the maximum number of knights that can be placed on the board such that no two knights attack each other. I claim that $|I| = k$, which I will prove by showing that $|I| \le k$ and $|I| \ge k$.

- $|I| \le k$: Since $I$ is an independent set, no two vertices in $I$ are adjacent. Therefore, no two knights placed on cells corresponding to vertices in $I$ would attack each other. Since we defined $k$ as the maximum number of knights that can be placed on the board such that no two knights attack each other, we have $|I| \le k$.
- $|I| \ge k$: Suppose for the sake of contradiction that $|I| < k$.  Then there must exist some set of valid placements $P = (i_1, j_1), \ldots, (i_k, j_k)$ in which we can place knights such that none of the knights attack each other. By construction of $G$, we would therefore have no edges between any of the vertices corresponding to pairs in $P$, and so said vertices would form an independent set, say $I'$. Since $|I| < k$, we have $|I'| > |I|$, which is a contradiction to $I$ being a maximum independent set.
