---
title: Feedforward Neural Networks
category: Natural Language Processing
tags: neural networks, machine learning, natural language processing, deep learning, feedforward
description: Overview of neural networks (feedforward), particularly in the context of natural language processing.
source: https://web.stanford.edu/~jurafsky/slp3/7.pdf
---

# Neural Networks

Contrasting with MLR, neural networks are a more flexible model that can learn complex patterns in the data, even without hand-crafted features.


## Activation Functions

A single computational unit $z = w \cdot x + b$ is a linear function of the input $x$ with weights $w$ and bias $b$. The output $y$ is a non-linear function of $f(z)$, where $f$ is the activation function (typically one of $\tanh$, $\text{ReLU}$, or $\sigma$).

$$
y = \sigma(w \cdot x + b) = \frac{1}{1 + e^{-(w \cdot x + b)}}
$$

In practice, $\sigma$ is rarely the best choice, and $\tanh$ is similar yet almost always better. $\tanh$ is a scaled version of $\sigma$ that ranges from $-1$ to $1$.

$$
y = \tanh(w \cdot x + b) = \frac{e^{w \cdot x + b} - e^{-(w \cdot x + b)}}{e^{w \cdot x + b} + e^{-(w \cdot x + b)}}
$$

The simplest activation function is the Rectified Linear Unit (ReLU), which is $0$ for negative inputs and linear for positive inputs.

$$
y = \text{ReLU}(w \cdot x + b) = \max(0, w \cdot x + b)
$$

A potential upside with ReLU is that it is computationally efficient, and also prevents the vanishing gradient problem, e.g. when the gradient is $\approx 0$, and the network stops learning.

## The XOR Problem

It can be shown that a single computational unit cannot solve XOR, as it is a non-linear problem. However, a two-layer network can solve XOR, as it can learn to represent the input in a higher-dimensional space where the problem is linearly separable.

$$
y = \begin{cases}
1 & \text{if } w \cdot x + b > 0 \\
0 & \text{otherwise}
\end{cases}
$$

XOR turns out to be a simple example of a problem that is not linearly separable in the input space, since the inputs $(x_1, x_2) = (0, 0)$ and $(1, 1)$ are in the same class, while $(0, 1)$ and $(1, 0)$ are in the other class. It is not possible to draw a straight line that separates the two classes.

## Feedforward Neural Networks

A feedforward NN is a multi-layer network where the output of each layer is the input to the next layer, all with no cycles. They are sometimes called multilayer perceptrons (MLPs), although this term is technically only applicable to networks with a single step function as their activation function.

The network has three different types of nodes:

### Input units

vector of input units is $x$. One node for each feature in the input.

### Hidden layers

one or more layers of hidden units, each with a non-linear activation function. In the standard architecture, each node is connected with all nodes in the previous layer. Thus, each hidden unit sums over all input values.

For a given hidden layer $h$, we combine the weights $w$ and bias $b$ for each computational unit into a weight matrix $W$ and bias vector $b$. Each element $W_{ij}$ of the weight matrix is the weight from the $i$th input unit $x_i$ to the $j$th hidden unit $h_j$.

Thus, the output for a given hidden layer with activation function $f$ is:

$$
h = f(W \cdot x + b)
$$

#### Dimensionality

Referring to the input layer as layer $0$, and $n_0$ as the number of input units, we have an input $x \in \mathbb{R}^{n_0}$, e.g. a column vector with dimension $n_0 \times 1$.

The first hidden layer $h^{(1)}$ has $n_1$ hidden units, so $W \in \mathbb{R}^{n_1 \times n_0}$, and $b \in \mathbb{R}^{n_1}$.

$$
h_j = f\left(\sum_{i=1}^{n_0} W_{ji} x_i + b_j\right)
$$

### Output units

one or more output units, each with a non-linear activation function. The output layer is the final layer of the network, and the output $y$ with $dim(y) = n_{\text{output}}$ is an estimate for the probability distribution of the correct class/output.

#### Normalization

In order to get that probability distribution, we normalize the output of the network using the softmax function.

$$
y = \text{softmax}(W \cdot h + b)
$$

$$
\text{softmax}(z) = \frac{e^z}{\sum_{i=1}^n e^{z_i}}
$$


### Comparison with MLR

A NN is like MLR but with with a few differences:
- many layers, since a deep NN is like layer after layer of MLR classifiers
- intermediate layers have non-linear activation functions. In fact, without these, the network would just be a linear classifier since the composition of linear functions is still linear
- instead of feature selection, previous layers build up a representation of the input that is useful for the final layer

### Details/Notation

- $*^{[l]}$ denotes a quantity associated with the $l$th layer, e.g. $W^{[l]}$ is the weight matrix for the $l$th layer. Note that these indices are 1-indexed.
- $n_l$ is the number of units in layer $l$.
- $g(.)$ is the activation function, which tends to be $\tanh$ or ReLU for hidden layers, and softmax for the output layer.
- $a^{[l]}$ is the output from layer $l$
- $z^{[l]}$ is the input to the activation function in layer $l$, e.g. $z^{[l]} = W^{[l]} \cdot a^{[l-1]} + b^{[l]}$
- $x = a^{[0]}$ is the input vector

#### Example: 2-layer NN

$$
\begin{aligned}
z^{[1]} &= W^{[1]} \cdot a^{[0]} + b^{[1]} \\
a^{[1]} &= g^{[1]}(z^{[1]}) \\
z^{[2]} &= W^{[2]} \cdot a^{[1]} + b^{[2]} \\
a^{[2]} &= g^{[2]}(z^{[2]}) \\
\hat{y} &= a^{[2]}
\end{aligned}
$$

### Feedforward Computation

$$
\begin{aligned}
\text{for } l = 1, \ldots, L: \\
z^{[l]} &= W^{[l]} \cdot a^{[l-1]} + b^{[l]} \\
a^{[l]} &= g^{[l]}(z^{[l]})\\

\text{return } \hat{y} = a^{[L]}
\end{aligned}
$$

```python
def feedforward(x):
  a = x
  for l in range(1, L):
    z = W[l] @ a + b[l]
    a = g[l](z)
  return a
```

### Replacing the Bias

Often, the bias term is included in the weight matrix, by adding a column of $1$s to the input vector $x$.

With $a^{[0]}_0 = 1$, we can write $z^{[l]} = W^{[l]} \cdot a^{[l-1]}$.

$$
h_j = f\left(\sum_{i=1}^{n_0} W_{ji} x_i\right)
$$

## FF networks for NLP: Classification

Instead of manually designed features, use words as embeddings (e.g. word2vec, GloVe). This constitutes "pre-training", i.e. relying on already computed values/embeddings. One simple method of representing a sentence is to sum the embeddings of the words in the sentence, or to average them.

To classify many examples at once, pack inputs into a single matrix $X$ where each row $i$ is an input vector $x^{(i)}$. If our input has $d$ features, then $X \in \mathbb{R}^{m \times d}$ where $m$ is the number of examples.

$W \in \mathbb{R}^{d_h \times d}$ is the weight matrix for the hidden layer, and $b \in \mathbb{R}^{d_h}$ is the bias vector. $Y \in \mathbb{R}^{m \times n_{\text{output}}}$ is the output matrix.

$$
\begin{aligned}
H &= f(X W^T + b) \\
Z &= H U^T\\
\hat{Y} &= \text{softmax}(Z)
\end{aligned}
$$

## Training Neural Nets

We want to learn the parameters $W^{[i]}$ and $b^{[i]}$ for each layer $i$ that make $\hat{y}$ as close as possible to the true $y$.

### Loss Function

Same as the one used for MLR, the cross-entropy loss function.


For binary classification, the loss function is:
$$
L_{\text{CE}}(\hat{y}, y) = - \log p(y | x) = - \left [ y \log \hat{y} + (1 - y) \log (1 - \hat{y}) \right ]
$$

For multi-class classification, the loss function is:

$$
L_{\text{CE}}(\hat{y}, y) = - \sum_{i=1}^n y_i \log \hat{y}_i = - \log \hat{y}_i \text{ where } y_i = 1
$$

$$
L_{\text{CE}}(\hat{y}, y) = -\log \frac{exp(z_{c})}{\sum_{i=1}^K exp(z_i)}
$$

### Backpropagation

One must pass gradients back through the network to update the weights. This is done using the chain rule. Each node in a computation graph takes an **upstream** gradient and computes its **local** gradient, multiplying the two to get the **downstream** gradient. A node may have multiple local gradients, one for each incoming edge.

#### A very simple example

Consider the function $L(a, b, c) = c(a + 2b)$. Create a computation graph with nodes $a, b, c$ for the inputs, and $d = 2b, e = a + d, L = ce$ for the intermediate computations.

```
(a) ---------------- \
                      (e) ------------ (L)
                     /                /
(b) --------(d)-----    /-------------
                       /
(c) -------------------
```

$$
\begin{aligned}
\frac{\partial L}{\partial c} &= e = a + 2b \\
\frac{\partial L}{\partial a} &= \frac{\partial L}{\partial e} \cdot \frac{\partial e}{\partial a} = c \\
\frac{\partial L}{\partial b} &= \frac{\partial L}{\partial e} \cdot \frac{\partial e}{\partial d} \cdot \frac{\partial d}{\partial b} = 2c
\end{aligned}
$$

### Learning details

NN optimization is a non-convex optimization problem, so it requires a few techniques to work well:

- Initialize weights and biases to small random values instead of all zeros
- Normalize input values to $\mu = 0, \sigma = 1$
- Dropout: randomly (with probability $p$) set some hidden units to 0, then renormalize other inputs to prevent overfitting
- Hyperparameters: learning rate, mini-batch size, number of hidden units, number of layers, choice of activation function, etc.