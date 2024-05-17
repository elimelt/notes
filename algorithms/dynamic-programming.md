# Dynamic Programming

**Dynamic Programming** is an algorithmic paradigm where you break up a problem into a series of **overlapping** sub-problems, building up solutions to progressively larger subproblems until the original answer is obtained. The key efficiency of DP is to **memoize** the answers to sub problems, often yielding a polynomial time algorithm.

You can design dynamic programming algorithms by induction, with the added construct of somehow memorizing/caching previously solved problems. The key then becomes finding a valid recurrence relation that relates a given instance of the problem to its composite subproblems.

## Weighted Interval Scheduling

**Problem**: Given a set of jobs $J$ with start times $s_i$, finish times $f_i$, and weights $w_i$, find the maximum weight subset of jobs that are compatible with each other.

A naive approach would be to use the following induction:

Given jobs $j_1, j_2, \ldots, j_n$, suppose we can compute the optimum job scheduling for $< n$ jobs.

Then, for any $n$ jobs we can compute $OPT$ as:

- Case 1: $j_n \notin OPT(j_1, j_2, \ldots, j_n)$:
  - Then just return $OPT(j_1, j_2, \ldots, j_{n - 1})$
- Case 2: $j_n \in OPT(j_1, j_2, \ldots, j_n)$:
  - Delete jobs not compatible with $j_n$ and recurse on that new subset of jobs

However, this approach is unfortunately still exponential, since there are potentially $2^n$ possible subsets of jobs to consider. Note that this problem is equivalent to maximum independent set, which is NP-complete. To differentiate our solution from the general (supposed) unsolvability of this problem, we can instead rely on an extra property of our inputs, namely that they are partially order-able.

So we sort by finishing time of each job, which reduces the number of subproblems from $O(2^n) \to O(n)$, i.e. the $n$ possible prefix subsets of our sorted jobs.

**Algorithm**: Given weighted jobs sorted by finish time, suppose we can compute the $OPT$ for $< n$ jobs.

- Case 1: $j_n \in OPT$:
  - So all jobs $i$ that are not compatible with $n$ are not in $OPT$
  - We can find this efficiently, i.e. $p(n) = $ largest index $i < n$ such that $j_i$ is compatible with $j_n$ (binary search based on $s_j, f_i$)
  - Then, we just need to find $OPT(j_1, \ldots, j_{p(n)})$
- Case 2: $j_n \notin OPT$:
  - Then we can return $OPT(j_1, \ldots, j_{n - 1})$
- Our actual $OPT(j_1, \ldots, j_n)$ is then just the maximum of these two cases

```python
# J[i] = (s_i, f_i, c_i)
def max_weighted_interval_subset(J: tuple[int, int, int]) -> int:
    J = sorted(J, key=lambda x: x[1])
    n = len(J)
    memo = [0] * n

    def p(n: int) -> int:
        for i in range(n - 1, -1, -1):
            if J[i][1] <= J[n][0]:
                return i
        return -1

    def dp(n: int) -> int:
        if n < 0:
            return 0
        if memo[n] != 0:
            return memo[n]
        memo[n] = max(J[n][2] + dp(p(n)), dp(n - 1))
        return memo[n]

    return dp(n - 1)
```

## Knapsack Problem

**Problem**: Given $n$ items with weights $w_1, \ldots, w_n$ and values $v_1, \ldots, v_n$, and a knapsack of capacity $W$, find the maximum value subset of items that fit in the knapsack.

In other words, let $I$ be our set of items, and $S \subseteq I$ be the items we select. We want to find the maximum value of $S$ such that $\sum_{i \in S} w_i \le W$

### What are we inducting on?

Assume $P(i, w)$ holds $\forall w \in [0, W]$, and then show $P(i + 1, w)$ holds $\forall w \in [0, W]$. This is a **bottom-up** approach, where we start from the base case and build up to the final solution.

**Algorithm**: Define $OPT(i, w)$ to be the solution for items $1, \ldots, i$ with a knapsack of capacity $w$. Then, we have the following induction:

$$
OPT(i, w) = \begin{cases}
OPT(i - 1, w) & \text{if } w_i > w \\
\max(v_i + OPT(i - 1, w - w_i), OPT(i - 1, w)) & \text{otherwise}
\end{cases}
$$

```python
# recursive
def knapsack_rec(W: int, w: list[int], v: list[int]) -> int:
    n = len(w)
    M = [[-1] * (W + 1) for _ in range(n + 1)]

    def dp(i: int, w: int) -> int:
      if M[i][w] != -1:
        return M[i][w]

      if i < 0 or w == 0:
        M[i][w] = 0
      elif w[i] > w:
        M[i][w] = dp(i - 1, w)
      else:
        M[i][w] = max(v[i] + dp(i - 1, w - w[i]), dp(i - 1, w))
      return M[i][w]

    return dp(n, W)

# iterative
def knapsack_it(W: int, w: list[int], v: list[int]) -> int:
    n = len(w)
    M = [[0] * (W + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        for j in range(1, W + 1):
            if w[i - 1] > j:
                M[i][j] = M[i - 1][j]
            else:
                M[i][j] = max(v[i - 1] + M[i - 1][j - w[i - 1]], M[i - 1][j])

    return M[n][W]
```

## String Building

Given 3 integers $n \geq 1$ and $k_A,k_B \geq 1$, design an algorithm that runs in time polynomial in $n, k_A, k_B$ and outputs the number of length $n$ strings composed of copies of $A, B$ such that no more than $k_A$ copies of $A$ are placed consecutively and no more than $k_B$ copies of $B$ are placed consecutively.

**Algorithm**:

```python
A, B = 0, 1

def num_strings(n, ka, kb):
  dp = [[None, None]] * (n + 1)
  dp[1][A], dp[1][B] = None, None, 1, 1

  if ka == 0 or kb == 0:
    if ka < n and kb < n:
      return 0
    else:
      return 1

  def f(i, c):
    if i == 1:
      return 1

    if dp[i][c] != None:
      return dp[i][c]

    kc = ka if c == A else kb
    notc = A if c == B else B

    if i <= kc:
      dp[i][c] = f(i - 1, notc) + f(i - 1, c)
    else:
      dp[i][c] = sum(f(i - j, notc) for j in range(1, kc + 1))

    return dp[i][c]

  return f(n, A) + f(n, B)
```

**Correctness**: A string is valid if it has $\le k_A$ consecutive $A$ and $\le k_B$ consecutive $B$.

Define $OPT(i, c)$ for $i, k_A, k_B \ge 1$ to be the number of valid strings ending in character $c \in \{A, B\}$. Our base case is $OPT(1, c) = 1$, since there is only one length-1 string ending in $c$.

Assuming we can compute $OPT(i, c)$ for $i < n$, we can compute $OPT(n, c)$ as follows:

$$
OPT(n, c) = \begin{cases}
1 & n = 1 \\
OPT(n - 1, c') + OPT(n - 1, c) & 2 \le n \le k_c \\
\sum_{j = 1}^{k_c} OPT(n - j, c') & n > k_c
\end{cases}
$$

where $c'$ is the other character, and $k_c$ is the maximum number of consecutive $c$ allowed.

For the case where $n > k_c$, we can sum over all possible lengths of the last run of $c$, and then recurse on the remaining string. For a run of $c$ of length $k$ in a string of length $n$, we must have the first $n - k$ characters be some other valid string ending in $c'$, since otherwise our string would end in a run of $c$ of length $> k$. Therefore, we only need to count the number of strings of left $n - k_c \le i \le n - 1$ ending in $c'$, since this is exactly the number of valid strings ending in runs of $1 \le k \le k_c$ $c$.

In the case where $2 \le n \le k_c$, we know that there is no way we'd have a run of $c$ of more than $k_c$, so we can simply count the number of valid strings of size $n - 1$ that either end in a $c$ or a $c'$. Then, we can add a $c$ to the end of all those strings to get our valid strings of length $n$.

Therefore, we cover all cases and $OPT(n, c)$ computes the correct value $\forall n \ge 1$.

To compute the total number of valid strings of length $n$, we simply return $OPT(n, A) + OPT(n, B)$, since all valid strings either end in $A$ or $B$.

### Running Time

We compute $2n$ total values of $OPT(n, c)$, $n$ corresponding to strings ending in $A$, and $n$ ending in $B$. When $n \le k_c$, we can compute our answer in constant time using the values previously computed. When $n > k_c$, we need to sum over $k_c$ previously computed values, which is $O(k_c)$. Therefore, our total running time is at most $O(nk_Ak_B)$.

## Post Office

**Problem**: Interstate highway 5 is a straight highway from Washington all the way to California. There are $n$ villages alongside this highway. Think about the highway as an integer axis, and the position of village $i$ is an integer $x_i$ along this axis. Assume that there are no two villages in the same position, i.e., $x_i \neq x_j$ for $i \neq j$. The distance between two villages $x_i,x_j$ is simply $| x_i - x_j |$.

USPS is interested in building k post offices in some, but not necessarily all of the villages along highway 5, for some $1 \leq k \leq n$. A village and the post office in it have the same position. We want to choose the positions of these post offices so that the sum of the distances from each village to its nearest post office is minimized. Design an algorithm that runs in time polynomial in $n$ and outputs the minimum possible sum of distances to the optimal location for post offices.

**Algorithm**:

```python
def min_dist_td(X, K):
  N = len(X)
  if K >= N:
    return 0

  dp = [[None] * (K + 1) for _ in range(N + 1)]
  for n in range(N + 1):
    for k in range(n, K + 1):
      dp[n][k] = 0

  def f(n, k):
    if n >= k:
      return 0

    if dp[n][k] is not None:
      return dp[n][k]

    dp[n][k] = float('inf')

    if k == 1:
      dp[n][k] = sum(abs(X[i - 1] - X[n - 1]) for i in range(1, n))
    else:
      for i in range(k - 1, n):
        dp[n][k] = min(
            dp[n][k],
            f(i, k - 1) + sum(
              min(
                abs(X[j - 1] - X[n - 1]),
                abs(X[j - 1] - X[i - 1])
              ) for j in range(i + 1, n))
        )

    return dp[n][k]

  def c(i):
    return f(i, k) + sum(abs(X[i - 1] - X[j - 1]) for j in range(i + 1, n + 1))

  return min(c(i) for i in range(k, n + 1))
```

### Correctness

Define $f(n, k)$ to be the minimum sum of distances from the nearest post office of the first $n$ villages to $k$ post offices given the $kth$ post office is placed in village $n$.

When $n \le k$, we have a sum of $0$, since every village has a post office. Then, assuming $f(i, k)$ is correct $\forall k > 0, 0 \le i < n$, we can calculate $f(n, k)$ by considering every possible placement of the $k - 1th$ post office, and choose the one that minimizes the sum of distances for villages between the $k - 1th$ and $kth$ post office. However, if $k = 1$, then the only post office we can place is the one in $x_n$, so we only need to find the distances of towns $x_1, \ldots, x_{n - 1}$ from $x_n$.

In the case where $k > 1$, we must consider placing a post office in towns $x_{k - 1}, x_k, \ldots, x_{n - 1}$, since it doesn't make sense to place the $k - 1th$ post office before we've seen $k - 1$ villages, and we can only place up to the village before $x_n$, since by construction it is the last of our $k$ post offices places in the $n$ towns. Therefore, we have the following recurrence:

$$
f(n, k) = \begin{cases}
0 & n \le k \\
\sum_{i = 1}^{n - 1} | x_i - x_n | & k = 1 \\
\min_{k - 1 \le i < n} \left( f(i, k - 1) + \sum_{i < j < n} \min \left( | x_j - x_n |, | x_j - x_i | \right) \right) & \text{otherwise}\\
\end{cases}
$$

Since $f(i, k - 1)$ holds for $i < n$, and we always choose the placement of the $k - 1th$ post office that minimizes the total sum of distances, $f(n, k)$ is correctly computed.

Now define $c(i)$ for $k \le i \le n$ to be the total sum of distances if we place the $kth$ post office in village $x_i$ (i.e. the last post office), and all other post offices optimally. Since $f(i, k)$ correctly computes the sum of distances in this case up to the $ith$ post office, and we are guaranteed that no other post office comes after the one placed in $x_i$, all villages $x_j$ for $j > i$ will be closest to the post office in $x_i$.

Therefore, we can compute $c(i)$ as follows:

$$
c(i) = f(i, k) + \sum_{i < j \le n} | x_i - x_j |
$$

Finally, in order to compute our final answer, we just need to check every placement of the last post office and return the minimum sum of distances returned. Thus, we have a minimal sum of distances of...

$$
\min_{k \le i \le n} c(i)
$$

And so our overall optimum is as follows:

$$
OPT(n, k) = \min_{k \le i \le n} \{f(i, k) + \sum_{i + 1 \le j \le n} | x_i - x_j |\}
$$


**Running Time**: Computing $f(n, k)$ runs in $O(n^2)$ time, and since we need to run this calculation over at most $nk$ values, to fully memoize all inputs it takes $O(kn^3)$.

Then, each $c(i)$ takes constant time to retrieve each $f(i, k)$, and an additional $O(n)$ to compute the sum of the remaining distances, for a total of $O(n)$.

Finally, we call $c(i)$ $O(n)$ times, for a total of $O(n^2)$.

Thus, our running time is $O(kn^3)$

## RNA Secondary Structure

**Problem**: Given an RNA molecule $B = b_1 b_2 \ldots b_n$, find a secondary structure $S$ that maximizes the number of base pairs.

Note that maximizing the number of base pairs is a practical problem, since RNA molecules fold into a secondary structure that minimizes free energy, and the number of base pairs is a good proxy for free energy.

*Rules*:

- *Watson-Crick base pairs*: $A-U, U-A, C-G, G-C$
- *No sharp turns*: the end pair are separated by at least 4 intervening base pairs, i.e. $(b_i, b_j) \in S \to |i - j| > 4$
- *No crossing*: If $(b_i, b_j), (b_k, b_l) \in S \to \neg (i < k < j < l)$

**Algorithm**:

```python
# Top Down Recursive

WC = { 'A': 'U', 'U': 'A', 'C': 'G', 'G': 'C' }

def ssr(B):
  N = len(B)
  dp = [[None] * N for _ in range(N)]

  for i in range(N) for j in range(N):
    if abs(j - i) <= 4:
      dp[i][j] = 0

  def f(i, j):
    if dp[i][j] is not None:
      return dp[i][j]

    for t in range(i, j - 5 + 1):
      if WC[B[t]] == B[j]:
        dp[i][j] = max(dp[i][j], 1 + f(i, t - 1) + f(t + 1, j - 1))

    return dp[i][j]

  return f(0, N - 1)

def ssi(B):
  N = len(B)
  dp = [[0] * N for _ in range(N)]

  for l in range(2, N + 1):
    for i in range(N - l + 1):
      j = i + l - 1
      if j - i <= 4:
        dp[i][j] = 0
      else:
        dp[i][j] = dp[i][j - 1]
        for t in range(i, j - 5 + 1):
          if WC[B[t]] == B[j]:
            dp[i][j] = max(dp[i][j], 1 + dp[i][t - 1] + dp[t + 1][j - 1])
```

**Correctness**:

Let $OPT(i, j)$ be the maximum number of base pairs in a secondary structure of the substring $b_i, b_{i + 1}, \ldots, b_j$.

**Base Case**: $\forall i, j$, we have $|j - i| \le 4 \to OPT(i, j) = 0$

Suppose that for some $l = j - i \ge 4$, we have computed all $OPT(i, j)$. Then to compute $OPT(i, j)$ for $|j - i| > l$, we do the following:

- Case 1: Base $b_j$ is not involved in a pair in our solution
  - $OPT(i, j) = OPT(i, j - 1)$, since we have $OPT$ solved for $l$
- Case 2: Base $b_j$ pairs with $b_t$ for some $t \in [i, j - 5]$
  - $OPT(i, j) = max_{i \le t \le j - 5} \{1 + OPT(i, t - 1) + OPT(t + 1, j - 1)\}$

## Sequence Alignment

**Problem**: Given two strings $x_1 x_2 \ldots x_m$ and $y_1 y_2 \ldots y_n$, find an alignment with the minimum number of mismatches and gaps.

An alignment is a set of ordered pairs $(x_{i_1}, y_{j_1}), \ldots, (x_{i_k}, y_{j_k})$ such that $i_1 < i_2 < \ldots$ and $j_1 < j_2 < \ldots$.

- **Correctness**: Let $OPT(i, j)$ be the min cost of aligning $x_i, \ldots, x_i$ and $y_j, \ldots, y_n$.

Our base case is when either $i$ or $j$ are $0$, we just need to do $j$ or $i$ deletes respectively.

- Case 1: $OPT$ matches $x_i, y_j$
  - Then, if $x_i \ne y_j$, add one, and otherwise add zero to $OPT(i - 1, j - 1)$.
- Case 2: $OPT$ leaves $x_i$ unmatched
  - Then, pay the gap cost for $x_i + OPT(i - 1, j)$
- Case 3: $OPT$ leaves $y_j$ unmatched
  - Then, pay gap cost for $y_j + OPT(i, j - 1)$

```python
# Bottom up, non memory optimized - T = O(mn), S = O(mn)
def seq_alignment(x, y):
  m, n = len(x), len(y)
  dp = [[None] * (n + 1) for _ in range(m + 1)]
  for i in range(m + 1):
    dp[i][0] = i
  for j in range(n + 1):
    dp[0][j] = j

  for i in range(1, m + 1):
    for j in range(1, n + 1):
      dp[i][j] = max(
        (0 if x[i] == y[j] else 1) + dp[i - 1][j - 1],
        1 + dp[i - 1][j],
        1 + d[i][j - 1]
      )

  return dp[m][n]
```

Note that in computational biology, you'll be running this on strings with thousands or even millions of characters. Therefore, the space starts to become a problem. For instance, if $m = n = 100,000$, we do $10,000,000,000$ operations (which isn't terrible), but we end up with a $40$ GB `dp` matrix.

You can optimize the space by only tracking the previous row of `dp`.

```python
# Bottom up DP, optimized for space
def seq_alignment(x, y):
  m, n = len(x), len(y)
  # base cases covered
  dp_prev = list(range(m + 1))
  dp_curr = [None] * (m + 1)

  for i in range(1, m + 1):
    dp_curr[0] = i
    for j in range(1, n + 1):
      dp[curr] = min(
        (0 if x[i] == y[j] else 1) + dp_prev[j - 1],
        1 + dp_prev[j],
        1 + dp_curr[j - 1]
      )
    for j in range(1, n + 1):
      dp_old[j] = dp_curr[j]

  return dp_curr[n]
```

## Longest Path in a DAG

**Problem** Given a DAG $G$, find the longest path.

*Note*: This problem is NP-hard for general directed graphs , as it has the Hamiltonian Path as a special case. However, with a DAG you can solve this in polynomial time.

**Approach**: Since $G$ is a DAG, it has a topological sort. Start by sorting vertices in their topological order.

Let $OPT(j)$ be the length of the longest path that ends at vertex $j$ in the topological sort. We just need to guess the last edge of the longest path that ends in $j$.

$$
OPT(j) = \max_{k \to j} \{ OPT(k) + 1 \}
$$

Then, to get our answer we can output...

$$
\max_{j \in [1, n]} OPT(j)
$$

## Longest Increasing Subsequence

Given a sequence of numbers $x_1, x_2, \ldots, x_n$, find the longest increasing (not necessarily contiguous) subsequence.

Define $OPT(j)$ as LIS that ends at $x_j$. Our approach is to guess the previous element $x_k$. Our base case is $OPT(1) = 1$, and for any $j$ such that $\forall k < j$, $x_j < x_k$, $OPT(j) = 1$.

$$
OPT(j) = \begin{cases}
1 & j = 1 \\
1 + \max_{k < j} \{ OPT(k) : x_k < x_j \} & \text{otherwise}
\end{cases}
$$

```python
def LIS(X):
  n = len(X)
  dp = [None] * (n + 1)
  dp[0], dp[1] = 0, 1

  def f(i):
    if dp[i] is None:
      dp[i] = 1 + max([0] + [f(k) for k in range(i) if X[k - 1] < X[i - 1]])

    return dp[i]

  return max(f(i) for i in range(1, n + 1))
```

## Shortest Paths with Negative Edge Weights (Bellman-Ford)

Given a weighted directed graph $G = (V, E)$, and a source vertex $s4, where the weight of edges $e = (u, v) \in E$ is $c_e = c_{u, v}$, find the shortest path from $s$ to all other vertices.

*Note*: if $G$ has a negative cycle, there is no solution, so suppose $G$ has no negative cycles.

**Approach**: Define $OPT(v, i)$ as the length of the shortest path from $s \to v$ among all paths that use at most $i$ edges. We induct on $i$.

- *Case 1*: Shortest path from $s \to v$ has $< i$ edges:
  - $OPT(v, i) = OPT(v, i - 1)$
- *Case 2*: Shortest path from $s \to v$ has exactly $i$ edges
  - $OPT(v, i) = \min_{u \to v} \{ OPT(u, i - 1) + c_{u, v} \}$

So we have...

$$
OPT(v, i) = \begin{cases}
0 & v = s, i = 0 \\
\infty & v \ne s, i = 0 \\
\min \{ OPT(v, i - 1), \min_{u \to v} \{ OPT(u, i - 1) + c_{u, v} \} \} & \text{otherwise}
\end{cases}
$$

Since any path in any graph has at most $n - 1$ edges, the shortest path to $v$ has $\le n - 1$ edges. Thus, $OPT(v, n - 1)$ is the length of the shortest path from $s \to v$.

**Running Time**: We solve $O(n)$ subproblems, each taking $O(m)$ time to solve, for a total running time of $O(nm)$.

```python
def bellman_ford(G, C, s):
  n = len(G)
  dp = [[float('inf')] * (n + 1) for _ in range(n)]

  for i in range(n + 1):
    dp[s][i] = 0

  for i in range(1, n):
    for v in range(n):
      dp[v][i] = dp[v][i - 1]
      for u in range(n):
        dp[v][i] = min(dp[v][i], dp[u][i - 1] + C[u][v])

  return [dp[v][n] for v in range(n)]
```

## P1 - Knapsack Approximation

Given $n$ items with integer weights $w_1, \ldots , w_n$ and values $v_1, \ldots , v_n$ and knapsack of weight $W$ such that $w_i \le \frac{W}{2}$ for all $i$. Design an algorithm that runs in time polynomial in $n$ and $\log W$ and outputs a 2-approximation for the knapsack problem.

```python
def A(weights, values, W):
  n = len(weights)
  greed = [(values[i] / weights[i], i) for i in range(n)]
  greed.sort(reverse=True)

  w, v = 0, 0
  for i in range(n):
    if w + weights[greed[i][1]] <= W:
      w += weights[greed[i][1]]
      v += values[greed[i][1]]
    else:
      break

  return v
```

**Correctness**: Let $A$ be my algorithm above, $G$ be an algorithm that makes the same greedy choice of selecting items in increasing order of $\frac{v_i}{w_i}$, but with fractional selection allowed, and $OPT$ be the optimal algorithm for selecting items of only whole quantities. Let $S$ be the set of items chosen by $A$, $S'$ be the set of items chosen by $G$, and $S^*$ be the set of items chosen by $OPT$. Define $w(X)$ and $v(X)$ as the sum of weights and values respectively of items in the set of items $X$.

*Lemma 1*: With fractional choices allowed, greedy (choosing highest $v_i/w_i$ ratio) upper bounds the optimal for non-fractional choices, i.e. $G \ge OPT$. This is given

*Lemma 2*: $A$ chooses items with a total sum of weights $\ge \frac{W}{2} + 1$

*Proof*: We know that each $w_i \le W/2$, so $A$ is guaranteed to choose at least two items before running out of room in the knapsack. Suppose for the sake of contradiction that the set of items chosen by $A$ had a total weight $< \frac{W}{2} + 1$. Let $x$ be the weight of our knapsack right before $A$ terminates. Since we are guaranteed to be able to choose at least $2$ items, and each item has an integer weight $1 \le w_i \le \frac{W}{2}$, we have that $2 \le x \le W$. In order for our premise to be true, we need to have $x \le \frac{W}{2}$, but since each $w_i \le \frac{W}{2}$, we must have then been able to select the next item, so our algorithm wouldn't have terminated at this point, which is a contradiction.

*Lemma 3*: $G$ will choose the whole item up until the last item it adds to its knapsack

*Proof*: By the design of the algorithm this must be true. Consider an arbitrary round of $G$ in which it considers item $i$ and has a current remaining weight of $x$. We have two cases:

- Case 1: $w_i \le x$
  - Then we take the entire item since this is the best value/weight item that we haven't already visited
- Case 2: $w_i > x$
  - Then we take as much of the item as possible (weight $x$ of it), after which our knapsack is full and we terminate

No matter what, if we select a fractional amount of an item then it means we've filled the remaining weight of our knapsack and so the algorithm terminates immediately after.

*Lemma 4*: For any integers $a, b$, if $a \le b$, then $a \le \frac{a + b}{2}$

*Proof*: $a \le b \to 2a \le a + b \to a \le \frac{a + b}{2}$

From (1), we have that $\frac{1}{2} OPT \le \frac{1}{2} G$

From (2) we have that $w(S) \ge \frac{W}{2} + 1$, and by definition $w(S') \le W$, so we have that $w(S) \ge \frac{1}{2} w(S')$. Both $G$ and $A$ choose values in the same order, and by (3) we have that $G$ picks only full items until the very last item added. Therefore, the items chosen by $A$ are exactly the same as the items chosen by $G$ up until the very last item. Let $x$ be the remaining weight in both $A$ and $G$'s knapsack at this point, and $g_k$ be the last item added by $G$. We have the following cases:

- Case 1: $w_{g_k} = x$
  - Then $G$ chooses all of $g_k$, and $A$ will also choose $g_k$, so $A$ and $G$ pick the exact same set and amounts of items, and we have $v(S) = v(S') \ge v(S^*)$, and so $v(S) \ge \frac{1}{2} v(S^*)$
- Case 2: $w_{g_k} > x$
  - Then $G$ chooses $x$ of $g_k$, and $A$ will see the item that it can't fit and terminate, in which case we have $v(S) = v(S') - x \cdot \frac{v_{g_k}}{w_{g_k}}$

In case 1, we clearly have a 2-approximation of $OPT$, since $A$ is optimal.

In case 2 however, the key insight is that the value that the last item contributes to $v(S')$ is no more than half of the total value, which I will show below.

We have that $w(g_1, \ldots, g_{k - 1}) > \frac{W}{2}$, since otherwise we would be able to choose a non-fractional amount of $g_k$ (since $w_{g_k} \le \frac{W}{2}$). Considering the sum of values of the first $k - 1$ items chosen by $G$ (as well as $A$), we have...

$$
v(g_1, \ldots, g_{k - 1}) = v_{g_1} + \ldots + v_{g_{k - 1}} = w_{g_1} \cdot \frac{v_{g_1}}{w_{g_1}} + \ldots + w_{g_{k - 1}} \cdot \frac{v_{g_{k - 1}}}{w_{g_{k - 1}}}
$$

Since $G$ chooses items in increasing order of $\frac{v_{g_i}}{w_{g_i}}$, we also have that $\frac{v_{g_i}}{w_{g_i}} \ge \frac{v_{g_k}}{w_{g_k}}$ for all $i < k$, so we can put a lower bound on the sum of the first $k - 1$ values chosen by $G$

$$
v(g_1, \ldots, g_{k - 1}) \ge w_{g_1} \cdot \frac{v_{g_k}}{w_{g_k}} + \ldots + w_{g_{k - 1}} \cdot \frac{v_{g_k}}{w_{g_k}} = \frac{v_{g_k}}{w_{g_k}} (w_{g_1} + \ldots + w_{g_{k - 1}})
$$

And since $(w_{g_1} + \ldots + w_{g_{k - 1}}) > \frac{W}{2}$, we have...

$$
v(g_1, \ldots, g_{k - 1}) \ge \frac{v_{g_k}}{w_{g_k}} \frac{W}{2}
$$

Similarly, we can lower bound $x \cdot \frac{v_{g_k}}{w_{g_k}}$, since $x \le w_{g_k} \le \frac{W}{2}$

$$
x \cdot \frac{v_{g_k}}{w_{g_k}} \le  \frac{W}{2} \cdot \frac{v_{g_k}}{w_{g_k}}
$$

So we have...

$$
x \cdot \frac{v_{g_k}}{w_{g_k}} \le v(g_1, \ldots, g_{k - 1})
$$

And since $v(S') = v(g_1, \ldots, g_{k - 1}) + x \cdot \frac{v_{g_k}}{w_{g_k}}$, by (4) we have that $x \cdot \frac{v_{g_k}}{w_{g_k}} \le \frac{1}{2} v(S')$.

Therefore, knowing that $G$ is optimal with fractional weights, and that the only way $A$ and $G$ differ is in the last item added in case 2, we have that...

$$
v(a_1, a_2, \ldots, a_{k - 1}) = v(g_1, g_2, \ldots, g_{k - 1}) \ge \frac{1}{2} v(S') = \frac{1}{2}v(S^*)
$$

And so $v(S) \ge \frac{1}{2} v(S^*)$. Additionally, since $v(S^*)$ is optimal for non-fractional weights, by definition we have $v(S) \le v(S^*)$, and $A$ is therefore a 2-approximation of $OPT$.

**Running Time**:

Since $w_i \le \frac{W}{2}$, and division by $W$ is $O(\log W)$, calculating `greed`, which has $n$ elements, takes $O(n \cdot \log W)$, and sorting it takes $O(n \log n)$.

Then, I iterate through $O(n)$ items in the loop, and once again since $w_i \le \frac{W}{2}$, and each iteration is only performing addition, we have $O(\log W)$ work in each iteration, for a total of $O(n \log W)$

Therefore, the overall running time of the algorithm is $O(n (\log n + \log W))$, which is polynomial in $n$ and $\log W$

## P2 - Maximum Sub-Rectangle

**Problem**: You are given an $n \times n$ array $A$ where for all $1 \le i, j \le n$, $A_{ij}$ is an integer that may be negative. For a rectangle $(x_1, y_1), (x_2, y_2)$ where $x_1 \le x_2$ and $y_1 \le y_2$, the value is the sum of all numbers in this rectangle, i.e.,

$$
\sum_{i = x_1}^{x_2} \sum_{j = y_1}^{y_2} A_{ij}
$$

Design an algorithm that runs in time $O(n^3)$ and outputs the value of the rectangle of largest value. Note that the value of the empty rectangle is zero.

```python
def max_rectangle(A):
  n = len(A)

  dp = [[0] * (n + 1) for _ in range(n + 1)]
  pf_row = [[0] * (n + 1) for _ in range(n + 1)]
  for x in range(1, n + 1):
    for y in range(1, n + 1):
      pf_row[x][y] = pf_row[x][y - 1] + A[x - 1][y - 1]

  def effsum(x1, y1, x2, y2):
    return A[x1 - 1][y1 - 1] if x1 == x2 and y1 == y2 else sum(
        pf_row[i][y2] - pf_row[i][y1 - 1]
        for i in range(x1, x2 + 1)
    )

  def g(y1, y2):
    if y1 > y2:
      return 0

    dp[y1][y2] = max(g(y1 + 1, y2), g(y1, y2 - 1))
    curr = 0
    for x in range(1, n + 1):
      curr = max(curr + effsum(x, y1, x, y2), 0)
      dp[y1][y2] = max(dp[y1][y2], curr)
    return dp[y1][y2]

  return max(0, g(1, n))
```

**Correctness**: Define $g(y_1, y_2)$ as the maximum sum rectangle with the upper left corner being $(x_1, y_1')$, and lower right corner being $(x_2, y_2')$ for all $x_1 \le x_2$ and $y_1' \ge y_1, y_2' \le y_2$. Additionally, define $s(x_1, y_1, x_2, y_2)$ as the sum of the rectangle with the upper left corner being $(x_1, y_1)$ and lower right corner being $(x_2, y_2)$, i.e. $\sum_{i = x_1}^{x_2} \sum_{j = y_1}^{y_2} A_{ij}$

Our base case is when $y_2 - y_1 < 0$, in which case we return $0$ because this is an empty/negative size rectangle.

Assuming we've calculated $g(y_1', y_2')$ for all $y_2 - y_1 > y_2' - y_1'$, we can calculate $g(y_1, y_2)$ by considering all rectangles that either (1) don't contain any of the row $y_2$, (2) don't contain any of the row $y_1$, or (3) contain both rows $y_1$ and $y_2$.

Since $y_2 - (y_1 + 1) < y_2 - y_1$ and $(y_1 - 1) - y_2 < y_2 - y_1$, we can find (1) and (2) with $g(y_1, y_2 - 1)$ and $g(y_1 + 1, y_2)$ respectively. Then, to find (3) we need to consider each possible $x_1, x_2$, choosing the values that maximum our sum for $y_1, y_2$ being fixed. This can be calculated as the largest sum of contiguous subsequences of rows between $y_1$ and $y_2$. To do this, I reduce this problem to the largest contiguous subsequence of a list of numbers $a_1, a_2, \ldots, a_n$,

Defining $f(i)$ to be the LCS that can be made with $a_1, \ldots, a_i$ which either includes $a_i$ or is empty, we induct over $i$. My base case is when $i = 0$, in which case $f(i) = 0$. Assuming $f(i - 1)$ is correct, we can calculate $f(i)$ by taking maximum of either choosing to include $a_i$ in our subsequence, or to reset our subsequence to zero. Therefore, we have...

$$
f(i) = \max \{ f(i - 1) + a_i, 0 \}
$$

Then, to find the maximum sum of a contiguous subsequence of $a_1, \ldots, a_n$, we just need to take the maximum of $f(i)$ for all $i$. Let $h(i) = \max_{0 \le j \le n} \{f(j)\}$. My code calculates $h(i)$ over the sum of rows between $y_1$ and $y_2$ in a bottom up fashion, but instead of storing all previous $f(j)$ for $j < i$, I only store the previous in a variable `curr`. Additionally, I keep track of the maximum $f(i)$ I've seen thus far in another variable `dp[y1][y2]`, but this is equivalent. Let $h(n, y_1, y_2)$ denote the same problem, but ranging over $n$ values of the form $a_i = A_{x_i, y_1} + \ldots + A_{x_i, y_2}$, with the induction being over $n$ (the number of elements) still. Note that this is an equivalently solved problem, and the extra parameters are just to define bounds on the rows in which the instance of the problem exists.

Then we have the following recurrence for $g(y_1, y_2)$:

$$
g(y_1, y_2) = \begin{cases}
0 & y_2 - y_1 < 0 \\
\max \{ g(y_1 + 1, y_2), g(y_1, y_2 - 1), h(n, y_1, y_2) \} & \text{otherwise}
\end{cases}
$$

Since $g$ checks all possible $y_1, y_2$ and finds the best $x_1, x_2$ for each of them, we must find the largest sum rectangle, and can thus return $g(1, n)$ as the maximum sub-rectangle in $A$.

**Running Time**:

I start by finding the prefix sum of all rows in $O(n^2)$.

Then, I solve $O(n^2)$ many subproblems, one for each $y_1, y_2$. Each subproblem takes $O(n)$ time to solve, since I need to loop through $n$ many sub-sub problems to find the maximum sum contiguous subsequence of row sums. Note that to calculate row sums, I use my precomputed prefix sum, which allows me to calculate the sum of a row in $O(1)$.

Therefore, the overall runtime is $O(n^3)$.

## P3 - Count connected subsets of size k

Given a tree $T$ with $n$ vertices and an integer $k \ge 1$ such that every vertex of $T$ has degree $deg(v) \le 3$, we want to choose a set $S$ of $k$ vertices of the tree which are connected, i.e., for any pair of vertices $u, v \in S$ the unique path between $u, v$ in $T$ is also in $S$. Design a polynomial time algorithm that outputs the number of such sets $S$.

Start by choosing an arbitrary vertex $v$ as root, and run $BFS(v)$, returning the level of each vertex in the BFS-tree (with `L[v] = 0`).

Define $f(v, k)$ as the number of connected subsets of size $k$ that **must** contain $v$, and are otherwise composed of vertices $u$ with $L[u] > L[v]$, i.e. only containing children of $v$.

Our base cases are as follows:

- $f(v, 1) = 1$
- $f(v, k) = 0$ if $k > 1$ and $children(v) = \emptyset$

Note that $children(v)$ is defined at $\{ u \in neighbors(v) : L[u] = L[v] + 1 \}$

And so to calculate $f(v, k)$, we just need to sum over all possibilities that involve $v$ in terms of children of $v$. Any given subproblem contains nodes in any subset of $children(v)$ of size $k - 1$, so we need to iterate through all possible ways to choose such a subset, for all values of $k'_1, k'_2, \ldots, k'_{k - 1}$.

- *Case 1*, $k' = 1$: $f(v)$ only contains $v$, and vertices from $k' = 1$ subtree of $v$.
  - Then $f(v, k) = \sum_{u \in children(v)} f(u, k - 1)$
- *Case 2*, $k' = 2$: $f(v)$ only contains $v$, and vertices from $k' = 2$ subtrees of $v$.
  - Then $f(v, k) = \sum_{}