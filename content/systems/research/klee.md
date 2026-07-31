---
title: Klee Paper Review
aliases:
  - systems-research/klee
category: Systems Research
tags:
  - klee
  - symbolic-execution
  - testing
  - verification
  - systems
  - software-engineering
  - correctness
  - program-analysis
date: 2025-01-06
updated: 2026-07-30
status: evergreen
description: Review notes on KLEE, a symbolic execution engine that generates high-coverage tests for systems programs, with its coverage results on Core Utils and Busybox.
sources:
  - title: "KLEE: Unassisted and Automatic Generation of High-Coverage Tests for Complex Systems Programs (OSDI 2008)"
    url: https://llvm.org/pubs/2008-12-OSDI-KLEE.pdf
    type: paper
  - title: KLEE source code and docs
    url: https://klee.github.io/
    type: docs
  - title: "Execution Synthesis (ESD), a follow-up direction"
    url: https://dl.acm.org/doi/pdf/10.1145/1755913.1755946
    type: paper
---

## Purpose

Reading notes on KLEE. The note covers how symbolic execution gets KLEE past the limits of random testing, the engineering that makes it practical, and the coverage numbers from the paper.

## Citation

- [KLEE: Unassisted and Automatic Generation of High-Coverage Tests for Complex Systems Programs](https://llvm.org/pubs/2008-12-OSDI-KLEE.pdf), Cadar, Dunbar, and Engler, OSDI 2008. [Source code](https://klee.github.io/).

## Problem

Testing large and complex programs is difficult. Writing manual tests is extremely time consuming and still misses edge cases. Automated random testing reaches limited coverage because randomization has no semantic understanding of the branches it needs to hit. Other symbolic execution tools existed, but many could not handle environmental dependencies like file I/O, network I/O, and system calls, which contribute a huge share of a systems program's state space.

## Main idea

KLEE runs a program on symbolic inputs and maintains a set of constraints describing every operation performed on those inputs down each path. At each branch it forks the execution state and adds the branch condition (or its negation) to each side's constraints. Solving the constraints for a path yields a concrete test case that drives the real program down that exact path. The same machinery finds bugs, by checking whether any path reaches an error state, and checks functional equivalence, by comparing the constraints two programs generate on the same symbolic input.

## Mechanism

Two design details carry most of the weight:

- KLEE keeps program execution state inside the engine itself, so forking at a branch never reruns the prefix of the path. Object-level copy-on-write semantics keep the cost of holding thousands of forked states low, and backtracking stays cheap.
- Environmental dependencies are handled with models. You give KLEE a model of the file system or network, and the program's interactions with the environment execute symbolically, the same way mocks stand in for dependencies in unit testing.

KLEE also spends real effort simplifying and caching constraint queries before they hit the solver, since solver time dominates everything.

## Evidence

Results reported in the paper:

- GNU Core Utils: 84.5% overall line coverage, against 67.7% for the developers' test suite
- Busybox: 90.5% overall line coverage, against 44.8% for the developers' test suite
- 100% line coverage on 16 Core Utils tools and 31 Busybox tools
- 56 serious bugs found across all tested applications
- Cross-checking equivalent Busybox and Core Utils utilities surfaced inconsistencies, some of which were bugs

Beyond the raw coverage, the semantic approach needed far fewer test cases than random testing to reach the same coverage.

## Assumptions and limits

State space explosion remains the limiting factor in practice, even with KLEE's optimizations. Support for some language features is limited, floating point and dynamic memory allocation among them. And getting a large system compiled to LLVM bitcode is its own project (`wllvm` helps).

## Open questions

- Can symbolic execution handle non-deterministic programs? Would the theoretical bounds on randomized algorithms be semantically understood by KLEE?
- Is symbolic execution possible at a lower level, like the instruction set, or do the semantics stop being interpretable there? If it works, a language-agnostic engine falls out.
- Can the same constraint techniques simplify program logic by detecting redundant constraints?

## Sources

- [KLEE: Unassisted and Automatic Generation of High-Coverage Tests for Complex Systems Programs](https://llvm.org/pubs/2008-12-OSDI-KLEE.pdf)
- [KLEE source code](https://klee.github.io/)
- [ESD synthesis follow-up](https://dl.acm.org/doi/pdf/10.1145/1755913.1755946)

## Related notes

- [[systems/research/paper-review-template|Paper Review Template]]
