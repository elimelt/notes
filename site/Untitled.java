# Multinomial Logistic Regression (MLR)

## Introduction

Multinomial Logistic Regression (MLR) is a generalization of binary logistic regression that allows for classification into multiple classes. It's a powerful and interpretable model widely used in Natural Language Processing (NLP) and other fields.

## Key Concepts

### Features

In MLR, features are functions that map input-output pairs to real numbers:

$f_j: \mathcal{V}^* \times \mathcal{L} \rightarrow \mathbb{R}$

Where $\mathcal{V}^*$ is the set of all possible input sequences and $\mathcal{L}$ is the set of all possible labels.

A common template for features is:

$f_{\ell,\phi}(x, y) = \phi(x) \cdot \mathbb{1}\{y = \ell\}$

Where $\phi(x)$ is some function of the input and $\mathbb{1}\{y = \ell\}$ is an indicator function.

```python
import numpy as np

def feature_template(phi, l):
    def feature(x, y):
        return phi(x) * (y == l)
    return feature

# Example usage
def word_count(x, word):
    return x.lower().count(word)

f_sports_vodka = feature_template(lambda x: word_count(x, 'vodka'), 'sports')
```

### Model Definition

An MLR model is defined by:

1. A set of feature functions $f_1, ..., f_d$
2. A weight vector $\theta \in \mathbb{R}^d$

The score for a given input-output pair is:

$\text{score}_{\text{MLR}}(x, y; \theta) = \sum_{j=1}^d \theta_j f_j(x, y) = \theta^T f(x, y)$

The classification rule is:

$\text{classify}_{\text{MLR}}(x) = \arg\max_{y \in \mathcal{L}} \text{score}_{\text{MLR}}(x, y; \theta)$

```python
def score_mlr(x, y, theta, features):
    return sum(theta[j] * f(x, y) for j, f in enumerate(features))

def classify_mlr(x, theta, features, labels):
    return max(labels, key=lambda y: score_mlr(x, y, theta, features))
```

### Probabilistic Interpretation

MLR defines a probability distribution over labels:

$p_{\text{MLR}}(Y | X = x; \theta) = \text{softmax}(\langle\text{score}_{\text{MLR}}(x, \ell; \theta)\rangle_{\ell \in \mathcal{L}})$

Where softmax is defined as:

$\text{softmax}(t_1, ..., t_k) = (\frac{e^{t_1}}{\sum_{j=1}^k e^{t_j}}, ..., \frac{e^{t_k}}{\sum_{j=1}^k e^{t_j}})$

```python
def softmax(scores):
    exp_scores = np.exp(scores)
    return exp_scores / np.sum(exp_scores)

def p_mlr(x, theta, features, labels):
    scores = [score_mlr(x, y, theta, features) for y in labels]
    return softmax(scores)
```

## Learning

The learning objective for MLR is to minimize the negative log-likelihood (also known as cross-entropy loss) plus a regularization term:

$\theta^* = \arg\min_{\theta \in \mathbb{R}^d} \sum_{i=1}^n -\log p_{\text{MLR}}(Y = y_i | X = x_i; \theta) + \lambda \|\theta\|_p^p$

Where $\lambda > 0$ is a hyperparameter and $p = 1$ or $2$ for L1 or L2 regularization respectively.

```python
def negative_log_likelihood(theta, X, y, features, labels, lambda_, p):
    nll = sum(-np.log(p_mlr(x, theta, features, labels)[labels.index(y_i)])
              for x, y_i in zip(X, y))
    reg = lambda_ * np.linalg.norm(theta, ord=p)**p
    return nll + reg

from scipy.optimize import minimize

def train_mlr(X, y, features, labels, lambda_=0.1, p=2):
    d = len(features)
    theta_init = np.zeros(d)
    result = minimize(lambda theta: negative_log_likelihood(theta, X, y, features, labels, lambda_, p),
                      theta_init, method='L-BFGS-B')
    return result.x
```

## Implementation Considerations

1. Feature engineering is crucial for MLR performance.
2. L1 regularization can lead to sparse models, effectively performing feature selection.
3. MLR can be computationally expensive for large label sets due to the normalization factor in the softmax.
4. Stochastic gradient descent or its variants are often used for large-scale problems.

## Evaluation

Common evaluation metrics include accuracy, precision, recall, and F1 score. Cross-validation is often used to get more reliable estimates of model performance.

```python
from sklearn.model_selection import cross_val_score
from sklearn.metrics import make_scorer, accuracy_score, precision_score, recall_score, f1_score

def mlr_classifier(theta, features, labels):
    return lambda X: [classify_mlr(x, theta, features, labels) for x in X]

def evaluate_mlr(X, y, features, labels, lambda_=0.1, p=2, cv=5):
    theta = train_mlr(X, y, features, labels, lambda_, p)
    clf = mlr_classifier(theta, features, labels)
    
    scorers = {
        'accuracy': make_scorer(accuracy_score),
        'precision': make_scorer(precision_score, average='weighted'),
        'recall': make_scorer(recall_score, average='weighted'),
        'f1': make_scorer(f1_score, average='weighted')
    }
    
    scores = {metric: cross_val_score(clf, X, y, cv=cv, scoring=scorer)
              for metric, scorer in scorers.items()}
    
    return {metric: (np.mean(score), np.std(score)) for metric, score in scores.items()}
```

This implementation provides a comprehensive overview of Multinomial Logistic Regression, including its key concepts, model definition, learning process, and evaluation methods. The code examples demonstrate how to implement these concepts using NumPy and Python.

