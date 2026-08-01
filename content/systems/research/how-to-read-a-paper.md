---
title: How to Read a Paper
aliases:
  - systems-research/how-to-read-a-paper
category: Systems Research
tags:
  - meta
  - research
  - paper
  - review
date: 2025-01-06
updated: 2026-07-30
status: evergreen
description: Summary of Keshav's three-pass method for reading research papers, with what each pass covers and what you should be able to answer afterward.
sources:
  - title: How to Read a Paper (Keshav)
    url: https://web.stanford.edu/class/cs114/reading-keshav.pdf
    type: paper
---

## Purpose

Summary of [Keshav's "How to Read a Paper"](https://web.stanford.edu/class/cs114/reading-keshav.pdf). I keep this next to my paper reviews as the method behind them.

## Problem

Researchers spend hundreds of hours reading papers every year, so they ought to know how to do it effectively. Keshav argues that reading a paper is a learnable skill, and one that school never teaches.

## The three-pass approach

Each pass ends with a decision about whether the paper deserves the next one:

```mermaid
flowchart TD
    P1[First pass, 5 to 10 minutes, title, abstract, intro, conclusion, headers]
    P1 --> D1{Worth a second pass?}
    D1 -->|no| OUT[Set the paper aside]
    D1 -->|yes| P2[Second pass, about an hour, full read, skip proofs, annotate]
    P2 --> D2{Can you summarize it to a peer?}
    D2 -->|not yet| RE[Set it aside, chase references, or push on]
    D2 -->|yes, and depth is needed| P3[Third pass, 1 to 5 hours, virtually re-implement the paper]
    style P1 fill:#e3f2fd,stroke:#1565c0
    style P2 fill:#e3f2fd,stroke:#1565c0
    style P3 fill:#e8f5e9,stroke:#2e7d32
```

### First pass

Gives you a general idea of what the paper is about. Read the title, abstract, introduction, and conclusion. Only read section and sub-section headers. Also glance over the references and note which you've read. This should only take 5-10 minutes.

After the first pass, you should be able to answer the five Cs:

- *Category*: What type of paper is this? (e.g. measurement, analysis)
- *Context*: Which other papers is it related to? What is the theoretical background?
- *Correctness*: Do the assumptions appear to be valid?
- *Contributions*: What are the paper's main contributions?
- *Clarity*: Is the paper well written?

### Second pass

Grasp the content of the paper, but not necessarily the details. Read the whole thing, but ignore things like proofs. It helps to annotate and take notes during this pass. Pay special attention to diagrams, and mark relevant unread references. This should take about an hour.

After this pass, you should be able to summarize the paper in a few sentences to a peer. If you still don't understand, you can do one of three things:

- Set the paper aside and hope
- Come back to the paper later after looking up references you didn't understand
- Continue to the third pass anyways 😢

### Third pass

Understand the paper in depth. You should *virtually re-implement* the paper, following all reasoning and challenging every assumption. Also try to think about how you would have presented the information differently, and note potential follow-up work as you go. This takes up to 5 hours, and at least 1 hour for a well-written paper and a well-read reader.

After this pass, you should be able to reconstruct the paper's structure from memory, critique it, and pinpoint implicit assumptions, limitations, and potential improvements.

## Sources

- [How to Read a Paper](https://web.stanford.edu/class/cs114/reading-keshav.pdf)

## Related notes

- [[systems/research/paper-review-template|Paper Review Template]]
- [[systems/research/strong-inference|Strong Inference]]
