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


### Algorithm

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

### Correctness

A string is valid if it has $\le k_A$ consecutive $A$ and $\le k_B$ consecutive $B$.

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

### Problem

Interstate highway 5 is a straight highway from Washington all the way to California. There are $n$ villages alongside this highway. Think about the highway as an integer axis, and the position of village $i$ is an integer $x_i$ along this axis. Assume that there are no two villages in the same position, i.e., $x_i \neq x_j$ for $i \neq j$. The distance between two villages $x_i,x_j$ is simply $| x_i - x_j |$.

USPS is interested in building k post offices in some, but not necessarily all of the villages along highway 5, for some $1 \leq k \leq n$. A village and the post office in it have the same position. We want to choose the positions of these post offices so that the sum of the distances from each village to its nearest post office is minimized. Design an algorithm that runs in time polynomial in $n$ and outputs the minimum possible sum of distances to the optimal location for post offices.

### Algorithm

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


### Running Time

Computing $f(n, k)$ runs in $O(n^2)$ time, and since we need to run this calculation over at most $nk$ values, to fully memoize all inputs it takes $O(kn^3)$.

Then, each $c(i)$ takes constant time to retrieve each $f(i, k)$, and an additional $O(n)$ to compute the sum of the remaining distances, for a total of $O(n)$.

Finally, we call $c(i)$ $O(n)$ times, for a total of $O(n^2)$.

Thus, our running time is $O(kn^3)$

