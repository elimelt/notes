# This is a test to see if I can properly render LaTeX in a markdown file.

# $$
# \begin{align}
# \dot{x} & = \sigma(y-x) \\
# \dot{y} & = \rho x - y - xz \\
# \dot{z} & = -\beta z + xy
# \end{align}
# $$
#
# $$

\sigma = 10, \quad \rho = 28, \quad \beta = \frac{8}{3}

$$
P = \begin{bmatrix}
1 & 0 & 0 & 0 \\
0 & 0 & 1 & 0 \\
0 & 1 & 0 & 0 \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

# This is a test to see if I can properly render HTML in a markdown file.

<em>Emphasis</em>, <strong>strong</strong>, <code>code</code>, <a href="http://example.com">link</a>.

# This is a test to see if I can render a table in a markdown file.

| Syntax | Description |
| ----------- | ----------- |
| Header | Title |
| Paragraph | Text |
| Large paragraph of many words repated over and over again. Large paragraph of many words repeated over and over and over again. Large paragraph of many words repeated over and over and over again. Large paragraph of many words repeated over and over and over again. Large paragraph of many words repeated over and over and over again. Large paragraph of many words repeated over and over and over again.| Text |

# This is a test to see if I can render a code block in a markdown file.

```python
def test():
    print("Hello World!")
```