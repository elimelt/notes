---
title: End-to-End Arguments in System Design
category: System Design
tags:
  - system-design
  - end-to-end
  - design
  - networking
  - paper-notes
date: 2025-01-14
updated: 2026-07-30
status: draft
description: Review notes on Saltzer, Reed, and Clark's end-to-end argument, which says functions like reliability belong at the endpoints and lower-level implementations are only performance optimizations.
sources:
  - title: End-to-End Arguments in System Design (1984)
    url: https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf
    type: paper
---

## Purpose

Short reading notes on the end-to-end argument. The note states the argument, why it holds, and the cases where it breaks down.

## Citation

- [End-to-End Arguments in System Design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf), Saltzer, Reed, and Clark.

## Problem

Where should a function like error checking, encryption, or delivery acknowledgment live in a layered system? The temptation is to push it into the lower layers so every application gets it for free. The paper argues that placement is usually wrong.

## Main idea

A function can only be implemented completely and correctly with the knowledge and help of the application at the endpoints. The paper's running example is careful file transfer: even if the network guarantees reliable delivery, the transfer application still has to check the file end to end, because the file can be corrupted on disk, in memory, or in the file system before it ever reaches the network. Since the endpoint check has to exist anyway, a lower-level implementation of the same function is redundant for correctness. It can only be justified as a performance optimization.

The same reasoning covers crash detection, message sequencing, and duplicate suppression. Only the endpoints know what the application actually needs, so a correct communication system gets built from endpoint checks, whatever the layers below do.

## When the argument cuts the other way

If the probability of an error inside the network is low, adding checks in the middle buys little and costs every user of the layer. But the argument is a guideline, and it has real limits:

- Systems that communicate over lossy media should have intermediate checks, because retransmitting a whole transfer from the endpoints costs far more than fixing errors hop by hop.
- Catching errors only at the endpoints delays detection. A corrupted message has to travel the whole path before anyone notices.
- Leaving checks out of the middle hurts maintainability, since failures surface far from where they happen.

## Sources

- [End-to-End Arguments in System Design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf)

## Related notes

- [[systems-research/internet-design-philosophy|Design Philosophy of DARPA Internet Protocols]]
- [[systems-research/hints-for-computer-system-design|Hints for Computer System Design]]
