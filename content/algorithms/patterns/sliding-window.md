---
title: Sliding Window Pattern
category: Algorithms
tags:
  - sliding-window
  - two-pointers
  - arrays
  - streaming-algorithms
date: 2024-03-31
updated: 2026-07-30
status: draft
description: How to recognize sliding window problems and design both fixed and variable size window algorithms over linear data structures.
---

## Purpose

Sliding window is the pattern to reach for when you need to maintain a contiguous subarray of elements within a linear data structure. This note covers how to recognize these problems and how to structure the two variants.

## Core idea

Problems typically fall into one of two categories:

1. **Fixed size window**: the window size never changes as you iterate. These are typically easier to solve.
2. **Variable size window**: the window grows and shrinks as you iterate, depending on the state of your algorithm. These are harder, since you have to decide when to expand and when to contract.

## Fixed size window

Any time you're given a linear data structure and asked for a minimal or maximal contiguous subset of elements with a known size, think fixed size sliding window.

A typical algorithm:

- Initialize the window state with the first $k$ elements.
- Iterate through the array from index $k$ to $n - 1$.
  - At each step, update the window state by removing the element leaving the window and adding the next element.
  - Update the result based on the window state, sometimes conditionally.
- Return the result.

To design such an algorithm, work out:

- What state describes a window of elements? A sum fits in an integer, element frequencies fit in a `dict`, a running maximum needs a monotonic deque.
- How does the state change when an element enters or leaves the window? This can be as simple as adding and subtracting, or as involved as solving an entire subproblem on the window state.
- How and when does the window state update the result? For minimum and maximum problems the state is often directly comparable against the result.

Some problems ask you to apply a function to every window of a fixed size and output a list of per-window results. The same algorithm works, appending each iteration's result to a list. If the final answer only depends on aggregating window states, update a single result in streaming fashion instead. Always look for the streaming version when the output is a single value.

## Variable size window

Variable size windows involve more logic per iteration, since at each step you decide whether to expand or contract the window, on top of updating the window state in each case.

A typical algorithm:

- Start with two pointers $l = r = 0$ and an empty window state.
- Advance $r$ one element at a time, adding $A[r]$ to the window state.
- After each expansion, shrink from the left while the window violates the problem's constraint, removing $A[l]$ from the state and incrementing $l$.
- Update the result whenever the window is valid. For longest-window problems that's after the shrink loop restores validity. For shortest-window problems, shrink while the window stays valid and record the size before it breaks.

The nested loop looks quadratic. Both pointers only move forward though, so each element enters and leaves the window at most once, and the whole pass costs $O(n)$ state updates.

## Practice problems

- [minimum-size-subarray-sum](https://leetcode.com/problems/minimum-size-subarray-sum/)
- [longest-substring-without-repeating-characters](https://leetcode.com/problems/longest-substring-without-repeating-characters)
- [substring-with-concatenation-of-all-words](https://leetcode.com/problems/substring-with-concatenation-of-all-words)
- [minimum-window-substring](https://leetcode.com/problems/minimum-window-substring)

## Related notes

- [[algorithms/patterns/BFS|Breadth First Search Pattern]]
