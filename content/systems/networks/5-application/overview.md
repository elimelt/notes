---
title: Application Layer Overview
aliases:
  - networks/5-application/overview
category: Networks
tags:
  - application-layer
  - TCP
  - UDP
  - reliability
date: 2024-03-04
updated: 2026-07-30
status: draft
description: How applications choose between TCP and UDP as the substrate for application-layer protocols.
sources:
  - title: "CSE 461: Computer Networks, University of Washington"
    url: https://courses.cs.washington.edu/courses/cse461/
    type: lecture
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Frame the transport choice that every application-layer protocol makes before the notes on individual protocols.

## Core idea

Applications built on [[systems/networks/4-transport/TCP|TCP]] can transfer arbitrary-length data and get reliability and flow control for free. Some applications do not need those guarantees, and some actively cannot afford them. Internet telephony and online games run on [[systems/networks/4-transport/UDP|UDP]] because a retransmitted packet arrives too late to be useful, and the delays TCP introduces waiting for in-order delivery hurt more than the losses do. The protocol notes in this section, [[systems/networks/5-application/HTTP|HTTP]] and [[systems/networks/5-application/DNS|DNS]], show one of each. HTTP rides on TCP because pages must arrive intact, while DNS rides on UDP because a lookup is one small message and a retry is cheap.

## Related notes

- [[systems/networks/5-application/HTTP|HTTP]]
- [[systems/networks/5-application/DNS|DNS]]
- [[systems/networks/5-application/CDNs|content delivery networks]]
- [[systems/networks/4-transport/transport-overview|transport layer overview]]
