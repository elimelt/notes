---
title: Sliding Window Pattern
category: algorithms
tags: sliding window, fixed size window, dynamic size window, streaming algorithms, array problems, contiguous subarray, linear data structure
description: A technical exploration of the sliding window pattern in algorithms, focusing on its applications and variations.
---

# Sliding Window

Sliding window is a useful pattern when you need to maintain a contiguous subarray of elements within a linear data structure. Problems typically fall into one of two categories:

1. **Fixed Size Window**: The window size is fixed and does not change as you iterate through the data structure. These are typically easier to solve.
2. **Variable Size Window**: The window size changes as you iterate through the data structure. These are typically harder to solve, since you need to dynamically adjust the window size depending on the state of your algorithm.

## Fixed Size Window

Any time you are given a linear data structure and are asked to find some minimal or maximal contiguous subset of elements, you should immediately think of using a fixed size sliding window.

A typical algorithm might look like this:

- Initialize the window state with the first $k$ elements.
- Iterate through the array, from index $k$ to $n - 1$.
  - At each step, update the window state by removing the first element of your current window and adding the next element.
  - (Sometimes conditionally) update the result based on the window state.
  - Move the window boundries to the right by one element.
- Return result based on the window state.

To design such an algorithm, you need to identify the following:
- What state do you need to describe a window of elements?
  - For example: the sum of elements: integer, the frequency of elements: `dict`, the maximum element: monotonic stack, etc.
- How do you update the window state as add and remove elements?
  - This can be as simple as adding/subtracting, and as complex as iterating through an auxiliary data structure or solving an entire subproblem based on the window state.
- How and when do you update the result based on the window state?
  - For minimum/maximum problems, often your state is `Comparable`, so you can easily update the result by comparing the current state with the result.

Some problems will require you to `map` (as in apply a function to each element of a collection) over all windows of a fixed size, outputting some linear data structe of results based on each iteration's window state. In this case, you can use the same algorithm, but instead of updating a single result, you can append the result of each iteration to a `list`. In others, you can update a single result in more of a "streaming" fashion. You should always look for the streaming approach if your final result only depends on a single window state.

## Dynamic Size Window

Dynamic size windows often involve more complicated logic within each iteration, since at any given step you need to decide whether to expand or contract the window, on top of how to update the window state for each case.

A typical algorithm might look like this:
- 


## Practice Problems

- [minimum-size-subarray-sum](https://leetcode.com/problems/minimum-size-subarray-sum/)
- [longest-substring-without-repeating-characters](https://leetcode.com/problems/longest-substring-without-repeating-characters)
- [substring-with-concatenation-of-all-words](https://leetcode.com/problems/substring-with-concatenation-of-all-words)
- [minimum-window-substring](https://leetcode.com/problems/minimum-window-substring)

