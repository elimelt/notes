# Divide and Conquer

Reduce problem to multiple sub-problems. While in induction, you typically only reduce your problem size by 1, with divide and conquer it is more common to reduce to some constant fraction of your original problem size. After recursively solving each sub-problem, merge the solutions.

**Examples**: Merge-sort, Binary Search, Strassen's Algorithm

## Why Balanced Partitioning?

With regular induction, split problem into $n - 1$ and $1$, then solve the $n - 1$ and merge the solution with the $1$.

$$
T(n) = T(n - 1) + T(1) + n
$$

Instead, divide into two problems of size $\frac{n}{2}$

$$
2T(\frac{n}{2}) + n = \frac{n^2}{2} + n
$$

## Divide and Conquer Approach

- "The more dividing and conquering, the better"
  - Overhead grows for each, but for many algorithms, two levels of D&C will be 4 times faster, 3 levels will be almost 8, and so on.
  - Best approach is to recurse down to a small problem size, then do the regular iterative brute force algorithm.
  - This is the approach behind Quick sort with random splitters.

## Finding the Root of a Function

Given a continuous function $f$ and two points $a, b$ and $b > a$ such that $f(a) \le 0$ and $f(b) \ge 0$.

Find an approximate root of $f$, ie a point $c$ where there is $r$ s.t. $|r - c| \le \epsilon$ and $f(r) = 0$. Note that this must exist by IVT.

### Naive Approach

Divide $[a, b]$ into $n = \frac{b - a}{\epsilon}$ intervals. For each interval, check $f(x) \le 0, f(x + \epsilon) \ge 0$.

This runs in $O(n) = O(\frac{b - a}{\epsilon})$.

### D&C Approach

```python
def Bisection(f, a, b, e):
    if (b - a) < e:
        return a

    m = (a + b)/2
    if f(m) < 0:
        return Bisection(c, b, e)
    else
        return Bisection(a, c, e)
```

Let $n = \frac{a - b}{\epsilon}$ and $c = \frac{a + b}{2}$. SO in each step we reduce by half.

$$
T(n) = T(\frac{n}{2}) + O(1) = O(\log(n)) = O(\log \frac{a - b}{\epsilon})
$$

### Correctness

$P(n)$: $\forall a, b$ s.t. $f(a) \le 0$ and $f(b) \ge 0$, and $\frac{a - b}{\epsilon} = n$, that `Bisection` returns a value, say $c$, s.t. $\exists r$ s.t. $|r - c| \le \epsilon$

**Base Case.** $P(1)$: By IVT, $\exists r \in [a, b]$ s.t. $f(r) = 0$. We output $a$, and $|a - r| \le |a - b| \le \epsilon$.

**IH:** Assume $P(n)$

**IS:** $P(2n)$

Given arbitrary $b > a$ s.t. $\frac{|a - b|}{\epsilon} = 2n$ and $f(a) \le 0$, $f(b) \ge 0$, start with $c = \frac{a + b}{2}$.

#### Case 1: $f(c) \ge 0$

Then we satisfy $P(n)$ for $a, c$ because $\frac{c - a}{\epsilon} = n$, and $f(a) \le 0$, $f(c) \ge 0$.

#### Case 2: $f(c) \le 0$

Then we satisfy $P(n)$ for $c, b$, for the exact same reasoning.

## Closest Pair of Points (non-geometrically)

Given $n$ points and an *arbitrary* distance between them, find the closest pair (not just Euclidean distance).

### 1 Dimensional Version

Given $n$ points on the real line, you can find the closest pair by sorting and then comparing each consecutive pair of points.

**Key point**: Don't need to check *every* pair. Can instead exploit geometry.

### 2 Dimensional Version

Given $n$ points in the plane$, find the pair with the smallest Euclidean distance between them.

- *Divide*: draw a vertical line $L$ with $\approx \frac{n}{2}$ points on each side.
- *Conquer*: find closest pair on each side recursively.

Suppose $\delta$ is the minimum on each side. Then you only need to consider points within $\delta$ of $L$ as the case where our two points lie on opposite sides of $L$.

Partition each side of $L$ into $\frac{\delta}{2} \times \frac{\delta}{2}$ squares. This guarantees that each square has at most one point, since multiple points in the same square would have to have been the minimum on that side (since the maximum distance within a single square is $\frac{\delta}{\sqrt{2}}$).

Then, sort the points in the strip $x \in [L - \delta, L + \delta]$ by $y$-coordinate to make $s_1, s_2, \ldots s_i$.

**Claim**: $\forall s_i, s_j$, if $|i - j| > 11$, then $d(s_i, s_j) > \delta$.

**Proof**: There are 4 squares in each row of the strip, each occupying at most on point. We know that any point $p_j$ more than two rows away from $p_i$ must have $d(p_i, p_j) > \delta$.

There are at most 3 points in the same row as $p_i$, and 8 in the 2 rows above/below. Thus, any point more than $8 + 3 = 11$ points away from $p_i$ will be more than two rows away, and thus have a distance greater than $\delta$.

#### Implementation

```python
# divide and conquer closest points

def bounding_indices(P, low, high, key=lambda x: x[0]):
    n = len(P)
    l, r = 0, n - 1

    while l <= r:
        mid = (l + r) // 2
        if low <= key(P[mid]):
            r = mid - 1
        else:
            l = mid + 1
    smallest_index = l

    l, r = 0, n - 1
    while l <= r:
        mid = (l + r) // 2
        if high >= key(P[mid]):
            l = mid + 1
        else:
            r = mid - 1
    highest_index = r

    return smallest_index, highest_index

def d(p1, p2):
  if p1 is None or p2 is None:
    return float('inf')
  return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** .5

def cp_brute_force(P):
  n = len(P)
  ans = P[:2]
  min_d = d(P[0], P[1])
  for i in range(n):
    for j in range(i + 1):
      if i == j:
        continue
      curr_d = d(P[i], P[j])
      if curr_d < min_d:
        min_d = curr_d
        ans = [P[i], P[j]]
  return ans

def cp_recursive(P):
  n = len(P)
  if n < 2:
    return None, None

  if n <= 10:
    return cp_brute_force(P)

  l1, l2 = cp_recursive(P[:n//2])
  r1, r2 = cp_recursive(P[n//2:])

  m1, m2 = (l1, l2) if d(l1, l2) < d(r1, r2) else (r1, r2)

  delta = d(m1, m2)
  L = (P[n//2][0] + P[n//2 + 1][0]) / 2

  l, h = bounding_indices(P, L - delta, L + delta)

  middle = sorted(P[l:h + 1], key=lambda x: x[1])
  k = len(middle)
  for i in range(k):
    low = max(0, i - 11)
    high = min(k, i + 11)
    for j in range(low, high):
      if i == j:
        continue
      curr_dist = d(middle[i], middle[j])
      if curr_dist  < delta:
        delta = curr_dist
        m1, m2 = middle[i], middle[j]

  return m1, m2

def closest_points(P):
  return cp_recursive(sorted(P, key = lambda x: x[0]))

```