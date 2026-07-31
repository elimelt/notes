---
title: Topological Ordering and Properties of Directed Acyclic Graphs
category: Algorithms
tags:
  - graph theory
  - topological sorting
  - directed acyclic graphs
  - proofs
date: 2024-04-14
updated: 2026-07-30
status: evergreen
description: Proves the equivalence between DAGs and topological orderings, shows every DAG has a source vertex, and gives Kahn's algorithm for computing a topological order.
---

## Purpose

A directed acyclic graph (DAG) is a directed graph with no cycles. DAGs model any dependency structure where work must happen in a legal order: build systems, course prerequisites, and the subproblem structure of [[algorithms/dynamic-programming|dynamic programming]]. This note proves the basic facts about topological orderings and gives the standard algorithm for computing one.

## Topological Orderings

A **topological ordering** of a directed graph $G = (V, E)$ is a linear ordering $u_1, u_2, \ldots, u_n$ of its vertices such that for every directed edge $(u_i, u_j) \in E$, we have $i < j$. Every edge points forward in the ordering.

**Lemma**: If $G$ has a topological ordering, then $G$ is a DAG.

**Proof**: For contradiction, assume $G$ has a topological ordering and also a cycle $v_0, v_1, \ldots, v_k, v_0$. Let $v_j$ be the vertex of the cycle that appears earliest in the topological ordering. The cycle contains an edge into $v_j$ from its predecessor on the cycle, and that predecessor appears later in the ordering than $v_j$ by choice of $v_j$. That edge points backward, contradicting the definition of a topological ordering. $\blacksquare$

**Lemma**: If $G$ is a DAG, then $G$ has a source vertex, i.e. a vertex with $indeg(v) = 0$.

**Proof**: Suppose for contradiction that every vertex has $indeg(v) \ge 1$. Start at an arbitrary vertex $v_1$ and repeatedly step backward along some incoming edge. Every vertex has an incoming edge, so this walk never gets stuck. The graph has finitely many vertices, so the walk must eventually revisit a vertex, and the segment between the two visits is a cycle. This contradicts $G$ being acyclic. $\blacksquare$

**Lemma**: If $G$ is a DAG, then $G$ has a topological ordering.

**Proof**: Induct on the number of vertices. A single vertex is trivially ordered. For $n$ vertices, take a source $v$ (one exists by the previous lemma), and place it first. Deleting $v$ leaves a DAG on $n - 1$ vertices, which by the inductive hypothesis has a topological ordering. Appending that ordering after $v$ orders all of $G$: edges out of $v$ point forward because $v$ is first, and $v$ has no incoming edges. $\blacksquare$

## Algorithm

The proof above is the algorithm, known as Kahn's algorithm: repeatedly remove a source and append it to the order. Track indegrees so that finding new sources is cheap. Each vertex and edge is processed once, so the runtime is $O(|V| + |E|)$.

```python
def topological_sort(G):
    indegree = {v: 0 for v in G}
    for v in G:
        for u in G[v]:
            indegree[u] += 1

    S = {v for v in G if indegree[v] == 0}
    order = []

    while S:
        v = S.pop()
        order.append(v)
        for u in G[v]:
            indegree[u] -= 1
            if indegree[u] == 0:
                S.add(u)

    return order
```

If the loop ends before all vertices are ordered, the remaining vertices all have positive indegree, which means the graph contains a cycle. That makes this algorithm a cycle detector too.

## Related notes

- [[algorithms/DFS|depth-first search]]
- [[algorithms/dynamic-programming|dynamic programming]]
- [[algorithms/graphs-intro|graph fundamentals]]
