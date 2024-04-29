# Divide and Conquer

## Master Theorem

Given any recurrence of the form $T(n) = a T(\frac{n}{b}) + c n^k$ for all $n > b$, we have:

- If $a > b^k$, then $T(n) = \Theta(n^{\log_b a})$
- If $a < b^k$, then $T(n) = \Theta(n^k)$
- If $a = b^k$, then $T(n) = \Theta(n^k \log n)$

## Root Finding

Given a continuous function $f$ and two points $a < b$ such that $f(a) \cdot f(b) < 0$, there exists a root of $f$ in the interval $[a, b]$ by the **intermediate value theorem**. Since said root may be irrational, we aim to approximate it with an arbitrary precision $\epsilon$.

- **Algorithm**: $Bisect(a, b, \epsilon)$
  - If $b - a < \epsilon$, $a$ is a suitable approximation
  - Otherwise, calculate the midpoint $m = (a + b)/2$
  - If $f(m) \le 0$ then return $Bisect(m, b, \epsilon)$
  - else return $Bisect(a, m, \epsilon)$
- **Time**: $T(n) = T(\frac{n}{2}) + O(1) = O(\log(\frac{b - a}{\epsilon}))$
- **Proof**:
  - $P(k) =$ For any $a, b$ such that $k\epsilon \le |a - b| \le (k + 1)\epsilon$, if $f(a)f(b) \le 0$, then we find an $\epsilon$ approx to a root using $\log k$ queries to $f$.
  - $P(1)$: Output $a + \epsilon$, since the whole interval is at most $epsilon$. This requires $0$ calls to $f$.
  - Suppose $P(k)$ and consider an arbitrary $a$, $b$ s.t. $2k\epsilon \le |a - b| \le (2k + 1)\epsilon$.
  - If $f(a + k\epsilon) = 0$, output $a + k\epsilon$.
  - If $f(a)f(a + k\epsilon) < 0$, solve on the interval $[a, a + k\epsilon]$. By I.H. this takes at most $\log(k)$ queries of $f$.
  - Otherwise, we have $f(b)f(a + k\epsilon) < 0$, since $f(a)f(b) < 0$ and $f(a)f(a + k\epsilon) \ge 0$. Solve the interval $[a + k\epsilon, b]$.
  - In any case, we used at most $\log(k) + 1 = $\log(2k)$ queries to $f$.


## kth Smallest Element

- **Algorithm**: $f(S \in \mathbb{R}^n, k \in \mathbb{R})$
  - Select an approximate median element $w$ using median of $\frac{n}{5} medians with subarrays of size $5$
  - Partition each element into three sets, $S_{>}, S_{<}, S_{=}$
  - If $k \le |S_{<}|$, recurse on $f(S_{<}, k)$
  - Else, if $k \le |S_{<}| + |S_{=}|$, return $w$
  - Else, recurse on $f(S_{>}, k - |S_{<}| - |S_{=}|)$# Graphs

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

- To find, initialize map of in-degrees for each vertex, and a queue of vertices with in-degree 0. Then, while the queue isn't empty, remove a vertex, adding it to the ordering, and decrement its neighbors in-degree. If any of them become 0, add them to the queue.

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
  - If the label of a root is $k$, there are at least $2^k$ elements in the set.# Interval Scheduling/Partitioning

## Scheduling the max number of intervals

- **Algorithm:** sort by finish time and select the next compatible interval
- **Proof**: Greedy stays ahead, by induction
  - *Claim*: Greedy algorithm is optimal
  - **Lemma**
    - $P(r)$: For greedy choices $g_1, \ldots, g_n$ and optimal choices $k_1, \ldots, k_m$, $f(g_r) \le f(k_r)$
    - $P(1)$: $g_1$ is chosen to have the minimum finish time, so $f(g_1) \le f(k_1)$
    - Suppose $P(r)$. Since $f(g_r) \le f(k_r) \le s(k_{r + 1})$, $k_{r + 1}$ is among the candidates considered for $g_{r + 1}$. Of those candidates, it picks the minimum finish time, so $f(g_{r + 1}) \le f(k_{r + 1})$.
  - By this lemma, we must have $n \ge m$, since since otherwise $k_{n + 1}$ is in the set of candidates for $g_{n + 1}$.

## Partitioning intervals into the minimum number of sets

- **Algorithm**: sort intervals by start time, adding them to **any** compatible set. If no set is compatible, create a new one
- **Proof**: exploit structural property
  - *Claim*: greedy algorithm is optimal
  - Let $d$ be the number of sets the greedy algorithm allocates. The $d$th set, $S_d$ is allocated because we had to assign some interval, $I_i$, that was not compatible with any of the $d - 1$ previous sets.
  - Since we sorted by start time, all intervals $I_j \in S_1 \cup \ldots \cup S_{d - 1}$ have $s(I_i) \ge s(I_j)$. Thus, we have at least depth $d$ intervals, and so all valid partitions must have $\ge d$ sets.
