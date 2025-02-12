---
title: Developing FPGA Designs with Quartus and ModelSim
category: hardware
tags: Quartus, ModelSim, Verilog, testing process, modular design
description: Describes a structured approach to testing and verifying digital circuits using Quartus and ModelSim.
---


- Make a copy of a previous lab directory to build off of what you already have (Quartus project file, ModelSim files) while keeping the old design as a reference.
- For each module you need to write:
  - Create and populate two new files, one for the module definition and one for that module's test bench.
  - Set the new module file as the top-level module in Quartus.
  - Run Analysis and Synthesis and fix any errors it finds.
  - Edit runlab.do to include the new module and run its test bench and yet-to-be created simulation view.
  - Start ModelSim and perform "do runlab.do." Fix any errors the compiler finds.
  - When it complains about a missing *_wave.do file, set up the Wave pane by drag-and dropping signals from the Object pane. Save the waveform setup using File -> "Save Formatting", then perform "do runlab.do" again.
  - Check the simulation results, correct errors, and iterate until the module works as intended.This process has two major features: First, it has you test every module before you work on the larger  modules that call this unit. This will significantly simplify the design process. Second, you have a separate *_wave.do file for each Verilog file. This keeps a formatted test window for each module, which can help when you discover a fresh bug in a larger design later on. You can always go back and test a submodule by simply editing the runlab.do file to point to the testbench and *_wave.do file for the unit you want to test
