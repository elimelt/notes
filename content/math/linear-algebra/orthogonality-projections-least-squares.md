---
title: Orthogonality, Projections, and Least Squares
category: Mathematics
tags:
  - linear algebra
  - orthogonality
  - projections
  - least squares
  - qr decomposition
date: 2026-08-01
status: draft
description: Orthogonality and projections as one story ending in least squares, with the normal equations, the geometry of residuals, and why QR beats the normal equations numerically.
sources:
  - title: MIT 18.06 Linear Algebra, Spring 2010 (Strang), lectures 15-17
    url: https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/
    type: course
  - title: Interactive Linear Algebra (Margalit and Rabinoff), chapter 6
    url: https://textbooks.math.gatech.edu/ila/chap-orthogonality.html
    type: book
  - title: numpy.linalg.lstsq
    url: https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html
    type: docs
  - title: Trefethen and Bau, Numerical Linear Algebra (SIAM, 1997), lectures 11 and 19
    type: book
---

## Purpose

Orthogonality, projection, and least squares are one idea seen three ways: the best approximation to $b$ from a subspace is the point where the error is perpendicular to the subspace. This note derives that chain, states the normal equations, and explains the numerical reason libraries solve least squares with QR or SVD instead. Matrix background is in [[math/linear-algebra/cheatsheet|Matrix Theory]].

## Orthogonality and orthonormal bases

Vectors $u, v \in \mathbb{R}^n$ are orthogonal when $u^T v = 0$. A set of vectors is orthonormal when the vectors are pairwise orthogonal and unit length. Orthonormal bases are the convenient ones: if $Q = [u_1 \cdots u_k]$ has orthonormal columns then $Q^T Q = I$, and coordinates in that basis are just inner products, no linear system to solve.

The orthogonal complement of a subspace $W \subseteq \mathbb{R}^n$ is $W^\perp = \{v : v^T w = 0 \text{ for all } w \in W\}$. The instance that matters for least squares is

$$
\mathrm{col}(A)^\perp = \ker(A^T),
$$

vectors perpendicular to every column of $A$ are exactly the vectors $A^T$ kills ([ILA §6.2](https://textbooks.math.gatech.edu/ila/chap-orthogonality.html)). Every $b \in \mathbb{R}^n$ splits uniquely as $b = \hat{b} + e$ with $\hat{b} \in W$ and $e \in W^\perp$.

## Projections

The projection of $b$ onto $W$ is that component $\hat{b}$, the closest point in $W$ to $b$. With an orthonormal basis $u_1, \dots, u_k$ for $W$,

$$
\mathrm{proj}_W(b) = \sum_{i=1}^{k} (u_i^T b)\, u_i = Q Q^T b,
$$

per [ILA §6.3](https://textbooks.math.gatech.edu/ila/chap-orthogonality.html). For a general full-column-rank matrix $A$ whose columns span $W$, project by solving for the coefficient vector: the projection is $A\hat{x}$ where $\hat{x}$ makes the residual perpendicular to every column, and the projection matrix is

$$
P = A (A^T A)^{-1} A^T.
$$

Projection matrices satisfy $P^2 = P$ (projecting twice changes nothing) and $P^T = P$. Strang's [18.06 lectures 15-16](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/) build the whole least-squares story from this matrix.

## Least squares and the normal equations

An overdetermined system $Ax = b$ with $A \in \mathbb{R}^{m \times n}$, $m > n$, usually has no solution because $b$ is not in $\mathrm{col}(A)$. Least squares asks for the $\hat{x}$ minimizing $\lVert Ax - b \rVert_2^2$. Geometrically, $A\hat{x}$ must be the projection of $b$ onto $\mathrm{col}(A)$, so the residual $r = b - A\hat{x}$ lies in $\mathrm{col}(A)^\perp = \ker(A^T)$:

$$
A^T (b - A\hat{x}) = 0
\quad\Longleftrightarrow\quad
A^T A\, \hat{x} = A^T b.
$$

These are the normal equations ([ILA §6.5](https://textbooks.math.gatech.edu/ila/chap-orthogonality.html)). The same equation drops out of calculus, since $\nabla_x \lVert Ax - b\rVert^2 = 2 A^T(Ax - b)$. $A^T A$ is invertible exactly when $A$ has full column rank, and then $\hat{x} = (A^T A)^{-1} A^T b$ is unique.

The residual orthogonality is worth internalizing. The error the fit cannot remove is perpendicular to everything the model can express. In a regression with an intercept column of ones, orthogonality against that column forces the residuals to sum to zero. Orthogonality against a feature column means the residual is uncorrelated with that feature; whatever structure remains in the residual is structure the column space cannot represent.

## Worked example

Fit a line $y = c_0 + c_1 t$ through the points $(0, 6)$, $(1, 0)$, $(2, 0)$, the example Strang uses in [18.06 lecture 16](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/):

$$
A = \begin{pmatrix} 1 & 0 \\ 1 & 1 \\ 1 & 2 \end{pmatrix}, \quad
b = \begin{pmatrix} 6 \\ 0 \\ 0 \end{pmatrix}, \quad
A^T A = \begin{pmatrix} 3 & 3 \\ 3 & 5 \end{pmatrix}, \quad
A^T b = \begin{pmatrix} 6 \\ 0 \end{pmatrix}.
$$

Solving $A^T A \hat{x} = A^T b$ gives $\hat{x} = (5, -3)^T$, the line $y = 5 - 3t$. The fitted values are $(5, 2, -1)$ and the residual is $r = (1, -2, 1)$. Check both orthogonality conditions: $r$ sums to zero (intercept column) and $0\cdot1 + 1\cdot(-2) + 2\cdot1 = 0$ (slope column), so $r \perp \mathrm{col}(A)$ as derived.

```python
import numpy as np

A = np.array([[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]])
b = np.array([6.0, 0.0, 0.0])

xhat, res, rank, sv = np.linalg.lstsq(A, b, rcond=None)
print(xhat)                    # [ 5. -3.]
r = b - A @ xhat
print(A.T @ r)                 # ~[0. 0.], residual orthogonal to columns

P = A @ np.linalg.inv(A.T @ A) @ A.T   # projection onto col(A)
print(np.allclose(P @ b, A @ xhat))    # True
print(np.allclose(P @ P, P))           # True, projecting twice is a no-op
```

## Why QR instead of the normal equations

Forming $A^T A$ squares the conditioning of the problem: for full-column-rank $A$, $\kappa(A^T A) = \kappa(A)^2$ (Trefethen and Bau, lecture 19; Golub and Van Loan, ch. 5). A matrix with $\kappa(A) = 10^6$ is unpleasant; its normal equations have $\kappa = 10^{12}$ and can lose all useful digits in double precision. The QR route factors $A = QR$ with orthonormal $Q$ and triangular $R$, then solves $R\hat{x} = Q^T b$ by back substitution. Orthogonal transformations preserve norms and hence conditioning, and Householder QR is backward stable (Trefethen and Bau, lecture 16), so the accuracy tracks $\kappa(A)$ rather than $\kappa(A)^2$.

[numpy.linalg.lstsq](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html) goes one step further and uses an SVD-based LAPACK driver (`gelsd`). SVD costs more than QR but handles rank deficiency: singular values below `rcond` times the largest are treated as zero, and among all minimizers `lstsq` returns the minimum-norm one. That pseudoinverse story continues in [[math/linear-algebra/svd-and-pseudoinverse|SVD and the Pseudoinverse]].

## Sources

- [MIT 18.06 Linear Algebra, Spring 2010 (Strang), lectures 15-17](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)
- [Interactive Linear Algebra (Margalit and Rabinoff), chapter 6](https://textbooks.math.gatech.edu/ila/chap-orthogonality.html)
- [numpy.linalg.lstsq documentation](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html)
- Trefethen and Bau, Numerical Linear Algebra (SIAM, 1997), lectures 11, 16, 19

## Related notes

- [[math/linear-algebra/cheatsheet|Matrix Theory]]
- [[math/linear-algebra/svd-and-pseudoinverse|Singular Value Decomposition and the Pseudoinverse]]
- [[math/linear-algebra/eigenvalues-eigenvectors-diagonalization|Eigenvalues, Eigenvectors, and Diagonalization]]
