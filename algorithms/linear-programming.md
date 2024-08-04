# Linear Programming

## Linear Systems

Systems of linear equations (key word being equality) can be solved via gaussian elimination. This is relatively easy, since your solution space ends up being a line, a plane, or a hyperplane in higher dimensions.

Let $a$ be a column vector in $\mathbb{R}^d$, and $x$ a column vector of $d$ variables. We can represent a system using the *inner product* of these two vectors:

$$
\langle a, x \rangle = a^Tx = a_1x_1 + a_2x_2 + \ldots + a_dx_d = \sum_{i=1}^d a_ix_i
$$

A **hyperplane** is the set of points $x$ such that $\langle a, x \rangle = b$ for some $b$. A **handspace** is the set of points on one side of a hyperplace, $\{x : \langle a, x \rangle \geq b\}$ or $\{x : \langle a, x \rangle \leq b\}$.

The intersection of a system of half spaces creates a **polytope**, which is a convex set. A **convex set** is a set where the line segment between any two points in the set is also in the set.

## Linear Programs

The goal of a linear program is to optimize some **objective function** subject to a set of constraints, which are also linear functions. For example...

$$
\begin{align*}
&max  & 3x_1 - 4x_3\\
&s.t. & x_1 + x_2 \le 5\\
&     & x_3 + x_1 = 4\\
&     & x_3 - x_2 \ge -5\\
&     & x_1, x_2, x_3 \ge 0\\
\end{align*}
$$


## Linear Algebra Review

$$
\langle a, x \rangle = a^Tx = a_1x_1 + a_2x_2 + \ldots + a_dx_d
$$

$$
A = \begin{bmatrix}
a_1^T \\
a_2^T \\
\vdots \\
a_m^T
\end{bmatrix} \Rightarrow
Ax = \begin{pmatrix}
\langle a_1, x \rangle \\
\langle a_2, x \rangle \\
\vdots \\
\langle a_m, x \rangle
\end{pmatrix}
$$

$$
Ax \le b \Rightarrow \begin{array}{c}
\langle a_1, x \rangle \le b_1 \\
\langle a_2, x \rangle \le b_2 \\
\vdots \\
\langle a_m, x \rangle \le b_m
\end{array}
$$

## Linear Program Standard Form

We can write any linear program in the *standard form* below.

$$
\begin{array}{cc}
max & \langle c, x \rangle \\
s.t., & Ax \le b\\
~ & x \ge 0
\end{array}
$$

For example, we can transform the following linear program by turning the minimization problem into a maximization, and turning all equalities into two inequalities.

$$
\begin{array}{cc}
min &   y_1 - 2y_2\\
s.t., & y_1 + 2y_2 = 3\\
~ & y_1 - y_2 \ge 1\\
~ & y_1, y_2 \ge 0\\
\end{array}
$$

To turn a min into a max, we just negate the objective function. The same holds for reversing the direction of a $\geq$. We can turn the above linear program into the following:

$$
\begin{array}{cc}
max &   -y_1 + 2y_2\\
s.t., & y_1 + 2y_2 \le 3\\
~ & -(y_1 + 2y_2) \le -3\\
~ & y_1 + y_2 \le 1\\
~ & y_1, y_2 \ge 0\\
\end{array}
$$

In LPs where you don't have non-negativity for all variables, you can replace the variables missing this constraint with the difference of two non-negative variables. For example...

$$
\begin{array}{cc}
max &   y_1\\
s.t., & y_1 + y_2 \le 3\\
~ & y_2 \ge 0\\
\end{array}
$$

We replace $y_1$ with $z_1 - z_1'$, where $z_1, z_1' \ge 0$. The linear program becomes...

$$
\begin{array}{cc}
max   & z_1 - z_1'\\
s.t., & z_1 - z_1' + y_2 \le 3\\
~     & z_1, z_1', y_2 \ge 0\\
\end{array}
$$

## Applications of Linear Programming.

LPs generalize to all sorts of problems, such as 2-person zero-sum games, shortest path, max-flow, matching, multi-commodity flow, MST, min weighted, arborescence, ...

We can solve linear programs in polynomial time, and they turn out to be useful for approximation algorithms.

## Components of a Linear Program

- Set of variables
- Bounding constraints on variables
  - Are they non-negative?
- Objective function
- Is it a minimization or maximization problem?
- LP constrains, but they need to be linear
  - Is it an equality or inequality?

## Max-Flow

Given a graph $G = (V, E)$ with source $s$ and sink $t$, for every edge $e$ we have a variable $x_e$ as the flow on the edge $e$.

The bounding constraints would be...

- $x_e \ge 0$ for all $e$ (since the flow is non-negative)
- $x_e \le c(e)$ for all $e$ (capacity constraint)
- $\sum_{e \text{ out of } v} x_e = \sum_{e \text{ into} v} x_e$ for all $v \ne s, t$ (conservation constraint)

And our objective function would be...

- Maximize $\sum_{e \text{ out of } s} x_e$

So we have an overall LP of...

$$
\begin{array}{ccc}
max     & \sum_{e \text{ out of } s} x_e & ~\\
s.t.,   & \sum_{e \text{ out of } v} x_e = \sum_{e \text{ into} v} x_e & \forall c \ne s, t\\
~       & x_e \le c(e) & \forall e\\
~       & x_e \ge 0 & \forall e
\end{array}
$$

Note that the flow this gives you is not necessarily an integer max-flow.

## Min-Cost Max-Flow

Expanding on the previous example, we can add a cost to each edge $p(e)$ and try to minimize $p(e)$ while achieving some constant flow $f$.

$$
\begin{array}{ccc}
max     & \sum_{e \in E} p(e) \cdot x_e & ~\\
s.t.,   & \sum_{e \text{ out of } v} x_e = \sum_{e \text{ into} v} x_e & \forall c \ne s, t\\
~       & \sum_{e \text{ out of } s} x_e = f & ~\\
~       & x_e \le c(e) & \forall e\\
~       & x_e \ge 0 & \forall e
\end{array}
$$

## Weighted Vertex Cover

Given a graph $G = (V, E)$, where each vertex has a cost $c_v$, find the minimum cost vertex cover, i.e. $\min \sum_{v \in S} c_v$

We have a variable $x_v$ for each $v$, where $x_v = 1$ if $v \in S$ and $x_v = 0$ otherwise. Then we have the constraint that for every edge $(u, v) \in

$$
\begin{array}{ccc}
max     & \sum_{e \in E} p(e) \cdot x_e & ~\\
s.t.,   & \sum_{e \text{ out of } v} x_e = \sum_{e \text{ into} v} x_e & \forall c \ne s, t\\
~       & \sum_{e \text{ out of } s} x_e = f & ~\\
~       & x_e \le c(e) & \forall e\\
~       & x_e \ge 0 & \forall e
\end{array}
$$
