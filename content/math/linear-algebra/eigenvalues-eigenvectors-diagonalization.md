---
title: Eigenvalues, Eigenvectors, and Diagonalization
category: Mathematics
tags:
  - linear algebra
  - eigenvalues
  - eigenvectors
  - diagonalization
  - matrix powers
date: 2026-08-01
status: draft
description: Eigenpairs as invariant directions, diagonalization as a change of basis, matrix powers and stability, with a hand-worked 2x2 example and NumPy caveats.
sources:
  - title: MIT 18.06 Linear Algebra, Spring 2010 (Strang), lectures 21-22
    url: https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/
    type: course
  - title: Interactive Linear Algebra (Margalit and Rabinoff), chapter 5
    url: https://textbooks.math.gatech.edu/ila/chap-eigenvalues.html
    type: book
  - title: numpy.linalg.eig
    url: https://numpy.org/doc/stable/reference/generated/numpy.linalg.eig.html
    type: docs
---

## Purpose

This note builds eigenvalues and diagonalization from the definition up, then uses them for the thing they are actually good at: understanding what happens when you apply the same linear map over and over. It is meant as the reference other notes can cite for eigendecompositions, matrix powers, and stability. Broader matrix background lives in [[math/linear-algebra/cheatsheet|Matrix Theory]].

## Eigenpairs are invariant directions

A square matrix $A \in \mathbb{R}^{n \times n}$ moves most vectors to somewhere unrelated. An eigenvector is a direction the map preserves: a nonzero $v$ with

$$
Av = \lambda v
$$

for some scalar $\lambda$, the eigenvalue ([ILA §5.1](https://textbooks.math.gatech.edu/ila/chap-eigenvalues.html)). Along the line spanned by $v$, the whole action of $A$ collapses to multiplication by $\lambda$. That is the entire appeal. If you can find a basis of such directions, the matrix has no geometry left to hide.

Rearranging $Av = \lambda v$ gives $(A - \lambda I)v = 0$, so $\lambda$ is an eigenvalue exactly when $A - \lambda I$ is singular, which happens exactly when

$$
\det(A - \lambda I) = 0.
$$

The left side is the characteristic polynomial, degree $n$ in $\lambda$, so $A$ has $n$ eigenvalues counted with multiplicity, possibly complex ([ILA §5.2](https://textbooks.math.gatech.edu/ila/chap-eigenvalues.html)). Two multiplicities matter: the algebraic multiplicity of $\lambda$ is its multiplicity as a root, and the geometric multiplicity is $\dim \ker(A - \lambda I)$, the number of independent eigenvectors it contributes. Geometric never exceeds algebraic.

## Diagonalization is a change of basis

Suppose $A$ has $n$ linearly independent eigenvectors $v_1, \dots, v_n$ with eigenvalues $\lambda_1, \dots, \lambda_n$. Stack the eigenvectors as columns of $P$ and the eigenvalues into $D = \mathrm{diag}(\lambda_1, \dots, \lambda_n)$. Then $AP = PD$ column by column, and since $P$ is invertible,

$$
A = P D P^{-1}.
$$

Read right to left: $P^{-1}$ rewrites a vector in eigenvector coordinates, $D$ scales each coordinate independently, and $P$ translates back. In the right basis, $A$ is just $n$ separate scalar multiplications.

$A$ is diagonalizable if and only if the geometric multiplicities sum to $n$, equivalently every eigenvalue's geometric multiplicity equals its algebraic multiplicity ([ILA §5.4](https://textbooks.math.gatech.edu/ila/chap-eigenvalues.html)). Distinct eigenvalues always give independent eigenvectors, so a matrix with $n$ distinct eigenvalues is automatically diagonalizable. The failure mode is a repeated root that comes up short on eigenvectors: $\begin{pmatrix} 1 & 1 \\ 0 & 1 \end{pmatrix}$ has $\lambda = 1$ with algebraic multiplicity 2 but only one eigenvector direction, so it is defective and not diagonalizable.

Symmetric matrices are the best case. If $A = A^T$, all eigenvalues are real, eigenvectors for distinct eigenvalues are orthogonal, and there is always an orthonormal eigenbasis, giving the spectral decomposition $A = Q D Q^T$ with $Q$ orthogonal ([ILA chapter 5](https://textbooks.math.gatech.edu/ila/chap-eigenvalues.html); Strang covers this in [18.06 lecture 25](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)).

## Worked 2x2 example

Take the symmetric matrix

$$
A = \begin{pmatrix} 3 & 1 \\ 1 & 3 \end{pmatrix}.
$$

Characteristic polynomial: $\det(A - \lambda I) = (3-\lambda)^2 - 1 = \lambda^2 - 6\lambda + 8 = (\lambda - 2)(\lambda - 4)$, so $\lambda_1 = 2$ and $\lambda_2 = 4$.

For $\lambda_1 = 2$: $A - 2I = \begin{pmatrix} 1 & 1 \\ 1 & 1 \end{pmatrix}$, whose kernel is spanned by $v_1 = (1, -1)^T$.

For $\lambda_2 = 4$: $A - 4I = \begin{pmatrix} -1 & 1 \\ 1 & -1 \end{pmatrix}$, kernel spanned by $v_2 = (1, 1)^T$.

The eigenvectors are orthogonal, as the spectral theorem promises. Normalizing gives $Q = \frac{1}{\sqrt{2}}\begin{pmatrix} 1 & 1 \\ -1 & 1 \end{pmatrix}$ and $A = Q\,\mathrm{diag}(2, 4)\,Q^T$. Geometrically, $A$ stretches by 4 along the diagonal direction $(1,1)$ and by 2 along the anti-diagonal $(1,-1)$.

## Matrix powers and stability

Diagonalization turns repeated application into repeated scalar multiplication:

$$
A^k = (P D P^{-1})^k = P D^k P^{-1}, \qquad D^k = \mathrm{diag}(\lambda_1^k, \dots, \lambda_n^k),
$$

because the inner $P^{-1}P$ pairs cancel. Writing an initial vector in eigencoordinates, $x_0 = \sum_i c_i v_i$, the dynamics $x_k = A^k x_0$ become

$$
x_k = \sum_i c_i \lambda_i^k v_i.
$$

Each mode evolves independently, and the long-run behavior is read off the eigenvalue magnitudes: modes with $|\lambda_i| < 1$ decay, modes with $|\lambda_i| > 1$ blow up, and as $k$ grows the term with the largest $|\lambda_i|$ dominates, so $x_k$ aligns with the dominant eigenvector. This is Strang's framing of difference equations in [18.06 lecture 22](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/), and it is also why power iteration converges to the dominant eigenvector and why the spectral radius decides the stability of a linear recurrence.

## NumPy and numerical caveats

```python
import numpy as np

A = np.array([[3.0, 1.0], [1.0, 3.0]])
lam, P = np.linalg.eig(A)
print(lam)                                # [4.+0.j 2.+0.j] on some BLAS builds, [4. 2.] on others
print(np.allclose(P @ np.diag(lam) @ np.linalg.inv(P), A))  # True

k = 10  # matrix powers through the eigendecomposition
Ak = P @ np.diag(lam**k) @ np.linalg.inv(P)
print(np.allclose(Ak, np.linalg.matrix_power(A, k)))  # True
```

Caveats that bite in practice, per the [numpy.linalg.eig docs](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eig.html):

- `eig` does not sort eigenvalues. Here it happens to return 4 before 2; never assume an order.
- For a real matrix with complex eigenvalues, `eig` returns complex arrays with conjugate pairs. A rotation matrix is the standard surprise.
- For symmetric or Hermitian matrices, use `eigh` instead. It guarantees real eigenvalues sorted ascending, returns orthonormal eigenvectors, and is faster and more accurate because it exploits symmetry.
- Nearly defective matrices are numerically hostile: when eigenvalues nearly coincide and the eigenvector matrix is close to singular, $P^{-1}$ amplifies error, and computed eigenvectors of non-symmetric matrices can be ill-conditioned even when the eigenvalues are fine. The eigendecomposition of a non-symmetric matrix is not a backward-stable route to $A^k$; for symmetric matrices the orthogonal $Q$ makes the reconstruction well behaved.

## Sources

- [MIT 18.06 Linear Algebra, Spring 2010 (Strang), lectures 21-22 and 25](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)
- [Interactive Linear Algebra (Margalit and Rabinoff), chapter 5](https://textbooks.math.gatech.edu/ila/chap-eigenvalues.html)
- [numpy.linalg.eig documentation](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eig.html)

## Related notes

- [[math/linear-algebra/cheatsheet|Matrix Theory]]
- [[math/linear-algebra/svd-and-pseudoinverse|Singular Value Decomposition and the Pseudoinverse]]
- [[math/linear-algebra/python-cheatsheet|Python Linear Algebra Cheatsheet]]
