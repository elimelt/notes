# Fundamentals of Vectors

## Geometric Basics

### Definition and Representation

- A vector is a quantity with both magnitude and direction
- Notation: $\vec{v}$ or $\mathbf{v}$ or $\begin{pmatrix} x \\ y \\ z \end{pmatrix}$
- Components: $\vec{v} = \langle v_1, v_2, v_3 \rangle$ in 3D space

### Geometric Interpretation

- Directed line segment from initial point to terminal point
- Length (magnitude): $\|\vec{v}\| = \sqrt{v_1^2 + v_2^2 + v_3^2}$
- Two vectors are equal if they have same magnitude and direction

### Position Vectors

- Vector from origin to a point $P(x,y,z)$
- Written as: $\vec{r} = x\mathbf{i} + y\mathbf{j} + z\mathbf{k}$

### Direction Vectors

- Unit vector in direction of $\vec{v}$: $\hat{v} = \frac{\vec{v}}{\|\vec{v}\|}$
- Represents pure direction (magnitude = 1)

### Unit Vectors

- Vectors with magnitude 1: $\|\vec{u}\| = 1$
- Direction cosines: $\cos \alpha = \frac{v_1}{\|\vec{v}\|}, \cos \beta = \frac{v_2}{\|\vec{v}\|}, \cos \gamma = \frac{v_3}{\|\vec{v}\|}$

#### Standard Basis Vectors

| Vector       | Components              | Description                |
| ------------ | ----------------------- | -------------------------- |
| $\mathbf{i}$ | $\langle 1,0,0 \rangle$ | Unit vector in x-direction |
| $\mathbf{j}$ | $\langle 0,1,0 \rangle$ | Unit vector in y-direction |
| $\mathbf{k}$ | $\langle 0,0,1 \rangle$ | Unit vector in z-direction |

## Basic Vector Operations

### Addition and Subtraction

- Addition: $\vec{a} + \vec{b} = \langle a_1+b_1, a_2+b_2, a_3+b_3 \rangle$
- Subtraction: $\vec{a} - \vec{b} = \langle a_1-b_1, a_2-b_2, a_3-b_3 \rangle$

#### Parallelogram Law

- Sum of vectors forms diagonal of parallelogram
- $\vec{a} + \vec{b} = \vec{d}$ where $\vec{d}$ is diagonal

#### Triangle Inequality

- $\|\vec{a} + \vec{b}\| \leq \|\vec{a}\| + \|\vec{b}\|$
- Equality holds if and only if vectors are parallel

### Scalar Multiplication

- $c\vec{v} = \langle cv_1, cv_2, cv_3 \rangle$
- Properties:
  - $c(\vec{a} + \vec{b}) = c\vec{a} + c\vec{b}$
  - $(c_1 + c_2)\vec{a} = c_1\vec{a} + c_2\vec{a}$
  - $\|c\vec{v}\| = |c|\|\vec{v}\|$

# Systems of Linear Equations

## Matrix Form (Ax = b)

$$
\begin{bmatrix}
a_{11} & a_{12} & \cdots & a_{1n} \\
a_{21} & a_{22} & \cdots & a_{2n} \\
\vdots & \vdots & \ddots & \vdots \\
a_{m1} & a_{m2} & \cdots & a_{mn}
\end{bmatrix}
\begin{bmatrix}
x_1 \\ x_2 \\ \vdots \\ x_n
\end{bmatrix} =
\begin{bmatrix}
b_1 \\ b_2 \\ \vdots \\ b_m
\end{bmatrix}
$$

## Solution Types

| Type               | Condition                                  | Geometric Interpretation            |
| ------------------ | ------------------------------------------ | ----------------------------------- |
| Unique Solution    | $\text{rank}(A) = \text{rank}([A\|b]) = n$ | Lines/planes intersect at one point |
| Infinite Solutions | $\text{rank}(A) = \text{rank}([A\|b]) < n$ | Lines/planes overlap                |
| No Solution        | $\text{rank}(A) < \text{rank}([A\|b])$     | Lines/planes are parallel           |

### Geometric Interpretation

- 2D: Intersection of lines
- 3D: Intersection of planes
- Higher dimensions: Intersection of hyperplanes

## Solution Methods

### Gaussian Elimination

1. Forward Elimination

   - Convert matrix to row echelon form (REF)
   - Create zeros below diagonal

   ```
   [1 * * *]
   [0 1 * *]
   [0 0 1 *]
   [0 0 0 1]
   ```

2. Back Substitution
   - Solve for variables from bottom up
   - $x_n \rightarrow x_{n-1} \rightarrow \cdots \rightarrow x_1$

### Gauss-Jordan Elimination

- Convert to reduced row echelon form (RREF)
- Create zeros above and below diagonal

```
[1 0 0 *]
[0 1 0 *]
[0 0 1 *]
```

#### Key Operations

| Operation             | Description                        | Notation                  |
| --------------------- | ---------------------------------- | ------------------------- |
| Row Swap              | Swap rows $i$ and $j$              | $R_i \leftrightarrow R_j$ |
| Scalar Multiplication | Multiply row $i$ by $c$            | $cR_i$                    |
| Row Addition          | Add multiple of row $i$ to row $j$ | $R_j + cR_i$              |

# Matrices

## Types and Properties

| Type             | Definition                                                                        | Properties                                                                         |
| ---------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Square           | $n \times n$ matrix                                                               | - Same number of rows and columns<br>- Can have determinant<br>- May be invertible |
| Rectangular      | $m \times n$ matrix                                                               | - Different number of rows and columns<br>- No determinant                         |
| Identity ($I_n$) | $a_{ij} = \begin{cases} 1 & \text{if } i=j \\ 0 & \text{if } i\neq j \end{cases}$ | - Square matrix<br>- 1's on diagonal, 0's elsewhere<br>- $AI = IA = A$             |
| Zero ($0$)       | All entries are 0                                                                 | - Can be any dimension<br>- $A + 0 = A$                                            |
| Diagonal         | $a_{ij} = 0$ for $i \neq j$                                                       | - Non-zero elements only on main diagonal                                          |
| Triangular       | Upper: $a_{ij} = 0$ for $i > j$<br>Lower: $a_{ij} = 0$ for $i < j$                | - Square matrix<br>- Determinant = product of diagonal entries                     |

## Basic Matrix Operations

### Addition and Subtraction

- Only defined for matrices of same dimensions
- $(A \pm B)_{ij} = a_{ij} \pm b_{ij}$
- Commutative: $A + B = B + A$
- Associative: $(A + B) + C = A + (B + C)$

### Scalar Multiplication

- $(cA)_{ij} = c(a_{ij})$
- Distributive: $c(A + B) = cA + cB$
- $(cd)A = c(dA)$

### Transpose

- $(A^T)_{ij} = a_{ji}$
- $(A^T)^T = A$
- $(A + B)^T = A^T + B^T$
- $(cA)^T = cA^T$
- $(AB)^T = B^T A^T$

## Row Echelon Form

A matrix is in row echelon form if:

1. All zero rows are at the bottom
2. Leading coefficient (pivot) of each nonzero row is to the right of pivots above
3. All entries below pivots are zero

### Reduced Row Echelon Form

Additional conditions for RREF:

1. Leading coefficient of each nonzero row is 1
2. Each leading 1 is the only nonzero entry in its column

### Pivot Positions

- First nonzero element in each row
- Determines rank of matrix
- Maximum number of linearly independent columns

### Leading Entries

Properties:

- Always nonzero
- Leftmost nonzero entry in row
- Each leading entry is right of leading entries above it

# Vector Spaces

## Axioms of Vector Spaces

Let $V$ be a vector space over field $F$ with vectors $\mathbf{u}, \mathbf{v}, \mathbf{w} \in V$ and scalars $c, d \in F$:

1. Closure under addition: $\mathbf{u} + \mathbf{v} \in V$
2. Commutativity: $\mathbf{u} + \mathbf{v} = \mathbf{v} + \mathbf{u}$
3. Associativity: $(\mathbf{u} + \mathbf{v}) + \mathbf{w} = \mathbf{u} + (\mathbf{v} + \mathbf{w})$
4. Additive identity: $\exists \mathbf{0} \in V$ such that $\mathbf{v} + \mathbf{0} = \mathbf{v}$
5. Additive inverse: $\exists -\mathbf{v} \in V$ such that $\mathbf{v} + (-\mathbf{v}) = \mathbf{0}$
6. Scalar multiplication closure: $c\mathbf{v} \in V$
7. Scalar multiplication distributivity: $c(\mathbf{u} + \mathbf{v}) = c\mathbf{u} + c\mathbf{v}$
8. Vector distributivity: $(c + d)\mathbf{v} = c\mathbf{v} + d\mathbf{v}$
9. Scalar multiplication associativity: $c(d\mathbf{v}) = (cd)\mathbf{v}$
10. Scalar multiplication identity: $1\mathbf{v} = \mathbf{v}$

## Linear Independence

### Definition

Vectors $\{\mathbf{v}_1, \mathbf{v}_2, ..., \mathbf{v}_n\}$ are linearly independent if:
$$c_1\mathbf{v}_1 + c_2\mathbf{v}_2 + ... + c_n\mathbf{v}_n = \mathbf{0}$$
implies $c_1 = c_2 = ... = c_n = 0$

### Tests and Algorithms

| Test        | Description                                                                | Result                                  |
| ----------- | -------------------------------------------------------------------------- | --------------------------------------- |
| Matrix Test | Form matrix $A$ with vectors as columns and solve $A\mathbf{x}=\mathbf{0}$ | Independent if only solution is trivial |
| Determinant | For square matrix of vectors                                               | Independent if det$(A) \neq 0$          |
| Rank        | Compute rank of matrix $A$                                                 | Independent if rank = number of vectors |

## Span

### Definition

The span of vectors $\{\mathbf{v}_1, ..., \mathbf{v}_n\}$ is:
$$\text{span}\{\mathbf{v}_1, ..., \mathbf{v}_n\} = \{c_1\mathbf{v}_1 + ... + c_n\mathbf{v}_n : c_i \in F\}$$

### Geometric Interpretation

- 1 vector: line through origin
- 2 vectors: plane through origin (if independent)
- 3 vectors: 3D space (if independent)

## Basis

A basis is a linearly independent set of vectors that spans the vector space.

### Standard Basis

For $\mathbb{R}^n$: $\{\mathbf{e}_1, \mathbf{e}_2, ..., \mathbf{e}_n\}$ where:
$\mathbf{e}_i = [0, ..., 1, ..., 0]^T$ (1 in $i$th position)

### Dimension

The dimension of a vector space is the number of vectors in any basis.

#### Basis Theorem

Every basis of a vector space has the same number of vectors.

#### Dimension Theorem

For finite-dimensional vector space $V$:

- Any linearly independent set can be extended to a basis
- Any spanning set can be reduced to a basis
- $\dim(V_1 + V_2) = \dim(V_1) + \dim(V_2) - \dim(V_1 \cap V_2)$

## Subspaces

### Tests for Subspaces

A subset $W$ of vector space $V$ is a subspace if:

1. $\mathbf{0} \in W$
2. Closed under addition: $\mathbf{u}, \mathbf{v} \in W \implies \mathbf{u} + \mathbf{v} \in W$
3. Closed under scalar multiplication: $c \in F, \mathbf{v} \in W \implies c\mathbf{v} \in W$

### Common Subspaces

| Subspace     | Definition                                      | Dimension            |
| ------------ | ----------------------------------------------- | -------------------- |
| Null Space   | $N(A) = \{\mathbf{x}: A\mathbf{x}=\mathbf{0}\}$ | $n - \text{rank}(A)$ |
| Column Space | $C(A) = \{\mathbf{y}: \mathbf{y}=A\mathbf{x}\}$ | $\text{rank}(A)$     |
| Row Space    | $R(A) = C(A^T)$                                 | $\text{rank}(A)$     |

# Advanced Vector Operations (cont. 1)

## Dot Product

The scalar product of two vectors.

### Geometric Definition

$$\vec{a} \cdot \vec{b} = |\vec{a}||\vec{b}|\cos(\theta)$$
where $\theta$ is the angle between vectors

### Algebraic Definition

For vectors in $\mathbb{R}^n$:
$$\vec{a} \cdot \vec{b} = \sum_{i=1}^n a_ib_i = a_1b_1 + a_2b_2 + ... + a_nb_n$$

### Properties

| Property              | Formula                                                                             | Description                                      |
| --------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------ |
| Commutative           | $\vec{a} \cdot \vec{b} = \vec{b} \cdot \vec{a}$                                     | Order doesn't matter                             |
| Distributive          | $\vec{a} \cdot (\vec{b} + \vec{c}) = \vec{a} \cdot \vec{b} + \vec{a} \cdot \vec{c}$ | Distributes over addition                        |
| Scalar Multiplication | $(k\vec{a}) \cdot \vec{b} = k(\vec{a} \cdot \vec{b})$                               | Scalars can be factored out                      |
| Self-Dot Product      | $\vec{a} \cdot \vec{a} = \|\vec{a}\|^2$                                             | Dot product with itself equals magnitude squared |

### Angle Formula

$$\cos(\theta) = \frac{\vec{a} \cdot \vec{b}}{|\vec{a}||\vec{b}|}$$

### Projection Formula

Vector projection of $\vec{a}$ onto $\vec{b}$:
$$\text{proj}_{\vec{b}}\vec{a} = \frac{\vec{a} \cdot \vec{b}}{|\vec{b}|^2}\vec{b}$$

## Cross Product

Vector product resulting in a vector perpendicular to both input vectors (3D only).

### Right-Hand Rule

1. Point index finger in direction of first vector
2. Point middle finger in direction of second vector
3. Thumb points in direction of cross product

### Properties

| Property         | Formula                                                                                | Description                             |
| ---------------- | -------------------------------------------------------------------------------------- | --------------------------------------- |
| Anti-commutative | $\vec{a} \times \vec{b} = -(\vec{b} \times \vec{a})$                                   | Order matters                           |
| Distributive     | $\vec{a} \times (\vec{b} + \vec{c}) = \vec{a} \times \vec{b} + \vec{a} \times \vec{c}$ | Distributes over addition               |
| Magnitude        | $\|\vec{a} \times \vec{b}\| = \|\vec{a}\|\|\vec{b}\|\sin(\theta)$                      | Area of parallelogram                   |
| Perpendicular    | $\vec{a} \times \vec{b} \perp \vec{a}$ and $\vec{a} \times \vec{b} \perp \vec{b}$      | Result is perpendicular to both vectors |

### Triple Product

Scalar triple product:
$$\vec{a} \cdot (\vec{b} \times \vec{c}) = \det[\vec{a} \; \vec{b} \; \vec{c}]$$
Represents volume of parallelepiped

## Linear Combinations

Sum of vectors with scalar coefficients:
$$c_1\vec{v_1} + c_2\vec{v_2} + ... + c_n\vec{v_n}$$

### Geometric Interpretation

- For two vectors: Points on plane formed by vectors
- For three vectors: Points in space formed by vectors
- Span: Set of all possible linear combinations

# Matrix Properties (cont. 1)

## Rank

The rank of a matrix is the dimension of the vector space spanned by its columns (or rows).

### Full Rank

A matrix has full rank when:

- For m×n matrix: rank = min(m,n)
- Column rank = Row rank
- For square matrix: rank = n ⟺ matrix is invertible

### Rank Theorems

| Theorem       | Statement                                  |
| ------------- | ------------------------------------------ |
| Rank-Nullity  | For m×n matrix A: rank(A) + nullity(A) = n |
| Product Rank  | rank(AB) ≤ min(rank(A), rank(B))           |
| Addition Rank | rank(A + B) ≤ rank(A) + rank(B)            |

## Trace

The trace of a square matrix is the sum of elements on the main diagonal.
$$tr(A) = \sum_{i=1}^n a_{ii}$$

### Properties

- tr(A + B) = tr(A) + tr(B)
- tr(cA) = c⋅tr(A)
- tr(AB) = tr(BA)
- tr(A^T) = tr(A)
- For eigenvalues λᵢ: tr(A) = ∑λᵢ

## Determinant

For square matrix A, det(A) or |A| measures the scaling factor of the linear transformation.

### Properties

1. det(AB) = det(A)⋅det(B)
2. det(A^T) = det(A)
3. det(A^{-1}) = \frac{1}{det(A)}
4. For triangular matrices: det = product of diagonal entries
5. det(cA) = c^n det(A) for n×n matrix

### Calculation Methods

#### Cofactor Expansion

For n×n matrix:
$$det(A) = \sum_{j=1}^n a_{ij}C_{ij}$$
where Cᵢⱼ is the (i,j) cofactor

#### Row/Column Expansion

Choose any row/column i:
$$det(A) = \sum_{j=1}^n (-1)^{i+j} a_{ij}M_{ij}$$
where Mᵢⱼ is the minor

#### Triangular Method

1. Convert to upper triangular using row operations
2. Multiply diagonal elements
3. Account for row operation signs

### Cramer's Rule

For system Ax = b with det(A) ≠ 0:
$$x_i = \frac{det(A_i)}{det(A)}$$
where Aᵢ is A with column i replaced by b

# Matrix Operations (cont. 1)

## Matrix Multiplication

For matrices $A_{m×n}$ and $B_{n×p}$:
$$(AB)_{ij} = \sum_{k=1}^n a_{ik}b_{kj}$$

### Properties

- Distributive: $A(B + C) = AB + AC$
- Associative: $(AB)C = A(BC)$
- Scalar multiplication: $c(AB) = (cA)B = A(cB)$
- Identity: $AI = IA = A$
- Zero matrix: $A0 = 0A = 0$

### Non-commutativity

- Generally, $AB \neq BA$
- Exception: If $A$ and $B$ commute, they are called "commuting matrices"
- Special cases where $AB = BA$:
  - When $A$ or $B$ is identity matrix
  - When $A$ or $B$ is scalar multiple of identity
  - When $A$ and $B$ are diagonal matrices

### Associativity

$(AB)C = A(BC)$ always holds for conformable matrices

## Inverse

For square matrix $A$, if $AA^{-1} = A^{-1}A = I$, then $A^{-1}$ is the inverse of $A$

### Existence Conditions

- Matrix must be square
- Matrix must be non-singular (determinant ≠ 0)
- rank(A) = n for n×n matrix

### Properties

| Property          | Formula                         |
| ----------------- | ------------------------------- |
| Double Inverse    | $(A^{-1})^{-1} = A$             |
| Product Inverse   | $(AB)^{-1} = B^{-1}A^{-1}$      |
| Scalar Inverse    | $(cA)^{-1} = \frac{1}{c}A^{-1}$ |
| Transpose Inverse | $(A^{-1})^T = (A^T)^{-1}$       |

### Calculation Methods

#### Adjugate Method

For an n×n matrix:
$$A^{-1} = \frac{1}{\det(A)}\text{adj}(A)$$
where adj(A) is the adjugate matrix

#### Gaussian Elimination

1. Form augmented matrix $[A|I]$
2. Convert left side to identity matrix
3. Right side becomes $A^{-1}$

### Elementary Matrices

- Result from applying elementary row operations to identity matrix
- Types:
  1. Row swap: $E_{ij}$
  2. Row multiplication: $E_i(c)$
  3. Row addition: $E_{ij}(c)$
- Properties:
  - Always invertible
  - $(E_1E_2...E_k)A = A'$ where $A'$ is row reduced form

## Conjugate Transpose

For matrix $A$:

- Denoted as $A^H$ or $A^*$
- $(a_{ij})^H = \overline{a_{ji}}$
- Properties:
  - $(A^H)^H = A$
  - $(AB)^H = B^HA^H$
  - $(A + B)^H = A^H + B^H$
  - For real matrices, $A^H = A^T$

# Systems of Linear Equations (cont. 1)

## Homogeneous Systems ($A\mathbf{x} = \mathbf{0}$)

A system where all constants are zero: $A\mathbf{x} = \mathbf{0}$

### Trivial Solution

- Always has solution $\mathbf{x} = \mathbf{0}$ (zero vector)
- Exists for any coefficient matrix $A$

### Nontrivial Solutions

- Exist if and only if $\text{rank}(A) < n$ where $n$ is number of variables
- Equivalent to $\text{det}(A) = 0$ for square matrices
- Number of free variables = $n - \text{rank}(A)$

## Consistency Theorems

### Consistent System Conditions

| Condition     | System is Consistent When                                 |
| ------------- | --------------------------------------------------------- |
| Rank Test     | $\text{rank}(A) = \text{rank}([A\|\mathbf{b}])$           |
| Square Matrix | $\text{det}(A) \neq 0$                                    |
| General       | Solutions exist if $\mathbf{b}$ is in column space of $A$ |

### Fredholm Alternative

For system $A\mathbf{x} = \mathbf{b}$, exactly one of these is true:

1. System has a solution
2. $\mathbf{y}^T A = \mathbf{0}$ has a solution with $\mathbf{y}^T\mathbf{b} \neq 0$

## Cramer's Rule

For system $A\mathbf{x} = \mathbf{b}$ where $A$ is $n \times n$ with $\text{det}(A) \neq 0$:
$$x_i = \frac{\text{det}(A_i)}{\text{det}(A)}$$
Where $A_i$ is matrix $A$ with column $i$ replaced by $\mathbf{b}$

## Matrix Inverse Method

For square system $A\mathbf{x} = \mathbf{b}$ where $A$ is invertible:
$$\mathbf{x} = A^{-1}\mathbf{b}$$

Requirements:

- $A$ must be square
- $\text{det}(A) \neq 0$
- Computationally expensive for large systems

# Linear Transformations

## Definition

A linear transformation $T: V \to W$ is a function between vector spaces that preserves:

1. Addition: $T(u + v) = T(u) + T(v)$
2. Scalar multiplication: $T(cv) = cT(v)$

## Matrix Representation

Every linear transformation $T: \mathbb{R}^n \to \mathbb{R}^m$ can be represented by a unique $m \times n$ matrix $A$

### Standard Matrix

For transformation $T$, the standard matrix $A$ is formed by:
$$A = [T(e_1) \; T(e_2) \; \cdots \; T(e_n)]$$
where $e_i$ are standard basis vectors

## Properties

| Property               | Definition                               | Test                    |
| ---------------------- | ---------------------------------------- | ----------------------- |
| Kernel (Null Space)    | $\text{ker}(T) = \{v \in V : T(v) = 0\}$ | Solve $Ax = 0$          |
| Range (Image)          | $\text{range}(T) = \{T(v) : v \in V\}$   | Span of columns of $A$  |
| One-to-One (Injective) | $T(v_1) = T(v_2) \implies v_1 = v_2$     | $\text{ker}(T) = \{0\}$ |
| Onto (Surjective)      | $\text{range}(T) = W$                    | Columns span $W$        |
| Isomorphism            | Bijective linear transformation          | One-to-one and onto     |

## Special Transformations

### Rotation

- 2D rotation by angle $\theta$:
  $$R_\theta = \begin{bmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{bmatrix}$$

### Reflection

- Across x-axis: $\begin{bmatrix} 1 & 0 \\ 0 & -1 \end{bmatrix}$
- Across y-axis: $\begin{bmatrix} -1 & 0 \\ 0 & 1 \end{bmatrix}$

### Projection

- Onto x-axis: $\begin{bmatrix} 1 & 0 \\ 0 & 0 \end{bmatrix}$
- Onto y-axis: $\begin{bmatrix} 0 & 0 \\ 0 & 1 \end{bmatrix}$

### Scaling

- Scale by factors $a$ and $b$:
  $$\begin{bmatrix} a & 0 \\ 0 & b \end{bmatrix}$$

### Shearing

- Horizontal shear by $k$:
  $$\begin{bmatrix} 1 & k \\ 0 & 1 \end{bmatrix}$$
- Vertical shear by $k$:
  $$\begin{bmatrix} 1 & 0 \\ k & 1 \end{bmatrix}$$

# Inner Product Spaces

## Definition

An inner product on a vector space $V$ is a function $\langle \cdot,\cdot \rangle: V \times V \to \mathbb{R}$ (or $\mathbb{C}$)

## Properties

| Property              | Mathematical Form                                                       | Description                                    |
| --------------------- | ----------------------------------------------------------------------- | ---------------------------------------------- |
| Positive Definiteness | $\langle x,x \rangle \geq 0$ and $\langle x,x \rangle = 0 \iff x = 0$   | Always non-negative, zero only for zero vector |
| Symmetry              | $\langle x,y \rangle = \overline{\langle y,x \rangle}$                  | Complex conjugate for complex spaces           |
| Linearity             | $\langle ax+by,z \rangle = a\langle x,z \rangle + b\langle y,z \rangle$ | Linear in first argument                       |

## Norm

The norm induced by inner product: $\|x\| = \sqrt{\langle x,x \rangle}$

### Properties

- Non-negative: $\|x\| \geq 0$
- Positive definite: $\|x\| = 0 \iff x = 0$
- Homogeneous: $\|cx\| = |c|\|x\|$
- Triangle inequality: $\|x + y\| \leq \|x\| + \|y\|$

### Distance Function

$$d(x,y) = \|x-y\| = \sqrt{\langle x-y,x-y \rangle}$$

## Orthogonality

### Orthogonal Vectors

Two vectors $x,y$ are orthogonal if $\langle x,y \rangle = 0$

### Orthogonal Sets

- Set of vectors where each pair is orthogonal
- If normalized, called orthonormal set
- Orthonormal basis: orthonormal set that spans space

### Orthogonal Matrices

Matrix $Q$ is orthogonal if $Q^TQ = QQ^T = I$

#### Properties

| Property            | Formula                                 | Note                     |
| ------------------- | --------------------------------------- | ------------------------ |
| Inverse             | $Q^{-1} = Q^T$                          | Transpose equals inverse |
| Determinant         | $\det(Q) = \pm 1$                       | Always unit magnitude    |
| Column/Rows         | $\langle q_i,q_j \rangle = \delta_{ij}$ | Form orthonormal set     |
| Length Preservation | $\|Qx\| = \|x\|$                        | Preserves distances      |

### Orthogonal Complements

For subspace $W$, orthogonal complement $W^⊥$:
$$W^⊥ = \{x \in V : \langle x,w \rangle = 0 \text{ for all } w \in W\}$$

### Orthogonal Projections

Projection onto subspace $W$:
$$\text{proj}_W(x) = \sum_{i=1}^k \frac{\langle x,w_i \rangle}{\|w_i\|^2}w_i$$
where $\{w_1,\ldots,w_k\}$ is basis for $W$

For orthonormal basis:
$$\text{proj}_W(x) = \sum_{i=1}^k \langle x,w_i \rangle w_i$$

# Special Matrices (cont. 1)

| Type           | Definition             | Properties                                                                                                            | Example                                                                              |
| -------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Symmetric      | $A = A^T$              | - Diagonal elements can be any real number<br>- Elements symmetric across main diagonal<br>- All eigenvalues are real | $$\begin{bmatrix} 1 & 2 & 3\\ 2 & 4 & 5\\ 3 & 5 & 6 \end{bmatrix}$$                  |
| Skew-symmetric | $A = -A^T$             | - Diagonal elements must be zero<br>- $a_{ij} = -a_{ji}$<br>- All eigenvalues are imaginary or zero                   | $$\begin{bmatrix} 0 & 2 & -1\\ -2 & 0 & 3\\ 1 & -3 & 0 \end{bmatrix}$$               |
| Orthogonal     | $AA^T = A^TA = I$      | - $A^{-1} = A^T$<br>- Columns/rows form orthonormal basis<br>- $\det(A) = \pm 1$<br>- Preserves lengths and angles    | $$\begin{bmatrix} \cos\theta & -\sin\theta\\ \sin\theta & \cos\theta \end{bmatrix}$$ |
| Idempotent     | $A^2 = A$              | - Eigenvalues are only 0 or 1<br>- Trace = rank<br>- Used in projection matrices                                      | $$\begin{bmatrix} 1 & 0\\ 0 & 0 \end{bmatrix}$$                                      |
| Nilpotent      | $A^k = 0$ for some $k$ | - All eigenvalues = 0<br>- Trace = 0<br>- $k \leq n$ where $n$ is matrix size                                         | $$\begin{bmatrix} 0 & 1\\ 0 & 0 \end{bmatrix}$$                                      |

---

### Additional Properties:

1. **Symmetric Matrices**:

   - All real symmetric matrices are diagonalizable
   - $x^TAx$ is a quadratic form

2. **Orthogonal Matrices**:

   - Every column/row has unit length
   - Any two columns/rows are perpendicular
   - Preserves inner products: $(Ax)^T(Ay) = x^Ty$

3. **Idempotent Matrices**:

   - $I - A$ is also idempotent if $A$ is idempotent
   - Rank = Trace for idempotent matrices

4. **Nilpotent Matrices**:
   - The minimal $k$ for which $A^k = 0$ is called the index of nilpotency
   - Characteristic polynomial is $\lambda^n$

# Change of Basis

## Transition Matrices

A transition matrix $P$ transforms coordinates from one basis to another:
$$P_{B←C} = [v_1 \; v_2 \; \cdots \; v_n]$$
where $v_i$ are the basis vectors of B expressed in basis C

| Operation          | Formula                  | Meaning               |
| ------------------ | ------------------------ | --------------------- |
| Change from C to B | $[v]_B = P_{B←C}[v]_C$   | Vector v in basis B   |
| Change from B to C | $[v]_C = P_{C←B}[v]_B$   | Vector v in basis C   |
| Inverse relation   | $P_{C←B} = P_{B←C}^{-1}$ | Matrices are inverses |

## Similar Matrices

Two matrices A and B are similar if:
$$B = P^{-1}AP$$
where P is an invertible matrix

Properties:

- Similar matrices have same eigenvalues
- Similar matrices have same determinant
- Similar matrices have same trace
- Similar matrices have same rank

## Coordinate Vectors

For a vector $v$ and basis $B = \{b_1, b_2, ..., b_n\}$:
$$[v]_B = \begin{bmatrix} c_1 \\ c_2 \\ \vdots \\ c_n \end{bmatrix}$$
where $v = c_1b_1 + c_2b_2 + ... + c_nb_n$

## Orthogonalization

### Gram-Schmidt Process

Converting basis $\{v_1, v_2, ..., v_n\}$ to orthogonal basis $\{u_1, u_2, ..., u_n\}$:

1. $u_1 = v_1$
2. $u_2 = v_2 - \text{proj}_{u_1}(v_2)$
3. $u_3 = v_3 - \text{proj}_{u_1}(v_3) - \text{proj}_{u_2}(v_3)$

General formula:
$$u_k = v_k - \sum_{i=1}^{k-1} \text{proj}_{u_i}(v_k)$$
where $\text{proj}_u(v) = \frac{\langle v,u \rangle}{\langle u,u \rangle}u$

### QR Decomposition

Matrix A can be decomposed as:
$$A = QR$$
where:

- Q is orthogonal matrix ($Q^TQ = I$)
- R is upper triangular matrix

## Orthonormal Basis

### Construction

1. Start with any basis
2. Apply Gram-Schmidt process
3. Normalize each vector: $e_i = \frac{u_i}{\|u_i\|}$

### Properties

| Property          | Description                                                                                     |
| ----------------- | ----------------------------------------------------------------------------------------------- |
| Orthogonality     | $\langle e_i,e_j \rangle = 0$ for $i \neq j$                                                    |
| Normality         | $\|e_i\| = 1$ for all i                                                                         |
| Transition Matrix | P is orthogonal ($P^T = P^{-1}$)                                                                |
| Coordinates       | $[v]_B = [\langle v,e_1 \rangle \; \langle v,e_2 \rangle \; \cdots \; \langle v,e_n \rangle]^T$ |

# Eigenvalues and Eigenvectors

## Definitions

- **Eigenvalue** ($\lambda$): A scalar value where $A\vec{v} = \lambda\vec{v}$ for some nonzero vector $\vec{v}$
- **Eigenvector** ($\vec{v}$): A nonzero vector satisfying $A\vec{v} = \lambda\vec{v}$ for some scalar $\lambda$

## Characteristic Equation

$$\det(A - \lambda I) = 0$$
where:

- $A$ is the square matrix
- $\lambda$ is the eigenvalue
- $I$ is the identity matrix

### Characteristic Polynomial

$$p(\lambda) = \det(A - \lambda I)$$

- Degree equals matrix dimension
- Roots are eigenvalues

## Properties

| Property | Description                        |
| -------- | ---------------------------------- |
| Sum      | $\sum \lambda_i = \text{trace}(A)$ |
| Product  | $\prod \lambda_i = \det(A)$        |
| Number   | ≤ dimension of matrix              |

### Geometric Multiplicity

- Number of linearly independent eigenvectors for a given eigenvalue
- ≤ algebraic multiplicity
- = dimension of null space of $(A - \lambda I)$

### Algebraic Multiplicity

- Multiplicity of eigenvalue as root of characteristic polynomial
- ≥ geometric multiplicity

### Eigenspace

$$E_\lambda = \text{null}(A - \lambda I)$$

- Subspace spanned by eigenvectors for eigenvalue $\lambda$
- Dimension = geometric multiplicity

## Diagonalization

$A = PDP^{-1}$ where:

- $D$ is diagonal matrix of eigenvalues
- $P$ is matrix of eigenvectors

### Diagonalizability Conditions

Matrix $A$ is diagonalizable if and only if:

1. Geometric multiplicity = algebraic multiplicity for all eigenvalues
2. Sum of dimensions of eigenspaces = matrix dimension

### Diagonalization Process

1. Find eigenvalues (solve characteristic equation)
2. Find eigenvectors for each eigenvalue
3. Form $P$ from eigenvectors as columns
4. Form $D$ with eigenvalues on diagonal
5. Verify $A = PDP^{-1}$

### Similar Matrices

- $A$ and $B$ similar if $B = P^{-1}AP$ for invertible $P$
- Similar matrices have same eigenvalues
- Similar matrices have same characteristic polynomial

## Special Cases

### Repeated Eigenvalues

- May have fewer linearly independent eigenvectors
- Need generalized eigenvectors if geometric multiplicity < algebraic multiplicity

### Complex Eigenvalues

- Occur in conjugate pairs for real matrices
- Complex eigenvectors also occur in conjugate pairs

## Applications

### Powers of Matrices

$$A^n = PD^nP^{-1}$$

- Simplifies computation of matrix powers
- Useful for recursive sequences

### Difference Equations

For system $\vec{x}_{k+1} = A\vec{x}_k$:

- General solution involves eigenvalues and eigenvectors
- Stability determined by $|\lambda| < 1$

### Differential Equations

For system $\frac{d\vec{x}}{dt} = A\vec{x}$:

- Solutions of form $\vec{x}(t) = ce^{\lambda t}\vec{v}$
- Stability determined by $\text{Re}(\lambda) < 0$

---

# Important Theorems

## Fundamental Theorem of Linear Algebra

For a linear transformation $T: V \rightarrow W$ and its matrix $A$:

- $\text{Null}(A) \oplus \text{Row}(A^T) = \mathbb{R}^n$
- $\text{Col}(A) \oplus \text{Null}(A^T) = \mathbb{R}^m$
- $\dim(\text{Null}(A)) + \dim(\text{Col}(A)) = n$
- $\text{rank}(A) + \text{nullity}(A) = n$

## Cayley-Hamilton Theorem

Every square matrix $A$ satisfies its own characteristic equation:
$$p(A) = 0 \text{ where } p(\lambda) = \det(A - \lambda I)$$

## Spectral Theorem

For symmetric matrices $A \in \mathbb{R}^{n \times n}$:

- All eigenvalues are real
- Eigenvectors of distinct eigenvalues are orthogonal
- $A = PDP^T$ where:
  - $P$ is orthogonal ($P^TP = I$)
  - $D$ is diagonal containing eigenvalues

## Triangle Inequality

For vectors $x, y$:
$$\|x + y\| \leq \|x\| + \|y\|$$

## Cauchy-Schwarz Inequality

For vectors $x, y$:
$$|x^Ty| \leq \|x\|\|y\|$$

- Equality holds if and only if vectors are linearly dependent

## Invertible Matrix Theorem

The following statements are equivalent for a square matrix $A$:

1. $A$ is invertible
2. $\det(A) \neq 0$
3. $\text{rank}(A) = n$
4. $\text{Null}(A) = \{0\}$
5. Columns are linearly independent
6. $Ax = b$ has unique solution for all $b$

## Matrix Factorization Theorems

### LU Decomposition

For matrix $A$:
$$A = LU$$
where:

- $L$ is lower triangular
- $U$ is upper triangular
- Exists if all leading principal minors are nonzero

### QR Decomposition

For matrix $A$:
$$A = QR$$
where:

- $Q$ is orthogonal ($Q^TQ = I$)
- $R$ is upper triangular
- Always exists for full-rank matrices

### Cholesky Decomposition

For symmetric positive definite matrix $A$:
$$A = LL^T$$
where:

- $L$ is lower triangular
- $L^T$ is upper triangular
- Elements are real

# Advanced Topics

## Singular Value Decomposition (SVD)

Any matrix $A \in \mathbb{R}^{m \times n}$ can be decomposed as $A = U\Sigma V^T$

### Singular Values

- Diagonal entries $\sigma_i$ of $\Sigma$ matrix
- $\sigma_i = \sqrt{\lambda_i(A^TA)}$
- Always real and non-negative
- Ordered: $\sigma_1 \geq \sigma_2 \geq ... \geq \sigma_n \geq 0$

### U and V Matrices

- $U$: $m \times m$ orthogonal matrix (left singular vectors)
- $V$: $n \times n$ orthogonal matrix (right singular vectors)
- $\Sigma$: $m \times n$ diagonal matrix with singular values

### Applications

| Application                  | Description                                        |
| ---------------------------- | -------------------------------------------------- |
| Low-rank approximation       | Truncate to $k$ largest singular values            |
| Image compression            | Reduce dimensionality while preserving structure   |
| Principal Component Analysis | Use right singular vectors as principal components |
| Pseudoinverse                | $A^+ = V\Sigma^+U^T$                               |

## Jordan Canonical Form

For matrix $A$, exists invertible $P$ such that $P^{-1}AP = J$

### Jordan Blocks

$$
J_k(\lambda) = \begin{bmatrix}
\lambda & 1 & 0 & \cdots & 0 \\
0 & \lambda & 1 & \cdots & 0 \\
\vdots & \vdots & \ddots & \ddots & \vdots \\
0 & 0 & \cdots & \lambda & 1 \\
0 & 0 & \cdots & 0 & \lambda
\end{bmatrix}
$$

### Generalized Eigenvectors

- Chain: $(A-\lambda I)^kv_k = 0$
- $v_1$ is regular eigenvector
- $(A-\lambda I)v_{i+1} = v_i$

## Positive Definite Matrices

Symmetric matrix $A$ where $x^TAx > 0$ for all nonzero $x$

### Tests for Positive Definiteness

| Test               | Condition                                          |
| ------------------ | -------------------------------------------------- |
| Eigenvalue         | All eigenvalues > 0                                |
| Leading Principals | All leading principal minors > 0                   |
| Cholesky           | Exists unique lower triangular $L$ with $A = LL^T$ |
| Quadratic Form     | $x^TAx > 0$ for all nonzero $x$                    |

### Applications

- Optimization problems
- Covariance matrices
- Least squares solutions
- Energy functions

## Linear Operators

Maps between vector spaces preserving linear structure

### Adjoint Operators

- For operator $T$, adjoint $T^*$ satisfies $\langle Tx,y \rangle = \langle x,T^*y \rangle$
- Matrix representation: conjugate transpose
- Properties:
  - $(T^*)^* = T$
  - $(ST)^* = T^*S^*$
  - $(\alpha T)^* = \overline{\alpha}T^*$

### Self-Adjoint Operators

- $T = T^*$
- Real eigenvalues
- Orthogonal eigenvectors
- Spectral theorem applies

## Dual Spaces

Vector space $V^*$ of linear functionals on $V$

### Dual Basis

- For basis $\{e_i\}$ of $V$, dual basis $\{e_i^*\}$ satisfies $e_i^*(e_j) = \delta_{ij}$
- Dimension equals original space
- Natural pairing: $\langle f,v \rangle = f(v)$

### Dual Maps

For linear map $T: V \to W$, dual map $T^*: W^* \to V^*$
$$\langle T^*f,v \rangle = \langle f,Tv \rangle$$

## Tensor Products

$V \otimes W$ is universal space for bilinear maps

### Definition

- Elementary tensors: $v \otimes w$
- Bilinear in components:
  - $(av_1 + bv_2) \otimes w = av_1 \otimes w + bv_2 \otimes w$
  - $v \otimes (aw_1 + bw_2) = av \otimes w_1 + bv \otimes w_2$

### Properties

| Property             | Description                                                         |
| -------------------- | ------------------------------------------------------------------- |
| Dimension            | $\dim(V \otimes W) = \dim(V)\dim(W)$                                |
| Associativity        | $(U \otimes V) \otimes W \cong U \otimes (V \otimes W)$             |
| Distributivity       | $(U \oplus V) \otimes W \cong (U \otimes W) \oplus (V \otimes W)$   |
| Field multiplication | $(\alpha v) \otimes w = v \otimes (\alpha w) = \alpha(v \otimes w)$ |

## Multilinear Algebra

### Tensors

- Multilinear maps: $T: V_1 \times ... \times V_k \to W$
- Type $(r,s)$: $r$ contravariant, $s$ covariant indices
- Transformation rules under basis change

### Exterior Algebra

- Antisymmetric tensors
- Wedge product $\wedge$
- Properties:
  - Anticommutativity: $v \wedge w = -w \wedge v$
  - Associativity: $(u \wedge v) \wedge w = u \wedge (v \wedge w)$
  - Distributivity over addition
  - $k$-forms and differential forms
