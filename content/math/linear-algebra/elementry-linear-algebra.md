---
title: Glossary of Linear Algebra Concepts
aliases:
  - linear-algebra/elementry-linear-algebra
category: Mathematics
tags:
  - gaussian-elimination
  - linear-transformations
  - matrix-multiplication
  - span
  - linear-independence
date: 2024-12-08
updated: 2026-07-30
status: evergreen
description: Introductory notes on systems of equations, Gaussian elimination, span, linear transformations, and matrix multiplication, with an emphasis on the ideas that stay useful past the algorithms.
sources:
  - https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/
  - https://textbooks.math.gatech.edu/ila/
---

## Purpose

These are introductory notes on the computational entry points to linear algebra, kept deliberately short on algorithm mechanics and longer on the takeaways that matter later. They are complemented by the broader [[math/linear-algebra/cheatsheet|Matrix Theory reference]] and its practical [[math/linear-algebra/python-cheatsheet|NumPy companion]].

## Systems of Equations

Systems of equations are both fundamental and important to actually understanding linear algebra. With that being said, the two primary introductory courses at the University of Washington, Math 208 and (to a much lesser extent) Applied Math 352, spend a significant amount of time on methods for *solving* systems of equations, something that I have almost no interest in. For the sake of completeness, I will briefly touch on notation and algorithms, but will try to both confine it to this document, and to focus on takeaways that become more useful later on.

### Notation

$$
\begin{aligned}
a_{11}x_1 + a_{12}x_2 + \cdots + a_{1n}x_n &= b_1 \\
a_{21}x_1 + a_{22}x_2 + \cdots + a_{2n}x_n &= b_2 \\
&\vdots \\
a_{m1}x_1 + a_{m2}x_2 + \cdots + a_{mn}x_n &= b_m
\end{aligned}
$$

Or equivalently, in matrix form $Ax = b$.

$$
\begin{aligned}
\begin{bmatrix}
a_{11} & a_{12} & \cdots & a_{1n} \\
a_{21} & a_{22} & \cdots & a_{2n} \\
\vdots & \vdots & \ddots & \vdots \\
a_{m1} & a_{m2} & \cdots & a_{mn}
\end{bmatrix}
\begin{bmatrix}
x_1 \\
x_2 \\
\vdots \\
x_n
\end{bmatrix}
&=
\begin{bmatrix}
b_1 \\
b_2 \\
\vdots \\
b_m
\end{bmatrix}
\end{aligned}
$$

### Gaussian Elimination

Perform any of the following **elementary row operations** on the augmented matrix $\lbrack  A|b  \rbrack$:

- Swap two rows
- Multiply a row by a nonzero scalar
- Add a multiple of one row to another

The aim of the algorithm is to get the matrix into either **row echelon form** or **reduced row echelon form**. In row echelon form, the first nonzero entry of each row sits strictly to the right of the first nonzero entry of the row above it (many texts also scale each leading entry to 1). In reduced row echelon form, each leading entry is 1 and is the only nonzero entry in its column. For example, below $A$ is in row echelon form, and $B$ is in reduced row echelon form.

$$
\begin{aligned}
A &=
\begin{bmatrix}
a_{11} & a_{12} & a_{13} & a_{14} \\
0 & a_{22} & a_{23} & a_{24} \\
0 & 0 & a_{33} & a_{34} \\
0 & 0 & 0 & a_{44}
\end{bmatrix}
\\
B &=
\begin{bmatrix}
1 & 0 & 0 & 0 \\
0 & 1 & 0 & 0 \\
0 & 0 & 1 & 0 \\
0 & 0 & 0 & 1
\end{bmatrix}
\end{aligned}
$$

As you perform row operations, you also act on $b$ to keep the system equivalent. Once you have the matrix in row echelon form, you can solve the system by back substitution, or by continuing to row reduce to reduced row echelon form, where the solution is immediately apparent.

### Takeaways

#### Row Operations

Solving systems of equations is pretty boring, but the emergent structure of a system on the verge of being solved cements a few important ideas:

- **Row operations** need to *somehow* be legal, in particular reversible and preservative of the solution set. Each operation corresponds to multiplication by an invertible elementary matrix, so the operations form a **group** in action.
- Row reducing exposes the structure of the solution set. Pivot columns correspond to determined variables and non-pivot columns to free ones, which gives a parameterization of the solution set and reads off the **rank** of the matrix.
- Rows of zeros left after row reduction indicate **redundancy** among the original equations, in other words **linear dependence**.

#### Span

The span of a set of vectors is the set of all possible linear combinations of those vectors, and it is always a **subspace** of the ambient vector space. For a matrix whose columns are those vectors, the span is exactly the **column space** of the matrix.

$$
\begin{aligned}
\text{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix}, \begin{bmatrix} 0 \\ 1 \end{bmatrix} \right\} &= \mathbb{R}^2 \\
\text{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix}, \begin{bmatrix} 0 \\ 1 \end{bmatrix}, \begin{bmatrix} 1 \\ 1 \end{bmatrix} \right\} &= \mathbb{R}^2 \\
\text{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix}, \begin{bmatrix} 0 \\ 1 \end{bmatrix}, \begin{bmatrix} 1 \\ 1 \end{bmatrix} \right\} &= \text{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix}, \begin{bmatrix} 0 \\ 1 \end{bmatrix} \right\}
\end{aligned}
$$

For a set of $n$ vectors in $\mathbb{R}^n$ to span $\mathbb{R}^n$, the vectors must be linearly independent. This is a necessary and sufficient condition for a set of vectors to be a **basis** for $\mathbb{R}^n$. You can perform additional reasoning to determine the rules for spanning sets, and implications on linear independence. For instance, a set of fewer than $n$ vectors in $\mathbb{R}^n$ cannot span $\mathbb{R}^n$, and a set of more than $n$ vectors in $\mathbb{R}^n$ must be linearly dependent.

#### Linear Transformations

For a function to be linear, it must satisfy two properties:

- **Additivity**: $f(x + y) = f(x) + f(y)$
- **Homogeneity**: $f(cx) = cf(x)$

A linear transformation is a function $T: \mathbb{R}^n \to \mathbb{R}^m$ that satisfies these properties. The **kernel** of a linear transformation is the set of vectors that are mapped to the zero vector, e.g. $T(x) = 0$, or $Ax = 0$ for a matrix $A$ that represents the transformation. The kernel is a subspace of the domain. The **range** of a linear transformation is the set of all possible outputs, and is a subspace of the codomain.

$$
\begin{aligned}
T: \mathbb{R}^2 &\to \mathbb{R}^2 \\
T\left( \begin{bmatrix} x \\ y \end{bmatrix} \right) &= \begin{bmatrix} x \\ 0 \end{bmatrix}
\end{aligned}
$$

$$
\begin{aligned}
\text{ker}(T) &= \text{span}\left\{ \begin{bmatrix} 0 \\ 1 \end{bmatrix} \right\} \\
\text{range}(T) &= \text{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix} \right\}
\end{aligned}
$$

#### Matrix-Vector Multiplication

$$
\begin{aligned}
A\begin{bmatrix} x \\ y \end{bmatrix} &= x\begin{bmatrix} a_{11} \\ a_{21} \end{bmatrix} + y\begin{bmatrix} a_{12} \\ a_{22} \end{bmatrix} \\
&= \begin{bmatrix} a_{11}x + a_{12}y \\ a_{21}x + a_{22}y \end{bmatrix}
\end{aligned}
$$

Matrix-vector multiplication is a linear transformation. The columns of the matrix are the images of the basis vectors, and the result is the image of the input vector. The kernel of the transformation is the null space of the matrix, and the range is the column space of the matrix.

Visually, you can picture transforming the basis vectors, and with them the unit square, of the domain. The matrix is the transformation, its columns are where the basis vectors land, and the product is where the input vector lands.

#### Matrix-Matrix Multiplication

$$
\begin{aligned}
AB &= A\begin{bmatrix} b_1 & b_2 & \cdots & b_n \end{bmatrix} \\
&= \begin{bmatrix} Ab_1 & Ab_2 & \cdots & Ab_n \end{bmatrix}
\end{aligned}
$$

The algorithm is to multiply $A$ by each column of $B$. The result is a matrix whose columns are the images of the columns of $B$ under $A$, which is exactly composing the two transformations. The column space of $AB$ sits inside the column space of $A$, and the null space of $AB$ contains the null space of $B$.

```python
import numpy as np

## inefficient
def multiply_bad(A, B):
    C = np.zeros((A.shape[0], B.shape[1]))
    for i in range(A.shape[0]):
        for j in range(B.shape[1]):
            for k in range(A.shape[1]):
                C[i, j] += A[i, k] * B[k, j]
    return C

## efficient
def multiply_good(A, B):
    return np.dot(A, B)

M, N = 1000, 1000
A = np.random.rand(M, N)
B = np.random.rand(N, M)

## in IPython/Jupyter:
## %timeit multiply_bad(A, B)
## %timeit multiply_good(A, B)
```

Matrix multiplication is fundamentally a costly operation. The schoolbook algorithm above takes $O(n^3)$ time for square matrices, which is why the naive triple loop is unusable at any real size. Libraries like NumPy dispatch to heavily optimized BLAS routines that use vectorized instructions and cache-aware blocking, and run orders of magnitude faster than the naive loop even at the same asymptotic complexity. In practice you should **never** write your own matrix multiplication.

## Related notes

- [[math/linear-algebra/cheatsheet|Matrix Theory reference]]
- [[math/linear-algebra/python-cheatsheet|Python Linear Algebra Cheatsheet]]
