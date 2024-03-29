# Measuring Efficiency

Time is roughly proportional to the number of operations performed. Generally, this holds for simple operations. As a side note, you should avoid hashing.

## O-Notation Definition

Given two functions $f(n)$ and $g(n)$, we say that $f(n)$ is $O(g(n))$ if there exist constants $c$ and $n_0$ such that $0 \leq f(n) \leq c \cdot g(n)$ for all $n \geq n_0$.

## Omega-Notation Definition

Given two functions $f(n)$ and $g(n)$, we say that $f(n)$ is $\Omega(g(n))$ if there exist constants $c$ and $n_0$ such that $0 \leq c \cdot g(n) \leq f(n)$ for all $n \geq n_0$.

## Theta-Notation Definition

Given two functions $f(n)$ and $g(n)$, we say that $f(n)$ is $\Theta(g(n))$ if there exist constants $c_1$, $c_2$, and $n_0$ such that $0 \leq c_1 \cdot g(n) \leq f(n) \leq c_2 \cdot g(n)$ for all $n \geq n_0$.

## Common Bounds

Logarithms **always** grow slower than polynomial functions.

### Polynomial 
$$
a_0 + a_1n + a_2n^2 + \ldots + a_kn^k \in O(n^k)
$$

### Logarithmic
$$
\log_a n \in O(\log_b n) \text{ for all } a, b > 1
$$

### Exponential
$$
a^n \in O(b^n) \text{ for all } a, b > 1
$$

### Factorial
$$
n! \in O(n^n)
$$

## "Efficient" Algorithms

If a problem size grows by at most a constant factor, then so does its run-time.

$$
T(2n) = 
$$
