---
title: Multinomial Logistic Regression
category: Natural Language Processing
tags: classification, multinomial logistic regression, machine learning
description: Explanation of multinomial logistic regression, a classification algorithm used in natural language processing.
---

# Multinomial Logistic Regression

## Classification

Input can be anything (document, image, etc.) and output is a class label from the finite set $\mathcal{L}$.

$$
classify : \mathcal{V}* \rightarrow \mathcal{L}
$$

$\mathcal{V}$ is the set of words in our vocabulary.

$X$ is a random variable representing the input, in a given instance taking values from $\mathcal{V}*$.

$Y$ is a random variable representing the output, taking values from $\mathcal{L}$.

$p(X, Y)$ is the "true" distribution of labeled texts. $p(Y)$ is the distribution of labels. We don't normally know this without looking at the data.
