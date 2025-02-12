---
title: Topological Ordering and Properties of Directed Acyclic Graphs
category: Algorithms
tags: graph theory, topological sorting, directed acyclic graphs, proofs
description: A technical exploration of Directed Acyclic Graphs (DAGs) focusing on their topological ordering properties and fundamental lemmas. The document includes mathematical proofs of key DAG properties and presents a Python implementation of the topological sorting algorithm.
---

# Directed Acyclic Graphs (DAGs)

DAGs are pretty self explanatory, but their use cases are vast.

## Topological Orderings

A **topological ordering** of a directed graph $G = (V, E)$ is a linear ordering of all its vertices such that for every directed edge $(v_i, v_j) \in E$, $v_i$ comes before $v_j$ in the ordering if $v_i < v_j$.

**Lemma**: If $G$ has a topological ordering, then $G$ is a DAG.
**Proof**: For contradiction, assume $G$ has a cycle $v_0, \ldots , v_k$, as well as a topological ordering.

We can order vertices $u_1, \ldots, u_n$ such that $\forall \text{ directed edges } i \to j$, we have $i < j$.

Take the smallest $u_i = v_j$ in the cycle mentioned previously. Then $v_{j - 1} \to v_{j}$ and $v_{j} \to v_{j + 1}$ violate our ordering, since $v_j$ was the minimum in the topological ordering (so both $v_{(j - 1) \mod k}$ and $v_{(j + 1) \mod k}$ are greater).

**Lemma**: If $G$ is a DAG, then $G$ has a source vertex ($indeg(v) = 0$).
**Proof**: Suppose for contradiction that $G$ has no source vertex.

i.e., $\forall v \in V, \, indeg(v) \ge 1$

Consider an arbitrary vertex $v_1$. Then $v_1$ has some neighbor(s) $v_2, \ldots$ with an edge into it. Similarly, $v_2$ has some neighbor(s) $v_i, \ldots$ with edges coming into it. You can continue this logic, and must eventually find a repeating vertex, since there are finitely many vertices.

### Algorithm

```python
def topological_sort(G):
  order = []
  count = [0] * len(G)
  S = { v for v in G if not G[v] }
  for v in G
    for u in G[v]:
      count[u] += 1

  while S:
    v = S.pop()
    order.append(v)

    for u in G[v]:
      count[u] -= 1
      if count[u] == 0:
        S.add(u)

  return order
```
