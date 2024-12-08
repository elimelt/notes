# Elementary Linear Algebra

## Systems of Equations

Systems of equations are both fundamental and important to actually understanding linear algebra. With that being said, the two primary introductory courses at the University of Washington, Math 208 and (to a much lesser extent) Applied Math 352, spend a significant amount of time on methods for *solving* systems of equations, something that I have almost no interest in. For the sake of completeness, I will briefly touch on notation and algorithms, but will try to both confine it to this document, and to focus on takeaways that become more useful later on.

### Notation

$$
\begin{align*}
a_{11}x_1 + a_{12}x_2 + \cdots + a_{1n}x_n &= b_1 \\
a_{21}x_1 + a_{22}x_2 + \cdots + a_{2n}x_n &= b_2 \\
&\vdots \\
a_{m1}x_1 + a_{m2}x_2 + \cdots + a_{mn}x_n &= b_m
\end{align*}
$$

Or equivalently, in matrix form $Ax = b$.

$$
\begin{align*}
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
\end{align*}
$$

### Gaussian Elimination

Perform any of the following **elementary row operations** to the augmented matrix $[A|b]$:

- Swap two rows
- Multiply a row by a nonzero scalar
- Add a multiple of one row to another

 The aim of the algorithm is to get the matrix into either **row echelon form** or **reduced row echelon form**. The former is a matrix where the first nonzero element in each row is 1, and the first nonzero element in each row is to the right of the first nonzero element in the row above it. The latter is a matrix where the first nonzero element in each row is 1, and the first nonzero element in each row is the only nonzero element in its column. For example, below $A$ is in row echelon form, and $B$ is in reduced row echelon form.


$$
\begin{align*}
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
\end{align*}
$$

As you perform row operations, you also act on $b$ to keep the system equivalent. Once you have the matrix in row echelon form, you can solve the system by back substitution, or by continuing to row reduce to reduced row echelon form, where the solution is immediately apparent.

### Takeaways

#### Row Operations

Solving systems of equations is pretty boring, but the emergent structure of a system on the verge of being solved cements a few important ideas:

- **Row operations** need to *somehow* be legal, in particular reversible and preservative of the solution set. This is a good example of a **group** in action.
- The result of running Gaussian elimination is a **basis** for the solution set. This gives the **span** of the solution set, and the **rank** of the matrix.
- Additional rows of zero left in the matrix after row reduction indicate **redundancy**, or in other words, **linear dependence**.

#### Span

The span of a set of vectors is the set of all possible linear combinations of those vectors. The span of a set of vectors is a **subspace** of the vector space. The span of a set of vectors is the **null space** of the matrix whose columns are those vectors.

$$
\begin{align*}
\text{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix}, \begin{bmatrix} 0 \\ 1 \end{bmatrix} \right\} &= \mathbb{R}^2 \\
\text{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix}, \begin{bmatrix} 0 \\ 1 \end{bmatrix}, \begin{bmatrix} 1 \\ 1 \end{bmatrix} \right\} &= \mathbb{R}^2 \\
\text{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix}, \begin{bmatrix} 0 \\ 1 \end{bmatrix}, \begin{bmatrix} 1 \\ 1 \end{bmatrix} \right\} &= \text{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix}, \begin{bmatrix} 0 \\ 1 \end{bmatrix} \right\}
\end{align*}
$$

For a set of $n$ vectors in $\mathbb{R}^n$ to span $\mathbb{R}^n$, the vectors must be linearly independent. This is a necessary and sufficient condition for a set of vectors to be a **basis** for $\mathbb{R}^n$. You can perform additional reasoning to determine the rules for spanning sets, and implications on linear independence. For instance, a set of less than $n$ vectors in $\mathbb{R}^n$ cannot span $\mathbb{R}^n$, and a set of more than $n$ vectors in $\mathbb{R}^n$ must be linearly dependent.

#### Linear Transformations

For a function to be linear, it must satisfy two properties:

- **Additivity**: $f(x + y) = f(x) + f(y)$
- **Homogeneity**: $f(cx) = cf(x)$

A linear transformation is a function $T: \mathbb{R}^n \to \mathbb{R}^m$ that satisfies these properties. The **kernel** of a linear transformation is the set of vectors that are mapped to the zero vector, e.g. $T(x) = 0$, or $Ax = 0$ for a matrix $A$ that represents the transformation. The kernel is a subspace of the domain. The **range** of a linear transformation is the set of all possible outputs, and is a subspace of the codomain.

$$
\begin{align*}
T: \mathbb{R}^2 &\to \mathbb{R}^2 \\
T\left( \begin{bmatrix} x \\ y \end{bmatrix} \right) &= \begin{bmatrix} x \\ 0 \end{bmatrix}
\end{align*}
$$

$$
\begin{align*}
\text{ker}(T) &= \text{span}\left\{ \begin{bmatrix} 0 \\ 1 \end{bmatrix} \right\} \\
\text{range}(T) &= \text{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix} \right\}
\end{align*}
$$

#### Matrix-Vector Multiplication

$$
\begin{align*}
A\begin{bmatrix} x \\ y \end{bmatrix} &= x\begin{bmatrix} a_{11} \\ a_{21} \end{bmatrix} + y\begin{bmatrix} a_{12} \\ a_{22} \end{bmatrix} \\
&= \begin{bmatrix} a_{11}x + a_{12}y \\ a_{21}x + a_{22}y \end{bmatrix}
\end{align*}
$$

Matrix-vector multiplication is a linear transformation. The columns of the matrix are the images of the basis vectors, and the result is the image of the input vector. The kernel of the transformation is the null space of the matrix, and the range is the column space of the matrix.

Visually, you can picture transforming the basis vectors/unit square of the domain into the basis vectors/unit square of the codomain. The matrix is the transformation matrix, and the columns are the images of the basis vectors. The result is the image of the input vector.

#### Matrix-Matrix Multiplication

$$
\begin{align*}
AB &= A\begin{bmatrix} b_1 & b_2 & \cdots & b_n \end{bmatrix} \\
&= \begin{bmatrix} Ab_1 & Ab_2 & \cdots & Ab_n \end{bmatrix}
\end{align*}
$$

The algorithm here is to multiply the matrix on the right by each column of the matrix on the left. The result is a matrix whose columns are the images of the columns of the matrix on the right. This is a linear transformation, and the kernel of the transformation is the null space of the matrix on the right, and the range is the column space of the matrix on the left.q

```python
import numpy as np

# inefficient
def multiply_bad(A, B):
    C = np.zeros((A.shape[0], B.shape[1]))
    for i in range(A.shape[0]):
        for j in range(B.shape[1]):
            for k in range(A.shape[1]):
                C[i, j] += A[i, k] * B[k, j]
    return C

# efficient
def multiply_good(A, B):
    return np.dot(A, B)

M, N = 10000, 10000
A = np.random.rand(M, N)
B = np.random.rand(N, M)

%timeit multiply_bad(A, B)
%timeit multiply_good(A, B)
```

```plaintext

```

Matrix multiplication is fundamentally a costly operation, taking $O(n^3)$ time. That being said, libraries like numpy are heavily optimized and can perform matrix multiplication orders of magnitude faster than naive implementations using vectorized operations. In practice you should **never** write your own matrix multiplication.
