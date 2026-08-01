---
title: Dynamo
description: Notes on the Dynamo paper.
category: Distributed Systems
tags:
  - distributed-systems
  - storage
date: 2025-10-01
sources:
  - "https://example.com/dynamo.pdf"
---

# Dynamo

Dynamo trades consistency for availability. Read the
[[systems/consistency#comparison|consistency comparison]] first.

An unresolved reference: [[systems/vector-clocks]] has not been written yet.

External links like [the paper](https://example.com/dynamo.pdf) and images
like ![ring topology](../images/ring.png) are not internal relationships.

1. Coordinator receives a put.
2. It writes locally and replicates to N - 1 peers.
   Hinted handoff covers failures.
3. Reads reconcile with **vector clocks**.
