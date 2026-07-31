---
title: Developing FPGA Designs with Quartus and ModelSim
category: Hardware
tags:
  - Quartus
  - ModelSim
  - Verilog
  - testing process
  - modular design
date: 2024-02-25
updated: 2026-07-30
status: evergreen
description: A module-by-module workflow for building and simulating FPGA designs in Quartus and ModelSim, and why testing each unit before integration pays off.
sources:
  - title: UW CSE 369 lab material
    type: lecture
---

## Purpose

This is the loop I use for FPGA labs in Quartus and ModelSim. The point is to verify every module in simulation before wiring it into anything larger.

## Setup

Make a copy of a previous lab directory and build from it. You keep the Quartus project file and the ModelSim files, and the old design stays around as a reference.

## Per-module loop

For each module you need to write:

1. Create and populate two new files, one for the module definition and one for that module's test bench.
2. Set the new module file as the top-level module in Quartus.
3. Run Analysis and Synthesis and fix any errors it finds.
4. Edit `runlab.do` to include the new module, its test bench, and its yet-to-be-created simulation view.
5. Start ModelSim and perform `do runlab.do`. Fix any errors the compiler finds.
6. When ModelSim complains about a missing `*_wave.do` file, set up the Wave pane by drag-and-dropping signals from the Object pane. Save the waveform setup with File -> "Save Formatting", then perform `do runlab.do` again.
7. Check the simulation results, correct errors, and iterate until the module works as intended.

## Why the loop works

Testing every module before you work on the larger modules that call it makes debugging much simpler, since a bug in a big design is unlikely to live in a unit you already verified. Keeping a separate `*_wave.do` file per Verilog file means each module keeps its own formatted wave window. When a fresh bug shows up in a larger design later, you can go back and re-test a submodule by pointing `runlab.do` at that unit's test bench and `*_wave.do` file.

## Related

- [[hardware-design/369/system-verilog|SystemVerilog]]
- [[hardware-design/369/waveform-diagram|Waveform Diagrams]]
