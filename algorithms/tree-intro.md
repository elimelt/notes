---
title: Tree Properties and Proof of Edge Count
category: Graph Theory
tags:
  - Trees
  - Acyclic Graphs
  - Connected Graphs
  - Induction Proofs
  - Graph Properties
description: This document explores the fundamental properties of trees in graph theory. It provides a proof by induction that a tree with n vertices has n-1 edges and outlines three key properties of trees, demonstrating their interconnected nature.
---

# Trees

### Lemma: acyclic and connected

A graph is a tree if and only if it is acyclic and connected.

## Claim: Every tree with $n$ vertices has $n - 1$ edges.

Proof by induction.

Base case: $n = 1$. A tree with 1 vertex has 0 edges.

IH: Suppose every tree with $n - 1$ vertices has $n - 2$ edges ($P(n - 1)$).

IS: Let $T$ be a tree with $n$ vertices.

$T$ must have a vertex of degree 1 (since it is by definition acyclic). Remove this vertex and its edge to get a tree $T'$ with $n - 1$ vertices. By IH, $T'$ has $n - 2$ edges. Adding back the vertex and edge, we get $n - 1$ edges.

## Properties of Trees

Any graph $G$ that satisfies two of the following properties must satisfy the third (and thus be a tree):

- $G$ is connected
- $G$ is acyclic
- $G$ has $|V| - 1$ edges