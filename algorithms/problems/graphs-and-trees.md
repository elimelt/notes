---
title: Graphs and Trees
category: algorithms
tags: graphs, trees, induction, proof by contradiction, cycle detection
description: A technical exploration of graphs and trees focusing on the properties and proofs of these fundamental data structures.
---

# Graphs and Trees

## Problem 1
Let $G$ be a tree. Use induction to prove that the number of leaves of $G$ is at least the number of vertices of degree at least $3$ in $G$.

#### Solution

$P(n)$: The number of leaves of any graph $G$ with $n$ vertices is at least the number of vertices of degree at least $3$ in $G$.

#### Base Case: $P(1)$

A tree with one vertex has no leaves or vertices of degree at least $3$, so the base case holds.

#### IH: Assume $P(k)$ holds for some $k \ge 1$.

#### IS: We want to show that $P(k + 1)$ holds.

Let $G = (V, E)$ be a tree with $|V| = k + 1$.

Choose some arbitrary leaf $l \in V$, and $(l, p) \in E$. Removing $l$ (and its corresponding edge) from $G$ results in a tree $G' = (V', E')$ with $|V'| = k$. By the IH, $G'$ satisfies $P(k)$.

**Case 1**: $p$ has degree $1$ in $G'$.

Then $p$ is a leaf in $G'$, and $G'$ has the same number of leaves and vertices with degree 3 as $G$ (since we didn't remove any vertices of degree 3). Thus, $G$ has at least as many leaves as vertices of degree 3.

**Case 2**: $p$ has degree $2$ in $G'$.

Then $p$ is not a leaf in $G'$, and $G'$ has one fewer leaf than $G$ (since we removed a leaf). However, we also removed a vertex of degree 3 from $G$, so the number of vertices of degree 3 in $G$ is still at least the number of leaves in $G$ (both increased by 1 from $G' \to G$).

**Case 3**: $p$ has degree at least $3$ in $G'$.

Then $p$ is a vertex of degree at least $3$ in $G$, and $G$ has the same number of vertices of degree greater than or equal to $3$ as $G'$. Since we only add a leaf to $G'$ to get $G$, the number of leaves in $G$ is at least the number of leaves in $G'$, which is at least the number of vertices of degree at least $3$ in $G'$.

In all cases, $G$ has at least as many leaves as vertices of degree at least $3$, so $P(k + 1)$ holds.

## Problem 2

Let $G$ be a graph with $n$ vertices and at least $n$ edges. Show that $G$ has a cycle.

#### Solution

Let $G$ be a graph with $n$ vertices and at least $n$ edges. Suppose for the sake of contradiction that $G$ has no cycles.

Since $G$ has no cycles, it is a tree.

Claim: The sum of the degrees of all vertices in a graph is equal to twice the number of edges.

Proof: Each edge contributes $1$ to the degree of two vertices, so the sum of the degrees of all vertices is twice the number of edges.


