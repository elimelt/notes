---
title: "C-SWAP: Cost, Size, Weight and Power"
aliases:
  - signal-conditioning/lecture-notes/lecture-1
category: Signal Conditioning
tags:
  - c-swap
  - embedded systems
  - power
  - hardware
  - energy constraints
  - heat dissipation
date: 2024-01-03
updated: 2026-07-30
status: draft
description: Lecture 1 notes on the C-SWAP constraints (cost, size, weight, power) that shape embedded hardware design, and where device power actually goes.
sources:
  - title: Signal conditioning course, lecture 1
    type: lecture
---

## Purpose

Lecture 1 framed hardware design around C-SWAP, short for cost, size, weight, and power. This note records that framing.

## The constraints

Cost mostly comes down to whether the device is consumable or reusable, since a consumable has to be cheap enough to throw away.

Size and weight are in many cases driven by power, because batteries tie stored energy to mass and volume.

Power decides how long the device runs between charges, and it also sets the thermal budget, since everything the device draws it eventually dissipates as heat. The lecture's rule of thumb was that 10 mW/cm^3 of dissipation raises device temperature about 2 degrees C.

Power draw comes from three key sources: sensing, computing, and communication. Knowing which one dominates tells you where to optimize.

## Related

- [[hardware/signal-conditioning/lecture-notes/lecture-2|Electricity]]
- [[systems/research/data-center-power-provisioning|Power Provisioning for a Warehouse-sized Computer]]
