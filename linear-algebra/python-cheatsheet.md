# Fundamentals of Vectors

## Working with Vectors in NumPy

```py
import numpy as np
```

### Creating Vectors

```python
# Row vector
v_row = np.array([1, 2, 3])

# Column vector
v_col = np.array([[1], [2], [3]])
assert v_col = np.transpose(v_row)
```

### Vector Operations

```python
# Addition
v1, v2 = np.array([1, 2, 3]), np.array([4, 5, 6])
v_sum = v1 + v2

# Subtraction
v_diff = v1 - v2

# Scalar multiplication
c = 2
v_scaled = c * v1

# Dot product
dot_product = np.dot(v1, v2)

# Cross product
cross_product = np.cross(v1, v2)
```

### Vector Norms

```python
# L1 norm
l1_norm = np.linalg.norm(v, ord=1)

# L2 norm
l2_norm = np.linalg.norm(v, ord=2)

# Infinity norm
inf_norm = np.linalg.norm(v, ord=np.inf)
```

### Useful Functions

```python
# Normalize vector
normalize = lambda v: v / np.linalg.norm(v)

# Angle between vectors (radians)
angle_rad = lambda v1, v2: np.arccos(np.clip(np.dot(normalize(v1), normalize(v2)), -1.0, 1.0))

# Angle between vectors (degrees)
angle_deg = lambda v1, v2: np.degrees(angle_rad(v1, v2))

# Projection of v1 onto v2
projection = lambda v1, v2: np.dot(v1, normalize(v2)) * normalize(v2)

# Rejection of v1 from v2
rejection = lambda v1, v2: v1 - projection(v1, v2)

# Distance between vectors
distance = lambda v1, v2: np.linalg.norm(v1 - v2)
```

### Visualization with Matplotlib

```python
import matplotlib.pyplot as plt
```

#### 2D Vectors

```python
import numpy as np
import matplotlib.pyplot as plt

def plot_2d(*vectors, figsize=(10, 10), arrows=True, grid=True, equal_aspect=True):
    """
    Plot multiple 2D vectors on a Cartesian plane.

    Parameters:
    -----------
    *vectors : array-like
        Variable number of 2D vectors to plot. Each vector should be a 2D point
        or array-like object with x and y coordinates.
    figsize : tuple, optional (default=(10, 10))
        Figure size as (width, height)
    arrows : bool, optional (default=True)
        If True, draws vectors as arrows from origin. If False, plots as points/lines.
    grid : bool, optional (default=True)
        Whether to show the grid
    equal_aspect : bool, optional (default=True)
        Whether to maintain equal aspect ratio for x and y axes

    Returns:
    --------
    fig, ax : tuple
        Matplotlib figure and axis objects
    """
    # convert all inputs to numpy arrays
    vectors = [np.array(v, dtype=float) if not isinstance(v, np.ndarray) else v for v in vectors]

    # validate inputs
    for i, v in enumerate(vectors):
        if v.shape != (2,):
            raise ValueError(f"Vector {i} has shape {v.shape}, expected (2,)")

    fig, ax = plt.subplots(figsize=figsize)

    colors = plt.cm.tab10(np.linspace(0, 1, len(vectors)))

    for v, color in zip(vectors, colors):
        if arrows:
            ax.quiver(0, 0, v[0], v[1], angles='xy', scale_units='xy', scale=1,
                     color=color, width=0.005)
        else:
            ax.plot([0, v[0]], [0, v[1]], '-o', color=color)

    all_coords = np.vstack(vectors)
    max_abs_coord = np.max(np.abs(all_coords)) * 1.2  # Add 20% padding
    ax.set_xlim(-max_abs_coord, max_abs_coord)
    ax.set_ylim(-max_abs_coord, max_abs_coord)
    ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)  # x-axis
    ax.axvline(x=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)  # y-axis

    if grid:
        ax.grid(True, linestyle='--', alpha=0.3)

    if equal_aspect:
        ax.set_aspect('equal')

    ax.set_xlabel('x')
    ax.set_ylabel('y')

    return fig, ax
```

#### 3D Vectors

```python
import numpy as np
import matplotlib.pyplot as plt

def plot_3d(*vectors):
    """Plot multiple 3D vectors from origin as lines with dots at endpoints."""
    # Convert inputs to numpy arrays
    vectors = [np.array(v) for v in vectors]

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    for v in vectors:
        # Plot line from origin to vector endpoint with dot
        ax.plot([0, v[0]], [0, v[1]], [0, v[2]], '-o')

    # Set equal aspect ratio and add labels
    ax.set_box_aspect([1,1,1])
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_zlabel('z')

    return fig, ax
```

# Matrices

## Working with Matrices in NumPy

```py
import numpy as np
```

### Creating Matrices

```python
# 2D array
A = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

# Identity matrix
I = np.eye(3)

# Zero matrix
Z = np.zeros((3, 3))

# Ones matrix
O = np.ones((3, 3))

# Random matrix
R = np.random.rand(3, 3)
```

### Matrix Operations

```python
# Addition
A1, A2 = np.array([[1, 2], [3, 4]]), np.array([[5, 6], [7, 8]])
A_sum = A1 + A2

# Subtraction
A_diff = A1 - A2

# Scalar multiplication
c = 2
A_scaled = c * A1

# Matrix multiplication
A_prod = np.dot(A1, A2)

# Transpose
A_transpose = np.transpose(A)

# Inverse
A_inv = np.linalg.inv(A)

# Determinant
det_A = np.linalg.det(A)

# Trace
trace_A = np.trace(A)

# Rank
rank_A = np.linalg.matrix_rank(A)

# Eigenvalues and eigenvectors
eigenvalues, eigenvectors = np.linalg.eig(A)

# Singular value decomposition
U, S, V = np.linalg.svd(A)

# Matrix norms
l1_norm = np.linalg.norm(A, ord=1)

l2_norm = np.linalg.norm(A, ord=2)

inf_norm = np.linalg.norm(A, ord=np.inf)

fro_norm = np.linalg.norm(A, ord='fro')

# Matrix power
A_squared = np.linalg.matrix_power(A, 2)
```

# Systems of Linear Equations

## Solving Linear Systems

### Matrix Inversion Method

```python
A = np.array([[2, 1], [1, 1]])
b = np.array([3, 2])

x = np.linalg.inv(A).dot(b)

# or, much faster

x = np.linalg.solve(A, b)

print(x)
```

# Vector Spaces

## Linear Independence, Span, Basis

```python

# check if set of vectors is linearly independent
is_linearly_independent = lambda *vectors: np.linalg.matrix_rank(np.array(vectors)) == len(vectors[0])

# check if vector is in span of other vectors
is_in_span = lambda v, *S: np.linalg.matrix_rank(np.array([*S, v])) == np.linalg.matrix_rank(S)

# find basis of a set of vectors
basis = lambda *vectors: np.array(vectors).T[:, np.linalg.matrix_rank(np.array(vectors)):]
```
# Matrix Properties (cont. 1)

## Dimension, Rank, Nullity, Row Space

```python
# dimension of a vector space
dim = lambda *vectors: np.linalg.matrix_rank(np.array(vectors))
rank = lambda A: np.linalg.matrix_rank(A)
nullity = lambda A: A.shape[1] - rank(A)
```

## Special Transformations

```python
# reflection matrix
reflect = lambda n: np.eye(len(n)) - 2 * np.outer(n, n) / np.dot(n, n)

# projection matrix
project = lambda n: np.outer(n, n) / np.dot(n, n)

# rotation matrix
rotate = lambda theta: np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])

# scaling matrix
scale = lambda s: np.diag(s)

# shearing matrix
shear = lambda s: np.array([[1, s], [0, 1]])

# translation matrix
translate = lambda t: np.array([[1, 0, t[0]], [0, 1, t[1]], [0, 0, 1]])

# homogenous coordinates
homogenize = lambda v: np.append(v, 1)

# dehomogenize
dehomogenize = lambda v: v[:-1] / v[-1]

# affine transformation
affine = lambda A, t: np.block([[A, t], [0, 0, 1]])

# perspective transformation
perspective = lambda d: np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1/d]])
```


## Orthogonality

```python
# check if two vectors are orthogonal
is_orthogonal = lambda u, v: np.dot(u, v) == 0

# check if set of vectors is orthogonal
is_orthogonal_set = lambda *vectors: all(np.dot(v1, v2) == 0 for v1, v2 in itertools.combinations(vectors, 2))

# check if set of vectors is orthonormal
is_orthonormal_set = lambda *vectors: is_orthogonal_set(*vectors) and all(np.linalg.norm(v) == 1 for v in vectors)

# check if matrix is orthogonal
is_orthogonal_matrix = lambda A: np.allclose(np.dot(A, A.T), np.eye(A.shape[0]))

# check if matrix is orthonormal
is_orthonormal_matrix = lambda A: is_orthogonal_matrix(A) and np.allclose(np.linalg.det(A), 1)
```

# Change of Basis

```python
# change of basis matrix
change_of_basis = lambda B, C: np.linalg.inv(C) @ B
```
