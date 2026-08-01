---
title: Consistency Models
category: Distributed Systems
tags: distributed-systems, consistency, replication
date: 2025-11-02
aliases:
  - linearizability-notes
  - consistency-cheatsheet
---

## Overview

Linearizability is the strongest single-object consistency model. See
[[systems/dynamo|Dynamo]] for a system that chooses availability instead,
or compare with [the Dynamo notes](dynamo.md) directly.

> Strong consistency is a spectrum, not a switch.

```python
# links in code fences are not relationships
graph = {"read": "[[systems/quorum-code-only]]"}
print(graph["read"])
```

The quorum condition is

$$
R + W > N
$$

where $R$ and $W$ are read and write quorum sizes.

### Comparison

| Model | Ordering |
| ----- | -------- |
| Linearizable | real-time |
| Sequential | program order |
