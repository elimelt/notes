# Inline link proposals

- Run: `inline-learned`
- Corpus: `sha256:1e78346f593363cdc686623ede1407775b1d1081f200f8c52394700e51aadba8`
- Generated: 2026-08-01T22:16:08+00:00
- Accepted: 244 across 151 source note(s)
- Abstained: 20981

## Breadth First Search Algorithm Implementation and Analysis (`algorithms/BFS`)

- **runtime analysis** -> Breadth First Search Pattern (`algorithms/patterns/BFS`)
  - scores: naturalness 0.837 · target 1.000 · placement 0.899 · combined 0.920
  - span: [678, 694)
  - context: ...of their distance from the starting vertex. This note gives the algorithm, its **runtime analysis** , and proofs of the two structural facts that make BFS useful: adjacent vertices...

## Depth First Search Algorithm and Tree Properties (`algorithms/DFS`)

- **BFS** -> Breadth First Search Pattern (`algorithms/patterns/BFS`)
  - scores: naturalness 0.236 · target 1.000 · placement 0.764 · combined 0.572
  - span: [3587, 3590)
  - context: ...so it finds \[\[algorithms/connected-components\|connected components\]\] just like **BFS** does. The ancestor property is what sets DFS apart. Since every non-tree edge...

## Approximation Algorithms (`algorithms/approximation-algorithms`)

- **NP-complete** -> Dynamic Programming Algorithms and Problem Solutions Guide (`algorithms/dynamic-programming`)
  - scores: naturalness 0.220 · target 1.000 · placement 0.985 · combined 0.587
  - span: [399, 410)
  - context: ...he greedy ln(n) approximation for set cover. --- \#\# Purpose When a problem is **NP-complete** , you give up on computing an exact optimum in polynomial time. This note define...

## Bipartite Graphs Properties, Proofs, and Detection Algorithm (`algorithms/bipartite-graphs`)

- **bipartite graphs** -> Finding Connected Components in Undirected Graphs Using BFS/DFS (`algorithms/connected-components`)
  - scores: naturalness 0.966 · target 1.000 · placement 0.976 · combined 0.983
  - span: [523, 539)
  - context: ...ww.cs.princeton.edu/~wayne/kleinberg-tardos/ --- \#\# Purpose This note defines **bipartite graphs** , proves the characterization in terms of odd cycles, and turns that proof into...

- **An** -> Graph Theory (`reference/cheatsheets/algorithms/graphs`)
  - scores: naturalness 0.362 · target 1.000 · placement 1.000 · combined 0.701
  - span: [709, 711)
  - context: ...ime detection algorithm based on \[\[algorithms/BFS\|BFS\]\] layers. \#\# Definition **An** undirected graph $G = (V, E)$ is bipartite if there exists a partition of $V$ i...

- **BFS** -> Depth First Search Algorithm and Tree Properties (`algorithms/DFS`)
  - scores: naturalness 0.212 · target 1.000 · placement 0.916 · combined 0.571
  - span: [2942, 2945)
  - context: ...$L(x) = L(y)$, and let $z$ be the lowest common ancestor of $x$ and $y$ in the **BFS** tree. The tree paths from $z$ to $x$ and from $z$ to $y$ have the same length,...

## Finding Connected Components in Undirected Graphs Using BFS/DFS (`algorithms/connected-components`)

- **connected components** -> Graph Theory (`reference/cheatsheets/algorithms/graphs`)
  - scores: naturalness 0.985 · target 1.000 · placement 0.963 · combined 0.987
  - span: [589, 609)
  - context: ...\#\# Purpose Given an undirected graph $G = (V, E)$, you can partition $V$ into **connected components** $C\_1, C\_2, \\ldots$ in $O(\|V\| + \|E\|)$ using \[\[algorithms/BFS\|breadth-first searc...

## Divide and Conquer Algorithm Analysis with Implementation Examples (`algorithms/divide-and-conquer`)

- **sub-problems** -> Dynamic Programming Algorithms and Problem Solutions Guide (`algorithms/dynamic-programming`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.135 · target 1.000 · placement 0.977 · combined 0.493
  - span: [536, 548)
  - context: ...lementations. --- \#\# Purpose Divide and conquer reduces a problem to multiple **sub-problems** , solves each recursively, and merges the solutions. In plain \[\[algorithms/induc...

## Dynamic Programming Algorithms and Problem Solutions Guide (`algorithms/dynamic-programming`)

- **Dynamic programming** -> Greedy Algorithms for Interval Scheduling and Partitioning (`algorithms/greedy-algorithms`)
  - scores: naturalness 0.798 · target 1.000 · placement 0.998 · combined 0.924
  - span: [597, 616)
  - context: ...s: - https://www.cs.princeton.edu/~wayne/kleinberg-tardos/ --- \#\# Purpose \*\* **Dynamic programming** \*\* breaks a problem into \*\*overlapping\*\* sub-problems and builds up solutions to...

- **NP-complete** -> Finding Connected Components in Undirected Graphs Using BFS/DFS (`algorithms/connected-components`)
  - scores: naturalness 0.223 · target 1.000 · placement 0.873 · combined 0.576
  - span: [2779, 2790)
  - context: ...ider. Note that this problem is equivalent to maximum independent set, which is **NP-complete** . To differentiate our solution from the general (supposed) unsolvability of thi...

- **BFS-tree** -> Depth First Search Algorithm and Tree Properties (`algorithms/DFS`)
  - scores: naturalness 0.609 · target 1.000 · placement 0.799 · combined 0.804
  - span: [34648, 34656)
  - context: ...vertex $r$ as root, and run $BFS(r)$, returning the level of each vertex in the **BFS-tree** (with \`L\[r\] = 0\`). Define $f(v, k)$ as the number of connected subsets of size...

## Introduction to Undirected Graphs and Their Properties (`algorithms/graphs-intro`)

- **odd-degree** -> Finding Connected Components in Undirected Graphs Using BFS/DFS (`algorithms/connected-components`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.379 · target 1.000 · placement 0.840 · combined 0.688
  - span: [1905, 1915)
  - context: ...re$ \#\#\# Odd Degree Vertices \*\*Claim\*\*: in any undirected graph, the number of **odd-degree** vertices is even. \*\*Proof\*\*: the sum of all degrees is even (it equals $2\|E\|$)...

## Greedy Algorithms for Interval Scheduling and Partitioning (`algorithms/greedy-algorithms`)

- **interval partitioning** -> Interval Scheduling/Partitioning (`reference/cheatsheets/algorithms/intervals`)
  - scores: naturalness 0.294 · target 1.000 · placement 0.845 · combined 0.630
  - span: [725, 746)
  - context: ...correctness carries the weight. This note works through interval scheduling and **interval partitioning** , which between them show the three standard proof techniques: greedy stays ahea...

## Linear Programming Fundamentals and Applications in Optimization (`algorithms/linear-programming`)

- **Linear programming** -> Convexity, Lagrangians, and KKT Conditions (`math/convexity-lagrangians-kkt`)
  - scores: naturalness 0.659 · target 1.000 · placement 1.000 · combined 0.864
  - span: [436, 454)
  - context: ...weighted vertex cover including the rounding 2-approximation. --- \#\# Purpose **Linear programming** optimizes a linear objective subject to linear constraints. A huge number of co...

- **min-cost** -> Network Flow Algorithms and Applications in Graph Theory (`algorithms/network-flows`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.220 · target 1.000 · placement 0.795 · combined 0.562
  - span: [717, 725)
  - context: ...ry, the standard form transformations, and three worked formulations: max-flow, **min-cost** flow, and the LP relaxation of weighted vertex cover. \#\# Linear Systems Syste...

- **NP-hard** -> Finding Connected Components in Undirected Graphs Using BFS/DFS (`algorithms/connected-components`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.120 · target 1.000 · placement 0.939 · combined 0.470
  - span: [6609, 6616)
  - context: ...restriction $x\_v \\in \\\{0, 1\\\}$ this is exactly weighted vertex cover, which is **NP-hard** , so the integer program is not directly solvable in polynomial time. Dropping t...

## Breadth First Search Pattern (`algorithms/patterns/BFS`)

- **Bipartiteness** -> Bipartite Graphs Properties, Proofs, and Detection Algorithm (`algorithms/bipartite-graphs`)
  - scores: naturalness 0.469 · target 1.000 · placement 0.050 · combined 0.421
  - span: [2706, 2719)
  - context: ...omponents\|Connected components\]\], by running BFS from every unvisited vertex. - **Bipartiteness** checks, since an edge between two vertices in the same level implies an odd cyc...

## Problem Set 4 Notes (`algorithms/practice/4`)

- **connected components** -> Finding Connected Components in Undirected Graphs Using BFS/DFS (`algorithms/connected-components`)
  - scores: naturalness 0.744 · target 1.000 · placement 0.897 · combined 0.882
  - span: [6748, 6768)
  - context: ...\_1$. Let $T\_1' = T\_1 - e$. Since $T\_1$ was a tree, this splits $T\_1'$ into two **connected components** $C\_1, C\_2$, both of which are also trees by (2). We have $u \\in C\_1$ and $v \\in...

## Graphs and Trees Problem Notes (`algorithms/problems/graphs-and-trees`)

- **graph theory** -> Graph Theory (`reference/cheatsheets/algorithms/graphs`)
  - scores: naturalness 0.851 · target 1.000 · placement 0.965 · combined 0.938
  - span: [426, 438)
  - context: ...eton.edu/~wayne/kleinberg-tardos/ --- \#\# Purpose Work through a pair of short **graph theory** exercises. The first is a full \[\[algorithms/induction\|inductive proof\]\]. The se...

## Caches, Virtual Memory, and Memory Systems (`hardware/computer-architecture/caches-virtual-memory`)

- **Trace** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.178 · target 0.933 · placement 1.000 · combined 0.529
  - span: [1076, 1081)
  - context: ...b/master/src/main/scala/rocket/NBDcache.scala type: source --- \#\# Purpose **Trace** what happens between \`int x = array\[i\]\` and the value landing in a register: ca...

- **memory-level parallelism** -> Memory-Level Parallelism Benchmarks (`systems/operating-systems/benchmarks/mlp`)
  - scores: naturalness 0.970 · target 1.000 · placement 0.844 · combined 0.956
  - span: [3752, 3776)
  - context: ...ath older misses that haven't returned yet. The MSHR count is a hard ceiling on **memory-level parallelism** (MLP): once every MSHR is occupied, the next miss stalls no matter how many out...

## Experiments and Benchmarking in Computer Architecture (`hardware/computer-architecture/experiments-and-benchmarking`)

- **RTL** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.098 · target 1.000 · placement 0.900 · combined 0.434
  - span: [1092, 1095)
  - context: ...ether the evidence is a wall-clock timer, a hardware performance counter, or an **RTL** simulation waveform, and then applies that schema to this repo's own benchmark...

- **branch misprediction** -> Branch Prediction Benchmarks (`systems/operating-systems/benchmarks/branch`)
  - scores: naturalness 0.918 · target 1.000 · placement 0.963 · combined 0.963
  - span: [6675, 6695)
  - context: ...dates the qualitative conclusions those notes draw (MLP scaling, TLB miss cost, **branch misprediction** penalty) since the relative comparisons hold regardless of the exact CPU model....

## A Working Map of Computer Architecture (`hardware/computer-architecture/index`)

- **SystemVerilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.989 · target 1.000 · placement 0.857 · combined 0.966
  - span: [1542, 1555)
  - context: ...predictors, out-of-order machinery), the microarchitecture is described in RTL ( **SystemVerilog** , Chisel), and RTL becomes gates through synthesis. Measurement runs the other d...

- **Measured** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - scores: naturalness 0.480 · target 0.999 · placement 0.050 · combined 0.425
  - span: [6689, 6697)
  - context: ...\#\# What's measured vs. simulated vs. inferred from source vs. conceptual - \*\* **Measured** on real hardware\*\*: the \[\[systems/operating-systems/benchmarks/branch\|branch\]\],...

## Interconnects, NoCs, DMA, and Memory Controllers (`hardware/computer-architecture/interconnects-noc-dma`)

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 0.891 · target 0.979 · placement 0.050 · combined 0.523
  - span: [12476, 12488)
  - context: ...header routes, before the whole packet has arrived), at the benefit of simpler **flow control** — the trade rocket-chip's arbiter makes by holding the winner for a burst's \`be...

## Instruction Sets, Datapaths, and Control (`hardware/computer-architecture/isa-datapath-control`)

- **SystemVerilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.990 · target 1.000 · placement 0.894 · combined 0.974
  - span: [1277, 1290)
  - context: ...different styles: \[CVA6\](https://github.com/openhwgroup/cva6) as a hand-written **SystemVerilog** single-issue pipeline, \[Rocket\](https://github.com/chipsalliance/rocket-chip) a...

- **Chisel-generated** -> Open-Source CPU RTL Reading Lab (`hardware/computer-architecture/rtl-reading-lab`)
  - scores: naturalness 0.251 · target 1.000 · placement 0.865 · combined 0.599
  - span: [1374, 1390)
  - context: ...gle-issue pipeline, \[Rocket\](https://github.com/chipsalliance/rocket-chip) as a **Chisel-generated** in-order core. Both ground the abstract datapath/control split in real RTL. Thi...

- **register-file** -> Pipelining, Hazards, and Branch Prediction (`hardware/computer-architecture/pipelining-hazards-branch-prediction`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.356 · target 1.000 · placement 0.955 · combined 0.690
  - span: [12637, 12650)
  - context: ...floating point; those are separate extensions (M, F/D) that plug into the same **register-file** and decode structure but add functional units and, in the multiply case, multi-...

## Multiprocessors, Cache Coherence, and Memory Consistency (`hardware/computer-architecture/multiprocessors-cache-coherence`)

- **false sharing** -> False Sharing Benchmarks (`systems/operating-systems/benchmarks/false_sharing`)
  - scores: naturalness 0.861 · target 1.000 · placement 0.755 · combined 0.897
  - span: [11071, 11084)
  - context: ...e-to-cache transfers, which is why the benchmark note recommends it for finding **false sharing** in the wild. \#\# Edge cases and limits - \*\*Coherence says nothing about atomic...

## Out-of-Order and Superscalar Execution (`hardware/computer-architecture/out-of-order-execution`)

- **pipelining
and hazards** -> Pipelining, Hazards, and Branch Prediction (`hardware/computer-architecture/pipelining-hazards-branch-prediction`)
  - scores: naturalness 0.908 · target 1.000 · placement 0.969 · combined 0.961
  - span: [943, 965)
  - context: ...line (see \[\[hardware/computer-architecture/pipelining-hazards-branch-prediction\| **pipelining and hazards** \]\]) issues and completes instructions strictly in program order, so one stalled...

- **memory bandwidth** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - scores: naturalness 0.551 · target 1.000 · placement 0.050 · combined 0.446
  - span: [9704, 9720)
  - context: ...cumulators only buys 1.3x at large array sizes because the bottleneck shifts to **memory bandwidth** , not the ALU/issue width, a case where the out-of-order engine already has en...

- **The MLP benchmark** -> Memory-Level Parallelism Benchmarks (`systems/operating-systems/benchmarks/mlp`)
  - scores: naturalness 0.974 · target 1.000 · placement 0.823 · combined 0.953
  - span: [11108, 11125)
  - context: ...an earlier one still waiting on an operand the way full out-of-order issue can. **The MLP benchmark** 's near-linear scaling up to 8 chains would not appear with only a scoreboard's...

- **branch misprediction** -> Branch Prediction Benchmarks (`systems/operating-systems/benchmarks/branch`)
  - scores: naturalness 0.351 · target 1.000 · placement 0.873 · combined 0.675
  - span: [12710, 12730)
  - context: ...-flush-like recovery, similar in kind to (but usually narrower in scope than) a **branch misprediction** . ROB size caps how far ahead of a stalled instruction the core can look for ind...

## Pipelining, Hazards, and Branch Prediction (`hardware/computer-architecture/pipelining-hazards-branch-prediction`)

- **ISA,
datapath, and control** -> Instruction Sets, Datapaths, and Control (`hardware/computer-architecture/isa-datapath-control`)
  - scores: naturalness 0.737 · target 1.000 · placement 0.803 · combined 0.860
  - span: [1465, 1491)
  - context: ...n cost. It continues from \[\[hardware/computer-architecture/isa-datapath-control\| **ISA, datapath, and control** \]\] and precedes \[\[hardware/computer-architecture/out-of-order-execution\|out-of-o...

- **MEM** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.093 · target 0.987 · placement 0.954 · combined 0.428
  - span: [5617, 5620)
  - context: ...ix is the \*\*load-use hazard\*\*: a load's result isn't available until the end of **MEM** , one stage later than an ALU result at the end of EX. If the very next instruct...

- **BTB** -> TLB and Page Walk Benchmarks (`systems/operating-systems/benchmarks/tlb`)
  - scores: naturalness 0.245 · target 0.999 · placement 0.856 · combined 0.592
  - span: [6686, 6689)
  - context: ...the target address the branch went to last time; if this fetch's PC hits in the **BTB** , the frontend speculatively fetches from the cached target instead of \`PC+4\`. A...

## Open-Source CPU RTL Reading Lab (`hardware/computer-architecture/rtl-reading-lab`)

- **SystemVerilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.986 · target 1.000 · placement 0.970 · combined 0.989
  - span: [2867, 2880)
  - context: ...8075606\` \| Ibex and Rocket both target small in-order cores but differ in HDL ( **SystemVerilog** vs. Chisel). BOOM is explicitly "Berkeley Out-of-Order Machine," built as an Oo...

## Karnaugh Maps (`hardware/digital-design/369/karnaugh-maps`)

- **SystemVerilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.982 · target 1.000 · placement 0.050 · combined 0.546
  - span: [2861, 2874)
  - context: ...@ (\*)\` implicitly includes every signal the block reads. - \`always\_comb\` is the **SystemVerilog** form of \`always @ (\*)\`. It infers the sensitivity list from the signals read in...

- **combinational logic** -> Combinational Logic (`hardware/digital-design/369/combinational-logic`)
  - scores: naturalness 0.949 · target 1.000 · placement 0.050 · combined 0.539
  - span: [2996, 3015)
  - context: ...sitivity list from the signals read in the block and tells the tools you intend **combinational logic** . \#\# Related - \[\[hardware/digital-design/369/combinational-logic\|Combinational...

## Developing FPGA Designs with Quartus and ModelSim (`hardware/digital-design/369/quartus-workflow`)

- **File -\> "Save Formatting** -> C-SWAP: Cost, Size, Weight and Power (`hardware/signal-conditioning/lecture-notes/lecture-1`)
  - scores: naturalness 0.658 · target 0.980 · placement 0.050 · combined 0.470
  - span: [1476, 1500)
  - context: ...by drag-and-dropping signals from the Object pane. Save the waveform setup with **File -\> "Save Formatting** ", then perform \`do runlab.do\` again. 7. Check the simulation results, correct e...

- **Verilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.908 · target 1.000 · placement 0.877 · combined 0.942
  - span: [1881, 1888)
  - context: ...to live in a unit you already verified. Keeping a separate \`\*\_wave.do\` file per **Verilog** file means each module keeps its own formatted wave window. When a fresh bug sh...

## Sequential Logic (SL) (`hardware/digital-design/369/sequential-logic`)

- **Sequential logic** -> Algorithmic State Machines (`hardware/digital-design/371/algorithmic-state-machines`)
  - scores: naturalness 0.592 · target 1.000 · placement 1.000 · combined 0.832
  - span: [885, 901)
  - context: ...this note covers the flip-flop that stores it and the timing rules it imposes. **Sequential logic** controls the flow of information through blocks of combinational logic, usually...

## SystemVerilog (`hardware/digital-design/369/system-verilog`)

- **SystemVerilog** -> Algorithmic State Machines (`hardware/digital-design/371/algorithmic-state-machines`)
  - scores: naturalness 0.995 · target 1.000 · placement 0.970 · combined 0.992
  - span: [549, 562)
  - context: ...W CSE 369 lecture notes type: lecture --- \#\# Purpose Working notes on the **SystemVerilog** primitives and the structural style used in CSE 369. The examples build the sam...

- **Verilog** -> Combinational Logic (`hardware/digital-design/369/combinational-logic`)
  - scores: naturalness 0.639 · target 1.000 · placement 1.000 · combined 0.855
  - span: [727, 734)
  - context: ...-OR-INVERT circuit three ways, then compose it into a mux. \#\# What Verilog is **Verilog** is a language for describing hardware. You describe the behavior you want progr...

- **Verilog** -> Sequential Logic (SL) (`hardware/digital-design/369/sequential-logic`)
  - scores: naturalness 0.924 · target 1.000 · placement 0.784 · combined 0.927
  - span: [1015, 1022)
  - context: ...but the execution model is different. SystemVerilog is a superset of the older **Verilog** , and this note says Verilog for both. \#\# Nets and variables A net (\`wire\`) tr...

## Waveform Diagrams (`hardware/digital-design/369/waveform-diagram`)

- **waveform diagrams** -> Algorithmic State Machines (`hardware/digital-design/371/algorithmic-state-machines`)
  - scores: naturalness 0.965 · target 1.000 · placement 0.970 · combined 0.982
  - span: [487, 504)
  - context: ...e: UW CSE 369 lecture notes type: lecture --- \#\# Purpose Notes on reading **waveform diagrams** , along with the Verilog syntax from the same lecture for buses, constants, conc...

- **Verilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.837 · target 1.000 · placement 0.910 · combined 0.922
  - span: [521, 528)
  - context: ...pe: lecture --- \#\# Purpose Notes on reading waveform diagrams, along with the **Verilog** syntax from the same lecture for buses, constants, concatenation, and test benc...

## Algorithmic State Machines (`hardware/digital-design/371/algorithmic-state-machines`)

- **SystemVerilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.909 · target 1.000 · placement 0.800 · combined 0.925
  - span: [760, 773)
  - context: ...fines the control/datapath split, walks the ASM diagram notation, and ends with **SystemVerilog** skeletons for the controller and datapath. \#\# Review: Finite State Machines (F...

- **sequential logic** -> Sequential Logic (SL) (`hardware/digital-design/369/sequential-logic`)
  - scores: naturalness 0.889 · target 1.000 · placement 0.050 · combined 0.527
  - span: [2262, 2278)
  - context: ...he actual computations and data manipulation. - Built from combinational and **sequential logic** . - Consists of registers, multiplexers, arithmetic units, and other componen...

- **combinational logic** -> Combinational Logic (`hardware/digital-design/369/combinational-logic`)
  - scores: naturalness 0.994 · target 1.000 · placement 0.846 · combined 0.965
  - span: [2916, 2935)
  - context: ...diate data (the variables), the datapath implements every register operation as **combinational logic** attached to register inputs, and a control FSM sequences the register operation...

- **register-transfer** -> Out-of-Order and Superscalar Execution (`hardware/computer-architecture/out-of-order-execution`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.116 · target 1.000 · placement 0.770 · combined 0.447
  - span: [3053, 3070)
  - context: ...ntrol FSM sequences the register operations. This scheme is what people mean by **register-transfer** level (RTL) design. The basic RTL operation is $$ r\_\{\\text\{dest\}\} \\leftarrow...

## Static Timing Analysis (`hardware/digital-design/371/static-timing-analysis`)

- **combinational logic** -> Combinational Logic (`hardware/digital-design/369/combinational-logic`)
  - scores: naturalness 0.985 · target 1.000 · placement 0.897 · combined 0.973
  - span: [2446, 2465)
  - context: ...ou find the longest. The canonical path runs from a launching register through **combinational logic** to a capturing register, with both registers on the same clock: \`\`\`mermaid flo...

## SystemVerilog Review (`hardware/digital-design/371/verilog-review`)

- **SystemVerilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.938 · target 1.000 · placement 0.050 · combined 0.537
  - span: [2646, 2659)
  - context: ...blocks\*\*: Used for behavioral code, run repeatedly based on sensitivity list - **SystemVerilog** variants: - \`always\_comb\`: For combinational logic (auto sensitivity list)...

- **combinational logic** -> Combinational Logic (`hardware/digital-design/369/combinational-logic`)
  - scores: naturalness 0.872 · target 1.000 · placement 0.050 · combined 0.523
  - span: [2693, 2712)
  - context: ...edly based on sensitivity list - SystemVerilog variants: - \`always\_comb\`: For **combinational logic** (auto sensitivity list) - \`always\_latch\`: For latch-based logic (auto sensiti...

- **sequential logic** -> Sequential Logic (SL) (`hardware/digital-design/369/sequential-logic`)
  - scores: naturalness 0.870 · target 1.000 · placement 0.050 · combined 0.523
  - span: [3944, 3960)
  - context: ...on over time using state transition diagrams - Components: 1. State register ( **sequential logic** ) 2. Next state logic (combinational) 3. Output logic (combinational) - Impl...

## GPU Architecture from First Principles (`hardware/gpu-architecture`)

- **combinational logic** -> Combinational Logic (`hardware/digital-design/369/combinational-logic`)
  - scores: naturalness 0.988 · target 1.000 · placement 0.858 · combined 0.966
  - span: [7178, 7197)
  - context: ...e RTL substrate above: fetching and decoding an instruction costs registers and **combinational logic** regardless of how many lanes execute it, so amortizing that cost over 32 lanes...

- **register-file** -> Memory-Level Parallelism Benchmarks (`systems/operating-systems/benchmarks/mlp`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.089 · target 1.000 · placement 0.962 · combined 0.426
  - span: [12225, 12238)
  - context: ...) register file Warp width is not arbitrary: 32 lanes read from 32 independent **register-file** banks in the same cycle, one bank per lane, which is exactly what lets the whol...

## Electricity (`hardware/signal-conditioning/lecture-notes/lecture-2`)

- **Current** -> Electric Circuit Analysis (`reference/cheatsheets/circuits/electricity`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.159 · target 1.000 · placement 0.996 · combined 0.525
  - span: [1217, 1224)
  - context: ...y to push electrons through the circuit, creating a current. \#\# Definitions \*\* **Current** \*\* ($I$) is the rate of flow of electrons, measured in Amperes (A). One amp is a...

## Resistance (`hardware/signal-conditioning/lecture-notes/lecture-3`)

- **resistance** -> Power Dissipation In a Resistor (`hardware/signal-conditioning/lecture-notes/lecture-4`)
  - scores: naturalness 0.837 · target 1.000 · placement 0.985 · combined 0.937
  - span: [510, 520)
  - context: ...ignal conditioning course, lecture 3 type: lecture --- \#\# Purpose Defines **resistance** and Ohm's law, then derives how voltage, current, and resistance combine when r...

## Power Dissipation In a Resistor (`hardware/signal-conditioning/lecture-notes/lecture-4`)

- **resistance** -> Resistance (`hardware/signal-conditioning/lecture-notes/lecture-3`)
  - scores: naturalness 0.898 · target 1.000 · placement 0.960 · combined 0.955
  - span: [2823, 2833)
  - context: ...\|-----+ \| \| phone power consumption \`\`\` The equivalent **resistance** is $R = V/I = 3.8\\,\\text\{V\} / 7.55\\,\\text\{mA\} \\approx 503\\,\\Omega$. \#\# Related...

## Thevenin's Theorem (`hardware/signal-conditioning/lecture-notes/lecture-5`)

- **resistance** -> Resistance (`hardware/signal-conditioning/lecture-notes/lecture-3`)
  - scores: naturalness 0.870 · target 1.000 · placement 0.970 · combined 0.947
  - span: [1927, 1937)
  - context: ...\#\# The two equivalents describe the same circuit Both procedures compute the **resistance** the same way, so $R\_\{no\} = R\_\{th\}$. Matching the open-circuit voltage of the tw...

## Capacitors (`hardware/signal-conditioning/lecture-notes/lecture-6`)

- **resistance** -> Resistance (`hardware/signal-conditioning/lecture-notes/lecture-3`)
  - scores: naturalness 0.897 · target 1.000 · placement 0.806 · combined 0.922
  - span: [2217, 2227)
  - context: ...hi\}e^\{j2\\pi ft\}\\right\\\} $$ \#\# Impedance Impedance is the AC generalization of **resistance** : $$ Z\_\{cap\} = \\frac\{1\}\{j\\omega C\}, \\qquad Z\_\{ind\} = j\\omega L, \\qquad Z\_\{res\}...

## Eigenvalues, Eigenvectors, and Diagonalization (`math/linear-algebra/eigenvalues-eigenvectors-diagonalization`)

- **chapter 5** -> Glossary of Linear Algebra Concepts (`math/linear-algebra/elementry-linear-algebra`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.200 · target 0.774 · placement 0.853 · combined 0.491
  - span: [4898, 4907)
  - context: ...asis, giving the spectral decomposition $A = Q D Q^T$ with $Q$ orthogonal (\[ILA **chapter 5** \](https://textbooks.math.gatech.edu/ila/chap-eigenvalues.html); Strang covers th...

## Matrix Calculus for Machine Learning (`math/matrix-calculus`)

- **deep learning** -> Deep Learning (`ml/deep-learning/index`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.129 · target 1.000 · placement 0.958 · combined 0.484
  - span: [1124, 1137)
  - context: ...rivation note for the handful of matrix-calculus facts that carry nearly all of **deep learning** : layout conventions, the core identities, the four gradients that appear in eve...

- **cross-entropy** -> Feedforward Neural Networks (`ml/nlp/reading/neural-networks`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.341 · target 1.000 · placement 0.888 · combined 0.670
  - span: [1277, 1290)
  - context: ...s that appear in every training loop (affine, quadratic, least squares, softmax **cross-entropy** ), and the JVP/VJP framing that autodiff systems actually implement. \[\[ml/deep-l...

## Numerical Optimization for Machine Learning (`math/numerical-optimization`)

- **Deep Learning** -> Deep Learning (`ml/deep-learning/index`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.100 · target 1.000 · placement 0.901 · combined 0.438
  - span: [2693, 2706)
  - context: ...hostage to the steepest direction while progress is needed along the flattest. \[ **Deep Learning** ch. 8\](https://www.deeplearningbook.org/contents/optimization.html) treats ill-...

- **deep learning** -> Neural Networks from Scratch (`ml/deep-learning/neural-networks-from-scratch`)
  - scores: naturalness 0.754 · target 1.000 · placement 0.050 · combined 0.497
  - span: [10720, 10733)
  - context: ...- \[Sutskever et al. (2013), On the importance of initialization and momentum in **deep learning** \](https://proceedings.mlr.press/v28/sutskever13.html) - \[Loshchilov and Hutter (...

## Decoder-Only Transformers (`ml/deep-learning/decoder-only-transformers`)

- **language-model** -> Encoder-Decoder Transformers (`ml/deep-learning/encoder-decoder-transformers`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.116 · target 1.000 · placement 0.956 · combined 0.466
  - span: [1059, 1073)
  - context: ...e This note covers the decoder-only transformer as the standard autoregressive **language-model** architecture. The serving note \[\[ml/serving-systems/transformers\|Transformer Ar...

## Deep Learning (`ml/deep-learning/index`)

- **deep learning** -> Graph Neural Networks (`ml/deep-learning/graph-neural-networks`)
  - scores: naturalness 0.220 · target 1.000 · placement 0.988 · combined 0.587
  - span: [990, 1003)
  - context: ...s://arxiv.org/abs/2006.11239 type: paper --- \#\# Purpose These notes treat **deep learning** as a modeling discipline, not just a list of branded architectures. The section...

## Machine Learning (`ml/index`)

- **parallelism** -> Parallelism in LLM Serving Systems (`ml/serving-systems/parallelism`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.088 · target 1.000 · placement 0.756 · combined 0.403
  - span: [1085, 1096)
  - context: ...overs the systems side of large-model inference: kernels, memory, batching, and **parallelism** . These areas connect in useful ways. Deep-learning architecture choices shape...

## Natural Language Processing (`ml/nlp/index`)

- **NLP** -> Deep Learning (`ml/deep-learning/index`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.105 · target 1.000 · placement 0.928 · combined 0.448
  - span: [971, 974)
  - context: ...olds practical notes that sit closer to modern language models than to textbook **NLP** . \[\[ml/nlp/prompting\|Prompting\]\] is the bridge between the older modeling materi...

## Indexing and Information Retrieval (`ml/nlp/reading/information-retrieval`)

- **Information retrieval** -> Two-Tower Retrieval (`ml/recommender-systems/two-tower-retrieval`)
  - scores: naturalness 0.593 · target 0.352 · placement 1.000 · combined 0.520
  - span: [1432, 1453)
  - context: .... Follows Jurafsky & Martin, \[SLP3\](https://web.stanford.edu/~jurafsky/slp3/). **Information retrieval** is the process of obtaining information based on user queries, and it applies t...

- **tf-idf** -> Depth First Search Algorithm and Tree Properties (`algorithms/DFS`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.106 · target 0.978 · placement 0.917 · combined 0.443
  - span: [3294, 3300)
  - context: ...fective. We instead compute a \*\*term weight\*\* for each document word, such as \*\* **tf-idf** \*\* or \*\*BM25\*\*. For tf-idf (term frequency-inverse document frequency), we compu...

- **BM25** -> Breadth First Search Algorithm Implementation and Analysis (`algorithms/BFS`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.115 · target 1.000 · placement 0.906 · combined 0.460
  - span: [3308, 3312)
  - context: ...stead compute a \*\*term weight\*\* for each document word, such as \*\*tf-idf\*\* or \*\* **BM25** \*\*. For tf-idf (term frequency-inverse document frequency), we compute the term...

- **IDs** -> Files and Directories (`systems/operating-systems/v4-persistent-storage/13-files-and-directories`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.200 · target 1.000 · placement 0.808 · combined 0.545
  - span: [6517, 6520)
  - context: ...at maps each term to its postings list. A postings list is the list of document **IDs** associated with the term, and can carry extra metadata such as term frequency o...

## Feedforward Neural Networks (`ml/nlp/reading/neural-networks`)

- **feedforward neural networks** -> Recurrent Neural Networks (`ml/deep-learning/recurrent-neural-networks`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.130 · target 1.000 · placement 0.997 · combined 0.490
  - span: [713, 740)
  - context: ...eb.stanford.edu/~jurafsky/slp3/7.pdf type: textbook --- \#\# Purpose Covers **feedforward neural networks** as classifiers for NLP. It works through units and activation functions, why no...

## Word Embeddings and Distributional Semantics (`ml/nlp/word-embeddings`)

- **Distributed Representations** -> Natural Language Processing (`ml/nlp/index`)
  - scores: naturalness 0.719 · target 1.000 · placement 0.050 · combined 0.489
  - span: [11482, 11509)
  - context: ...ons in Vector Space\](https://arxiv.org/abs/1301.3781) - \[Mikolov et al. (2013), **Distributed Representations** of Words and Phrases and their Compositionality\](https://arxiv.org/abs/1310.454...

## Deep Neural Networks for YouTube Recommendations (`ml/recommender-systems/deep-neural-networks-for-youtube-recommendations`)

- **CTR** -> Practical Lessons from Predicting Clicks on Ads at Facebook (`ml/recommender-systems/predicting-clicks-on-ads-at-facebook`)
  - scores: naturalness 0.858 · target 1.000 · placement 0.753 · combined 0.895
  - span: [1032, 1035)
  - context: ...ce information was withheld in one place, and why watch time mattered more than **CTR** . \#\# Citation - \[Deep Neural Networks for YouTube Recommendations (Covington,...

## Distributed Computing for Data Mining (`ml/recommender-systems/intro-mapreduce-spark`)

- **distributed-systems** -> Distributed Systems (`systems/distributed-systems/index`)
  - scores: naturalness 0.537 · target 0.992 · placement 0.807 · combined 0.768
  - span: [3061, 3080)
  - context: ...rigid because it is rigid. The benefit is that the runtime hides a lot of ugly **distributed-systems** detail: - scheduling - retries - locality - fault recovery \#\#\# Example: Co-Oc...

## Practical Lessons from Predicting Clicks on Ads at Facebook (`ml/recommender-systems/predicting-clicks-on-ads-at-facebook`)

- **CTR** -> Sparsity and Pruning in LLM Serving Systems (`ml/serving-systems/sparsity-and-pruning`)
  - scores: naturalness 0.705 · target 0.818 · placement 0.957 · combined 0.801
  - span: [866, 869)
  - context: ...ote records the main modeling and systems lessons from He et al.'s Facebook ads **CTR** paper. The paper is worth reading because it is not just a model comparison. It...

- **CTR** -> InfLLM: Training-Free Long-Context Extrapolation for LLMs with an Efficient Context Memory (`ml/serving-systems/inf-llm`)
  - scores: naturalness 0.651 · target 0.994 · placement 0.964 · combined 0.852
  - span: [1962, 1965)
  - context: ...nough that a more expensive model makes sense. The core problem is to estimate **CTR** well enough that the downstream auction can trust the score. The paper keeps th...

## Recommender Systems Reading Guide (`ml/recommender-systems/reading-guide`)

- **Collaborative Filtering** -> Recommender Systems (`ml/recommender-systems/recommender-systems`)
  - scores: naturalness 0.465 · target 0.898 · placement 0.050 · combined 0.400
  - span: [3721, 3744)
  - context: ...r Systems\](https://arxiv.org/pdf/1606.07792) - \[Hu, Koren, and Volinsky (2008), **Collaborative Filtering** for Implicit Feedback Datasets\](https://yifanhu.net/PUB/cf.pdf)

## Recommender Systems (`ml/recommender-systems/recommender-systems`)

- **Graph** -> Graph Neural Networks (`ml/deep-learning/graph-neural-networks`)
  - scores: naturalness 0.706 · target 1.000 · placement 0.050 · combined 0.486
  - span: [5440, 5445)
  - context: ...or both. - \*\*Sequential models\*\* capture short-horizon intent and recency. - \*\* **Graph** models\*\* propagate signal across the user-item interaction graph and related st...

## Retrieval and Ranking (`ml/recommender-systems/retrieval-and-ranking`)

- **CTR** -> Practical Lessons from Predicting Clicks on Ads at Facebook (`ml/recommender-systems/predicting-clicks-on-ads-at-facebook`)
  - scores: naturalness 0.964 · target 1.000 · placement 0.968 · combined 0.981
  - span: [8342, 8345)
  - context: ...efine calibration for ad click prediction as the ratio of the average predicted **CTR** to the average empirical CTR, with 1.0 being perfect. The reason this matters b...

## GPU Architecture and Programming (`ml/serving-systems/gpu-basics`)

- **memory bandwidth** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - scores: naturalness 0.392 · target 0.741 · placement 0.841 · combined 0.608
  - span: [4667, 4683)
  - context: ...ound 200 Gb/s, which is 25 GB/s. That two-orders-of-magnitude gap between local **memory bandwidth** and network bandwidth shapes the parallelism strategies in \[\[ml/serving-systems...

## GPU Interconnects and Collective Communication (`ml/serving-systems/gpu-interconnects`)

- **load-balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.199 · target 0.831 · placement 0.839 · combined 0.505
  - span: [13507, 13521)
  - context: ...to one node's GPUs. The practical consequences: MoE deployments care more about **load-balancing** routing (to keep the All-to-All traffic matrix close to uniform) and about plac...

## Memory Management in LLM Serving Systems (`ml/serving-systems/memory-management`)

- **memory bandwidth** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.113 · target 0.960 · placement 0.834 · combined 0.442
  - span: [8406, 8422)
  - context: ...es 2 \\times 2 \\times 8 \\times 128 = 64$ KB, big enough that reading a page uses **memory bandwidth** efficiently, small enough that internal fragmentation is capped at one partial...

## Intro to Mixture of Experts (MoE) in LLM Serving Systems (`ml/serving-systems/mixture-of-experts`)

- **distributed systems** -> Distributed Systems (`systems/distributed-systems/index`)
  - scores: naturalness 0.978 · target 1.000 · placement 0.964 · combined 0.985
  - span: [13133, 13152)
  - context: ...rd\](https://arxiv.org/abs/2006.16668) (Lepikhin et al. 2020) turned that into a **distributed systems** problem: a set of lightweight sharding annotations plus an XLA compiler extensi...

## Optimizing GPU Kernels (`ml/serving-systems/optimizing-gpu-kernels`)

- **address-generation** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - scores: naturalness 0.539 · target 1.000 · placement 0.050 · combined 0.442
  - span: [14145, 14163)
  - context: ...n one instruction, issued by a single thread, freeing the rest of the warp from **address-generation** and copy-loop overhead. This replaces the per-thread \`cp.async\` copy loop used...

## Performance Modeling for LLM Serving Systems (`ml/serving-systems/performance-modeling`)

- **memory bandwidth** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - scores: naturalness 0.457 · target 0.964 · placement 0.914 · combined 0.735
  - span: [2119, 2135)
  - context: ...hardware traces out a roofline: a slanted region where performance is capped by **memory bandwidth** times intensity (memory bound), and a flat region capped by peak compute (compu...

## Sparsity and Pruning in LLM Serving Systems (`ml/serving-systems/sparsity-and-pruning`)

- **KV** -> Memory Management in LLM Serving Systems (`ml/serving-systems/memory-management`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.093 · target 1.000 · placement 0.956 · combined 0.432
  - span: [1483, 1485)
  - context: ...rpose This note surveys where sparsity shows up in LLMs (weights, activations, **KV** cache) and the pruning techniques that exploit each kind. Like \[\[ml/serving-sys...

## Speculative Decoding in LLM Serving Systems (`ml/serving-systems/speculative-decoding`)

- **speculative decoding** -> Decoding Strategies for Language Models (`ml/nlp/decoding-strategies`)
  - scores: naturalness 0.864 · target 1.000 · placement 0.989 · combined 0.948
  - span: [1269, 1289)
  - context: ...ring 2025 (lecture notes) type: lecture --- \#\# Purpose This note explains **speculative decoding** : the algorithm, why it leaves the output distribution unchanged, and the tree-b...

## Interval Scheduling/Partitioning (`reference/cheatsheets/algorithms/intervals`)

- **Greedy algorithms** -> Greedy Algorithms for Interval Scheduling and Partitioning (`algorithms/greedy-algorithms`)
  - scores: naturalness 0.511 · target 1.000 · placement 1.000 · combined 0.790
  - span: [349, 366)
  - context: ...thms and proof sketches for interval scheduling and interval partitioning. --- **Greedy algorithms** for the two classic interval problems, with proof sketches. \#\# Scheduling the...

## Electronic Components (`reference/cheatsheets/circuits/components`)

- **resistance** -> Resistance (`hardware/signal-conditioning/lecture-notes/lecture-3`)
  - scores: naturalness 0.886 · target 1.000 · placement 0.932 · combined 0.945
  - span: [1791, 1801)
  - context: ...ors drop the voltage of a circuit branch as current flows through them. Their \*\* **resistance** \*\* is measured in ohms ($\\Omega$), and can be thought of as a hill in the flow o...

- **BJTs** -> Static Timing Analysis (`hardware/digital-design/371/static-timing-analysis`)
  - scores: naturalness 0.208 · target 1.000 · placement 0.917 · combined 0.568
  - span: [6288, 6292)
  - context: ...als: the gate, drain, and source. They are voltage controlled devices, and like **BJTs** they appear in pretty much every electronic device. They come in two flavors: N...

## Electric Circuit Analysis (`reference/cheatsheets/circuits/electricity`)

- **Potential** -> Electricity (`hardware/signal-conditioning/lecture-notes/lecture-2`)
  - scores: naturalness 0.724 · target 0.323 · placement 0.998 · combined 0.537
  - span: [875, 884)
  - context: ...y carry negative charge and drift the other way, from low potential to high. \*\* **Potential** \*\* is the energy per unit charge at a point in space. It's measured in volts, an...

- **resistance** -> Resistance (`hardware/signal-conditioning/lecture-notes/lecture-3`)
  - scores: naturalness 0.943 · target 1.000 · placement 0.970 · combined 0.974
  - span: [1826, 1836)
  - context: ...a rolling ball. \#\# Short Circuit A short circuit is any path with negligible **resistance** , or ideally zero resistance. Connecting any two points in a circuit with a wire...

## Patterns for Scalability and Reliability in Systems (`reference/slides/system-design`)

- **sharding** -> Sharding (`systems/distributed-systems/sharding`)
  - scores: naturalness 0.814 · target 0.999 · placement 0.852 · combined 0.901
  - span: [1743, 1751)
  - context: ...ate a \*partition key\* to determine which shard to write to. !\[w:900p\](./assets/ **sharding** .png) --- \#\# Scalability Patterns \#\#\# 3. Queueing Problem: My system is over...

## System Design Interviews (`reference/slides/system-design-interviews`)

- **system design interviews** -> Patterns for Scalability and Reliability in Systems (`reference/slides/system-design`)
  - scores: naturalness 0.279 · target 0.799 · placement 0.941 · combined 0.571
  - span: [409, 433)
  - context: ...ciples. sources: - original slide deck --- This is a concise outline of what **system design interviews** are, how they usually flow, and how to prepare your thinking during the convers...

- **load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 0.973 · target 1.000 · placement 0.050 · combined 0.544
  - span: [3733, 3747)
  - context: ...chronous message queues Select technologies for each component - e.g. NGINX for **load balancing** , Redis for caching, PostgreSQL for database --- \#\# Format/Structure of the In...

- **Database** -> Storage and Retrieval Techniques for Database Systems (`systems/databases/foundations/ch3-storage-and-retrieval`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.078 · target 0.999 · placement 1.000 · combined 0.409
  - span: [4074, 4082)
  - context: ...lgorithms or data structures - e.g. Bloom filter to check if URL already exists **Database** schema with tables and relationships - e.g. URLs table with indexes on short\_ke...

- **URLs** -> Domain Name System (DNS) (`systems/networks/5-application/DNS`)
  - scores: naturalness 0.434 · target 1.000 · placement 0.050 · combined 0.410
  - span: [4252, 4256)
  - context: ...lookups Caching strategy and policies - e.g. LRU cache for frequently accessed **URLs** with 80% hit rate --- \#\# Format/Structure of the Interview \#\#\# Addressing bo...

## Batch Processing Systems and MapReduce Fundamentals (`systems/databases/derived-data/ch10-batch-processing`)

- **Batch processing** -> Batching in LLM Serving Systems (`ml/serving-systems/batching`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.155 · target 0.999 · placement 0.996 · combined 0.520
  - span: [1172, 1188)
  - context: ...services. Performance is measured in requests per second and response time. \*\* **Batch processing** \*\* (offline systems) runs scheduled jobs that process accumulated data. Performa...

- **Google File System** -> Google File System (GFS) Overview (`systems/distributed-systems/google-file-system`)
  - scores: naturalness 0.988 · target 1.000 · placement 0.837 · combined 0.961
  - span: [3254, 3272)
  - context: ...ng access, optimized for throughput over latency, and follows the design of the **Google File System** . It differs from an object store like Amazon S3 in that computation runs on the...

## Replication Strategies in Distributed Data Systems (`systems/databases/distributed-data/ch5-replication`)

- **non-database** -> CRDTs and Conflict-Free Replication (`systems/distributed-systems/crdts`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.191 · target 0.963 · placement 0.871 · combined 0.536
  - span: [2457, 2469)
  - context: ...ny relational databases use this setup, as do some non-relational databases and **non-database** systems like the distributed message brokers Kafka and RabbitMQ. \#\# Synchronou...

- **RabbitMQ** -> Domain Name System (DNS) (`systems/networks/5-application/DNS`)
  - scores: naturalness 0.853 · target 0.906 · placement 0.764 · combined 0.857
  - span: [2525, 2533)
  - context: ...tabases and non-database systems like the distributed message brokers Kafka and **RabbitMQ** . \#\# Synchronous versus asynchronous replication With \*\*synchronous replicatio...

- **Logical** -> Distributed Systems Consistency Models (`systems/distributed-systems/consistency`)
  - scores: naturalness 0.620 · target 1.000 · placement 0.924 · combined 0.833
  - span: [9146, 9153)
  - context: ...ow plus a commit record; the MySQL binlog uses this approach in row-based mode. **Logical** logs decouple replication from storage engine internals, which restores cross-v...

## Scalable Distributed Data Systems (`systems/databases/distributed-data/preface`)

- **systems** -> Databases and Data-Intensive Systems (`systems/databases/index`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.082 · target 0.987 · placement 0.943 · combined 0.410
  - span: [953, 960)
  - context: ...he rest of the book assumes. \#\# Why distribute data Moving up a level to data **systems** that run on multiple machines, the motivations echo the single-machine concerns...

## Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)

- **Stream processing** -> Streaming Data (`systems/performance/streaming`)
  - scores: naturalness 0.811 · target 0.996 · placement 0.050 · combined 0.510
  - span: [1766, 1783)
  - context: ...d up reads - Search indexes, which let users search or filter data by keyword - **Stream processing** , which sends messages to other processes for asynchronous handling - Batch proc...

## Data Models and Relationships in Database Systems (`systems/databases/foundations/ch2-data-models-and-query-languages`)

- **data models** -> Databases and Data-Intensive Systems (`systems/databases/index`)
  - scores: naturalness 0.978 · target 1.000 · placement 0.828 · combined 0.956
  - span: [946, 957)
  - context: ...) by Martin Kleppmann. The chapter compares the relational, document, and graph **data models** , with relationships between records as the axis that separates them. \#\# The re...

- **batch processing** -> Batch Processing Systems and MapReduce Fundamentals (`systems/databases/derived-data/ch10-batch-processing`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.147 · target 0.998 · placement 0.988 · combined 0.509
  - span: [5845, 5861)
  - context: ...esult, which can be a single value or a more complex structure. MapReduce fits **batch processing** . It does not fit interactive queries that need low latency. Some NoSQL database...

## Storage and Retrieval Techniques for Database Systems (`systems/databases/foundations/ch3-storage-and-retrieval`)

- **Sorted String Table (SSTable** -> CRDTs and Conflict-Free Replication (`systems/distributed-systems/crdts`)
  - scores: naturalness 0.321 · target 1.000 · placement 0.999 · combined 0.672
  - span: [2986, 3014)
  - context: ...ead threads. Writes serialize, reads parallelize. \#\# SSTables and LSM-trees A **Sorted String Table (SSTable** ) stores key-value pairs sorted by key. Segments are organized by time: reads se...

- **LSM-tree** -> Depth First Search Algorithm and Tree Properties (`algorithms/DFS`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.084 · target 1.000 · placement 0.972 · combined 0.418
  - span: [3468, 3476)
  - context: ...order lets you scan from the nearest indexed key. A Log-Structured Merge Tree ( **LSM-tree** ) is the combination of an in-memory balanced tree with on-disk SSTables. The si...

- **Elasticsearch** -> Replication Strategies in Distributed Data Systems (`systems/databases/distributed-data/ch5-replication`)
  - scores: naturalness 0.276 · target 1.000 · placement 0.975 · combined 0.634
  - span: [4603, 4616)
  - context: ...L0 -.-\>\|miss\| L1 L1 -.-\>\|miss\| L2 \`\`\` Lucene, the index engine behind **Elasticsearch** and Solr, uses a similar scheme for its term dictionary. Words are the keys and...

- **Bigtable** -> Bigtable, A Distributed Storage System for Structured Data (`systems/distributed-systems/bigtable`)
  - scores: naturalness 0.395 · target 0.541 · placement 0.796 · combined 0.524
  - span: [5514, 5522)
  - context: ...\*\*missing\*\* keys, which otherwise pay the worst case of checking every level; \[ **Bigtable** \](https://research.google/pubs/pub27898/) reports Bloom filters drastically redu...

## Encoding, Evolution, and Data Flow in Distributed Systems (`systems/databases/foundations/ch4-encoding-and-evolution`)

- **HTTP** -> Hyper Text Transfer Protocol (HTTP) (`systems/networks/5-application/HTTP`)
  - scores: naturalness 0.268 · target 1.000 · placement 0.792 · combined 0.602
  - span: [10078, 10082)
  - context: ...ers, load balancers, proxies, caches, monitoring, and debugging tools all speak **HTTP** , and browsers do too. For evolvability, the usual simplifying assumption is th...

## Databases and Data-Intensive Systems (`systems/databases/index`)

- **systems** -> Distributed Systems (`systems/distributed-systems/index`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.424 · target 0.997 · placement 0.953 · combined 0.732
  - span: [403, 410)
  - context: ...batch processing. --- \#\# Purpose These notes are the beginning of a database **systems** branch. Right now the material comes mostly from DDIA, but the section is organ...

## Query Planning and Join Execution (`systems/databases/query-planning-and-joins`)

- **dynamic programming** -> Dynamic Programming Algorithms and Problem Solutions Guide (`algorithms/dynamic-programming`)
  - scores: naturalness 0.863 · target 1.000 · placement 0.947 · combined 0.939
  - span: [4472, 4491)
  - context: ...f alternative plans and pick the cheapest, searching join orders with bottom-up **dynamic programming** . Pass 1 finds the best access path per table (sequential scan or each index, co...

- **polynomial-ish** -> Breadth First Search Algorithm Implementation and Analysis (`algorithms/BFS`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.089 · target 1.000 · placement 0.859 · combined 0.416
  - span: [4820, 4834)
  - context: ...inner side is always a base table, so plans pipeline and the search space stays **polynomial-ish** ). Subplans are kept not only if globally cheapest but also if they produce an \*...

## Remote Procedure Call (RPC) (`systems/distributed-systems/RPC`)

- **error detection and correction** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 0.942 · target 1.000 · placement 0.050 · combined 0.538
  - span: [4258, 4288)
  - context: .... - Messages won't be corrupted (bit flips). Another strong assumption. See **error detection and correction** for working without it. - The network may partition nodes from each other,...

- **distributed systems** -> Distributed Systems (`systems/distributed-systems/index`)
  - scores: naturalness 0.912 · target 1.000 · placement 0.841 · combined 0.935
  - span: [10436, 10455)
  - context: ...sent could always have been the one that dropped. This limit shows up all over **distributed systems** , for example in the commit problem that \[\[systems/distributed-systems/two-phase...

## Bigtable, A Distributed Storage System for Structured Data (`systems/distributed-systems/bigtable`)

- **systems** -> Databases and Data-Intensive Systems (`systems/databases/index`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.087 · target 1.000 · placement 0.757 · combined 0.402
  - span: [968, 975)
  - context: ...nts at the end, since those are the parts that keep showing up in later storage **systems** . \#\# Problem Google needed one storage system that could serve workloads as di...

- **load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 0.775 · target 0.999 · placement 0.906 · combined 0.897
  - span: [2274, 2288)
  - context: ...amically partitioned into ranges called \*tablets\*, the unit of distribution and **load balancing** . Reads over short row ranges therefore touch only a few machines. Users should...

## Clocks (`systems/distributed-systems/clocks`)

- **logical clocks** -> Time, Clocks, and the Ordering of Events in a Distributed System (`systems/distributed-systems/ordering-events-in-distributed-systems`)
  - scores: naturalness 0.943 · target 1.000 · placement 0.862 · combined 0.951
  - span: [887, 901)
  - context: ...why you cannot rely on physical clocks to order events across machines, and how **logical clocks** and vector clocks recover a useful ordering from causality alone. \#\# Physical...

- **Git** -> Consistent Global State in Distributed Systems (`systems/distributed-systems/consistent-global-state`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.131 · target 1.000 · placement 0.781 · combined 0.467
  - span: [5605, 5608)
  - context: ...sistent and causally consistent systems build on, and the same idea shows up in **Git** and in Amazon's \[\[systems/distributed-systems/dynamo-db\|Dynamo\]\]. The algorith...

## CRDTs and Conflict-Free Replication (`systems/distributed-systems/crdts`)

- **Commutative Replicated Data Types** -> Distributed Systems Consistency Models (`systems/distributed-systems/consistency`)
  - scores: naturalness 0.794 · target 1.000 · placement 0.050 · combined 0.507
  - span: [11227, 11260)
  - context: ...ro, Preguica, Baquero, Zawirski (2011), A Comprehensive Study of Convergent and **Commutative Replicated Data Types** , INRIA RR-7506\](https://hal.inria.fr/inria-00609399/document) - \[Gomes, Kleppma...

- **Distributed Systems** -> Distributed Systems (`systems/distributed-systems/index`)
  - scores: naturalness 0.629 · target 1.000 · placement 0.050 · combined 0.467
  - span: [11413, 11432)
  - context: ...Kleppmann, Mulligan, Beresford (2017), Verifying Strong Eventual Consistency in **Distributed Systems** , OOPSLA\](https://martin.kleppmann.com/papers/crdtops.pdf) - \[Kleppmann, Gomes,...

## Distributed Cache Coherence (`systems/distributed-systems/distributed-cache-coherence`)

- **DNS** -> Domain Name System (DNS) (`systems/networks/5-application/DNS`)
  - scores: naturalness 0.617 · target 1.000 · placement 0.798 · combined 0.807
  - span: [871, 874)
  - context: ...is worth understanding exactly what they cost, because most large systems (NFS, **DNS** , most of the web) deliberately pay for less. \#\# Core idea When linearizabilit...

## Failure Detectors, Leases, and Leader Election (`systems/distributed-systems/failure-detectors-leases-leader-election`)

- **Distributed File Cache Consistency** -> Distributed Cache Coherence (`systems/distributed-systems/distributed-cache-coherence`)
  - scores: naturalness 0.558 · target 1.000 · placement 0.050 · combined 0.448
  - span: [10854, 10888)
  - context: ...- \[Gray and Cheriton (1989), Leases: An Efficient Fault-Tolerant Mechanism for **Distributed File Cache Consistency** , SOSP\](https://dl.acm.org/doi/10.1145/74850.74870) - \[Kleppmann (2016), How to...

## Google File System (GFS) Overview (`systems/distributed-systems/google-file-system`)

- **file systems** -> File Systems (`systems/operating-systems/lecture-notes/file-systems`)
  - scores: naturalness 0.972 · target 1.000 · placement 0.930 · combined 0.976
  - span: [1067, 1079)
  - context: ...tributed-systems/bigtable\|Bigtable\]\]. \#\# Problem GFS departs from traditional **file systems** because Google's workload departs from traditional workloads: - It runs on com...

- **load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 0.943 · target 0.989 · placement 0.767 · combined 0.925
  - span: [6837, 6851)
  - context: ...at enables garbage collection, re-replication after failures, and migration for **load balancing** . The obvious objection is that memory bounds the filesystem's size. In practic...

## Managing Critical State (`systems/distributed-systems/managing-critical-state`)

- **distributed systems** -> Distributed Systems (`systems/distributed-systems/index`)
  - scores: naturalness 0.962 · target 1.000 · placement 0.951 · combined 0.977
  - span: [6868, 6887)
  - context: ...tributed storage systems often order operations by timestamp, and this fails in **distributed systems** because of clock drift. Google's Spanner attacks the timestamp uncertainty head...

- **Bigtable** -> Bigtable, A Distributed Storage System for Structured Data (`systems/distributed-systems/bigtable`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.119 · target 0.840 · placement 0.837 · combined 0.424
  - span: [7711, 7719)
  - context: ...ly the elected leader delegates actual work to a pool of workers, as in GFS and **Bigtable** . The leader election service sits off the critical path, so its latency barely...

## Distributed Mutual Exclusion (`systems/distributed-systems/mutual-exclusion`)

- **distributed mutual exclusion** -> Time, Clocks, and the Ordering of Events in a Distributed System (`systems/distributed-systems/ordering-events-in-distributed-systems`)
  - scores: naturalness 0.538 · target 0.290 · placement 0.965 · combined 0.458
  - span: [650, 678)
  - context: ...s/time-clocks.pdf type: paper --- \#\# Purpose This note records \[Lamport's **distributed mutual exclusion** algorithm\](https://lamport.azurewebsites.net/pubs/time-clocks.pdf), which provi...

## Time, Clocks, and the Ordering of Events in a Distributed System (`systems/distributed-systems/ordering-events-in-distributed-systems`)

- **logical clocks** -> Clocks (`systems/distributed-systems/clocks`)
  - scores: naturalness 0.948 · target 1.000 · placement 0.858 · combined 0.952
  - span: [938, 952)
  - context: ...defines what "before" even means in a system with no shared clock, then builds **logical clocks** that respect that ordering. It closes by deriving how closely physical clocks m...

## Sharding (`systems/distributed-systems/sharding`)

- **Load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 0.745 · target 1.000 · placement 0.912 · combined 0.886
  - span: [2563, 2577)
  - context: ...-\> server address\` on every client, with many more table entries than servers. **Load balancing** then becomes table assignment: give fewer entries to servers whose entries hold...

## Systems (`systems/index`)

- **load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 0.953 · target 0.999 · placement 0.902 · combined 0.963
  - span: [1229, 1243)
  - context: ...nch because the same policy questions show up in CPU runtimes, packet handling, **load balancing** , and model serving. Networking and operating systems meet in queues, interrupts...

## Network Components and Protocols (`systems/networks/0-foundation/1-network-components-and-protocols`)

- **Ethernet** -> Switched Ethernet (`systems/networks/2-direct-links/switching`)
  - scores: naturalness 0.357 · target 0.999 · placement 0.869 · combined 0.678
  - span: [1576, 1584)
  - context: ...m both do this job. \*\*Link\*\* (channel). A connection between nodes, such as an **Ethernet** cable, a fiber strand, or a wireless channel. \#\#\# Types of links - \*\*Full-dup...

- **the global internet** -> The Global Internet (`systems/networks/3-network/global-internet`)
  - scores: naturalness 0.989 · target 1.000 · placement 0.789 · combined 0.950
  - span: [2711, 2730)
  - context: ...you get an \*\*internetwork\*\*, or \*\*internet\*\*. The Internet with a capital I is **the global internet** . \#\#\# Switched networks \*\*Switched networks\*\* forward messages node to node un...

- **packet-switched** -> Networking Services: Store-and-Forward Packet Switching and Datagrams vs. Virtual Circuits (`systems/networks/3-network/networking-services`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.258 · target 1.000 · placement 0.811 · combined 0.597
  - span: [2917, 2932)
  - context: ...ation. The two common kinds are \*\*circuit-switched\*\* networks (telephony) and \*\* **packet-switched** \*\* networks (most computer networks). \`\`\`txt +-- (Host) --+ \|...

- **UDP** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.972 · target 1.000 · placement 0.944 · combined 0.979
  - span: [4821, 4824)
  - context: ...------------\> Y \<- (peers) (comm using Y) \`\`\` Examples of protocols: TCP, **UDP** , HTTP, FTP, SMTP, POP3, IMAP, DNS, DHCP, ARP, ICMP, IP, Ethernet, WiFi, Bluetoo...

## Performance (`systems/networks/0-foundation/3-performance`)

- **bandwidth-delay product** -> Latency, Throughput, and Utilization (`systems/performance/latency-throughput-and-utilization`)
  - scores: naturalness 0.241 · target 1.000 · placement 0.838 · combined 0.586
  - span: [1280, 1303)
  - context: ...ms/networks/1-physical/coding-and-modulation\|coding and modulation\]\] covers the **bandwidth-delay product** , and \[\[systems/networks/0-foundation/information-theory\|information theory\]\] co...

## Media in Networks (`systems/networks/1-physical/media`)

- **media** -> Networking Services: Store-and-Forward Packet Switching and Datagrams vs. Virtual Circuits (`systems/networks/3-network/networking-services`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.120 · target 1.000 · placement 0.871 · combined 0.463
  - span: [884, 889)
  - context: ...opagate the signals that carry information. This note compares the common wired **media** and wireless, then states the two limits that cap what any of them can carry....

- **SNR** -> Resistance (`hardware/signal-conditioning/lecture-notes/lecture-3`)
  - scores: naturalness 0.301 · target 1.000 · placement 0.854 · combined 0.637
  - span: [3258, 3261)
  - context: ...how many signal levels the receiver can tell apart. The signal-to-noise ratio ( **SNR** ) determines that number, and it is usually quoted in decibels: $$ SNR\_\{dB\} = 1...

## Error Detection and Correction (`systems/networks/2-direct-links/errors`)

- **the physical layer** -> The Physical Layer (`systems/networks/0-foundation/2-physical-layer`)
  - scores: naturalness 0.950 · target 1.000 · placement 0.969 · combined 0.976
  - span: [7441, 7459)
  - context: ...are rare and retransmission is cheap. In practice, error correction dominates **the physical layer** , where LDPC codes appear in 802.11, DVB, and WiMAX, and convolutional codes are...

## Framing in Network Protocols (`systems/networks/2-direct-links/framing`)

- **The physical layer** -> The Physical Layer (`systems/networks/0-foundation/2-physical-layer`)
  - scores: naturalness 0.958 · target 1.000 · placement 1.000 · combined 0.985
  - span: [611, 629)
  - context: ...url: https://book.systemsapproach.org/ type: textbook --- \#\# Purpose **The physical layer** delivers a stream of bits. The link layer has to know where each frame starts a...

## Multiple Access (`systems/networks/2-direct-links/multiple-access`)

- **Ethernet** -> Switched Ethernet (`systems/networks/2-direct-links/switching`)
  - scores: naturalness 0.582 · target 1.000 · placement 0.791 · combined 0.789
  - span: [919, 927)
  - context: ...chedules (TDM, FDM) to distributed random access (ALOHA, CSMA), and how classic **Ethernet** put the pieces together. \#\# Multiplexing \*\*Multiplexing\*\* shares one resource...

- **Ethernet** -> Transmission Control Protocol (TCP) (`systems/networks/4-transport/TCP`)
  - scores: naturalness 0.341 · target 1.000 · placement 0.771 · combined 0.651
  - span: [3939, 3947)
  - context: ...th. That is why Ethernet has a 64-byte minimum frame, a 500 m limit for coaxial **Ethernet** , and a 100 m limit for twisted pair. The worst case, with D standing for the o...

- **Classic Ethernet** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 0.394 · target 1.000 · placement 1.000 · combined 0.722
  - span: [5617, 5633)
  - context: ...ich backs the senders off fast enough to thin out the contention. \#\# Ethernet **Classic Ethernet** (IEEE 802.3) ran at 10 Mbps over shared coaxial cable and was everywhere in the...

- **physical-layer** -> The Physical Layer (`systems/networks/0-foundation/2-physical-layer`)
  - scores: naturalness 0.747 · target 1.000 · placement 0.050 · combined 0.496
  - span: [6133, 6147)
  - context: ...ver. - A CRC-32 checksum detects errors. There is no ACK or retransmission. - A **physical-layer** preamble marks the start of the frame. \`\`\`plaintext +----------------+ \| Pream...

## Switched Ethernet (`systems/networks/2-direct-links/switching`)

- **Modern Ethernet** -> Networking Services: Store-and-Forward Packet Switching and Datagrams vs. Virtual Circuits (`systems/networks/3-network/networking-services`)
  - scores: naturalness 0.938 · target 0.990 · placement 1.000 · combined 0.973
  - span: [642, 657)
  - context: ...url: https://book.systemsapproach.org/ type: textbook --- \#\# Purpose **Modern Ethernet** is switched. Instead of sharing one cable and arbitrating with \[\[systems/networ...

## Dynamic Host Configuration Protocol (DHCP) (`systems/networks/3-network/DHCP`)

- **UDP** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.991 · target 1.000 · placement 0.972 · combined 0.991
  - span: [1192, 1195)
  - context: ...es, and DHCP is the protocol that manages the assignments. DHCP runs on top of **UDP** , with the server on port 67 and the client on port 68. It has to work before th...

## Internet Control Message Protocol (ICMP) (`systems/networks/3-network/ICMP`)

- **ICMP** -> Address Resolution Protocol (ARP) (`systems/networks/3-network/ARP`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.162 · target 1.000 · placement 0.954 · combined 0.524
  - span: [1236, 1240)
  - context: ...MP message tells the source what happened. One useful control message is the \*\* **ICMP** Redirect\*\*, which tells a host that a better route exists for a given destinati...

## The Global Internet (`systems/networks/3-network/global-internet`)

- **switched ethernet** -> Switched Ethernet (`systems/networks/2-direct-links/switching`)
  - scores: naturalness 0.988 · target 1.000 · placement 0.888 · combined 0.972
  - span: [1060, 1077)
  - context: ...hing the internet through a single IP address (NAT in home networks) or through **switched ethernet** in an enterprise LAN. Service providers build the infrastructure and route traf...

## Internetworking (`systems/networks/3-network/internetworking`)

- **UDP** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.843 · target 1.000 · placement 0.769 · combined 0.894
  - span: [2748, 2751)
  - context: ...ceeded messages report, and the protocol field says whether the payload is TCP, **UDP** , or something else. \`\`\`plaintext \<--------------------------------------- 32 b...

## Networking Services: Store-and-Forward Packet Switching and Datagrams vs. Virtual Circuits (`systems/networks/3-network/networking-services`)

- **Virtual** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.277 · target 0.982 · placement 1.000 · combined 0.633
  - span: [1927, 1934)
  - context: ...ms/networks/3-network/internetworking\|internetworking\]\]). \#\# Virtual circuits **Virtual** circuits are a connection-oriented service. The network sets up a path between...

- **ATM** -> Multiple Access (`systems/networks/2-direct-links/multiple-access`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.117 · target 0.999 · placement 0.766 · combined 0.448
  - span: [2253, 2256)
  - context: ...uters hold per-connection state. The internet mostly doesn't work this way, but **ATM** and Frame Relay do. \#\# Tradeoffs \| Issue \| Datagram \| Virtual Circuit \| \|----...

## Routing (`systems/networks/3-network/routing`)

- **UDP** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.982 · target 1.000 · placement 0.941 · combined 0.982
  - span: [6818, 6821)
  - context: ...numNewRoutes; ++i) mergeRoute(&newRoute\[i\]); \} \`\`\` Actual RIP runs on **UDP** port 520, and its messages carry a list of route entries: \`\`\`text RIP Message:...

## UDP (`systems/networks/4-transport/UDP`)

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 0.997 · target 1.000 · placement 0.827 · combined 0.962
  - span: [1023, 1035)
  - context: ...nothing else. There is no connection setup, no ordering, no retransmission, no **flow control** , and no congestion control. A datagram either arrives once, arrives duplicated,...

## Flow Control (`systems/networks/4-transport/flow-control`)

- **Sequence** -> Automatic Repeat reQuest (ARQ) (`systems/networks/2-direct-links/retransmission`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.074 · target 0.999 · placement 1.000 · combined 0.402
  - span: [4486, 4494)
  - context: ...e over R: Delivers 2, 3, 4 in order R--\>\>S: ACK 4 \`\`\` \#\# Sequence numbers **Sequence** numbers must be large enough that a retransmitted old packet can never be confu...

## Transport Layer Overview (`systems/networks/4-transport/transport-overview`)

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 0.999 · target 1.000 · placement 0.813 · combined 0.959
  - span: [1559, 1571)
  - context: ...re continuous ordered streams of bytes, and TCP provides them with reliability, **flow control** , and congestion control layered on top of the network's best-effort delivery....

## Domain Name System (DNS) (`systems/networks/5-application/DNS`)

- **DNS** -> Dynamic Host Configuration Protocol (DHCP) (`systems/networks/3-network/DHCP`)
  - scores: naturalness 0.213 · target 1.000 · placement 0.980 · combined 0.579
  - span: [933, 936)
  - context: ...tps://book.systemsapproach.org/ type: textbook --- \#\# Purpose Explain how **DNS** resolves human-readable names into IP addresses at internet scale, and why its...

## Hyper Text Transfer Protocol (HTTP) (`systems/networks/5-application/HTTP`)

- **HTTP** -> Content Delivery Networks (CDNs) (`systems/networks/5-application/CDNs`)
  - scores: naturalness 0.506 · target 0.996 · placement 0.992 · combined 0.785
  - span: [815, 819)
  - context: ...rl: https://book.systemsapproach.org/ type: textbook --- \#\# Purpose Cover **HTTP** as the web's request-response protocol, what a page fetch actually involves, an...

- **HTTP** -> QUIC, HTTP/2, and HTTP/3 (`systems/networks/5-application/quic-http2-http3`)
  - scores: naturalness 0.211 · target 1.000 · placement 0.826 · combined 0.558
  - span: [936, 940)
  - context: ...ol, what a page fetch actually involves, and where the time goes, since most of **HTTP** 's evolution has been about cutting page load time. \#\# Core idea A web page is...

- **HTTP** -> Dynamic Host Configuration Protocol (DHCP) (`systems/networks/3-network/DHCP`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.084 · target 0.998 · placement 0.970 · combined 0.417
  - span: [1038, 1042)
  - context: ...een about cutting page load time. \#\# Core idea A web page is a set of related **HTTP** transactions. Each transaction is a request and a response, carried over TCP, t...

- **JavaScript** -> A Soft Introduction to Java Streams and Lambdas (`software/java/lambdas-and-streams`)
  - scores: naturalness 0.206 · target 0.987 · placement 0.806 · combined 0.548
  - span: [2217, 2227)
  - context: ...Dynamic pages are built on the server per request, or shipped as code, usually **JavaScript** , that runs in the client. \#\# Methods \| Method \| Description \| \| --- \| --- \| \|...

- **load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 0.979 · target 1.000 · placement 0.961 · combined 0.985
  - span: [5405, 5419)
  - context: ...he client. Putting an intermediary between clients and servers also helps with **load balancing** , security, and privacy, and it moves cached data physically closer to clients....

## Application Layer Overview (`systems/networks/5-application/overview`)

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 0.998 · target 1.000 · placement 0.959 · combined 0.991
  - span: [861, 873)
  - context: ...-transport/TCP\|TCP\]\] can transfer arbitrary-length data and get reliability and **flow control** for free. Some applications do not need those guarantees, and some actively can...

## QUIC, HTTP/2, and HTTP/3 (`systems/networks/5-application/quic-http2-http3`)

- **UDP** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.987 · target 1.000 · placement 0.950 · combined 0.985
  - span: [4577, 4580)
  - context: ...9000) is a connection-oriented, encrypted, multiplexed transport that runs over **UDP** . UDP is not the point — it is the deployment vehicle: middleboxes drop or mangl...

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 0.867 · target 0.997 · placement 0.050 · combined 0.522
  - span: [5205, 5217)
  - context: ...sport objects\*\* (§2). A QUIC connection carries many streams, each with its own **flow control** and its own ordering. Loss recovery is per-packet, and data delivery is per-str...

## Networks (`systems/networks/index`)

- **the physical layer** -> The Physical Layer (`systems/networks/0-foundation/2-physical-layer`)
  - scores: naturalness 0.970 · target 1.000 · placement 0.879 · combined 0.964
  - span: [883, 901)
  - context: ...tion/information-theory\|Information theory\]\] explains the capacity bound behind **the physical layer** . \[\[systems/networks/4-transport/TCP\|TCP\]\] and \[\[systems/networks/4-transport/AC...

## Computer Networks, a Systems Approach (`systems/networks/reference`)

- **computer networks, a systems approach** -> Networks (`systems/networks/index`)
  - scores: naturalness 0.641 · target 0.991 · placement 0.050 · combined 0.468
  - span: [489, 526)
  - context: ...url: https://book.systemsapproach.org/ type: textbook --- \#\# Textbook - \[ **computer networks, a systems approach** \](https://book.systemsapproach.org/index.html)

## Socket Reference (`systems/networks/sockets`)

- **reference** -> Reference (`reference/index`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.081 · target 0.956 · placement 0.997 · combined 0.406
  - span: [604, 613)
  - context: ...roach" url: https://book.systemsapproach.org/ type: textbook --- Quick **reference** for the BSD sockets API, with each call shown in C and Python side by side. The...

- **API** -> Syscall API Reference (`systems/operating-systems/v1-kernels-and-processes/3-the-programming-interface`)
  - scores: naturalness 0.782 · target 1.000 · placement 0.981 · combined 0.914
  - span: [634, 637)
  - context: ...ystemsapproach.org/ type: textbook --- Quick reference for the BSD sockets **API** , with each call shown in C and Python side by side. The C signatures follow the...

## Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)

- **In Verilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.650 · target 1.000 · placement 1.000 · combined 0.860
  - span: [2078, 2088)
  - context: ...\| \| \|--+--\| \| GND Access transistors connect to bit lines \`\`\` **In Verilog** , you'd write: \`\`\`verilog module sram \#( parameter ADDR\_WIDTH = 10, // 102...

## Memory Bandwidth Benchmarks (`systems/operating-systems/benchmarks/bandwidth`)

- **memory-bound** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.248 · target 0.952 · placement 0.883 · combined 0.586
  - span: [3687, 3699)
  - context: .../bench bw\_8 1024 \# 8 threads \`\`\` Use arrays of 1 GB or more so the run stays **memory-bound** instead of measuring cache bandwidth. \#\# Sources - \[What Every Programmer Sho...

## Branch Prediction Benchmarks (`systems/operating-systems/benchmarks/branch`)

- **branch misprediction** -> Pipelining, Hazards, and Branch Prediction (`hardware/computer-architecture/pipelining-hazards-branch-prediction`)
  - scores: naturalness 0.385 · target 1.000 · placement 0.992 · combined 0.715
  - span: [654, 674)
  - context: ...g/optimize/microarchitecture.pdf type: docs --- \#\# Purpose Measure what a **branch misprediction** costs on a real workload. Modern CPUs speculatively execute past branches befor...

## False Sharing Benchmarks (`systems/operating-systems/benchmarks/false_sharing`)

- **false sharing** -> Distributed Mutual Exclusion (`systems/distributed-systems/mutual-exclusion`)
  - scores: naturalness 0.744 · target 0.955 · placement 0.764 · combined 0.837
  - span: [1001, 1014)
  - context: ...ads fight over the line even though they never touch each other's data. That is **false sharing** . \#\# Setup The CPU model and compiler flags were not recorded with these resul...

## Software Prefetching Benchmarks (`systems/operating-systems/benchmarks/prefetch`)

- **memory-level** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - scores: naturalness 0.663 · target 1.000 · placement 0.870 · combined 0.842
  - span: [2945, 2957)
  - context: ...gh to cover the DRAM round trip, and the 7.6 ns baseline already reflects heavy **memory-level** parallelism (see \[\[systems/operating-systems/benchmarks/mlp\|memory-level parall...

## Parallel Reductions Benchmarks (`systems/operating-systems/benchmarks/reductions`)

- **memory bandwidth** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - scores: naturalness 0.676 · target 0.975 · placement 0.945 · combined 0.852
  - span: [3292, 3308)
  - context: ...ns 1.3x rather than anything close to 8x. At these sizes the loop is limited by **memory bandwidth** rather than by the add units, so extra ILP has little to push against. SIMD lan...

## Store-to-Load Forwarding Benchmarks (`systems/operating-systems/benchmarks/store_fwd`)

- **store-to-load forwarding** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 0.306 · target 0.938 · placement 0.992 · combined 0.641
  - span: [681, 705)
  - context: ...org/optimize/microarchitecture.pdf type: docs --- \#\# Purpose Measure what **store-to-load forwarding** is worth, and what it costs when it fails. When a load reads an address that wa...

## TLB and Page Walk Benchmarks (`systems/operating-systems/benchmarks/tlb`)

- **paging** -> How the Operating System Handles Page Faults (`systems/operating-systems/lecture-notes/page-faults`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.248 · target 0.999 · placement 0.772 · combined 0.583
  - span: [2623, 2629)
  - context: ...bout Memory\](https://www.akkadia.org/drepper/cpumemory.pdf)) covers the TLB and **paging** structures behind these numbers. The miss penalty stays fixed instead of growi...

## Components of an OS (`systems/operating-systems/lecture-notes/components`)

- **Windows** -> Syscall API Reference (`systems/operating-systems/v1-kernels-and-processes/3-the-programming-interface`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.095 · target 1.000 · placement 0.766 · combined 0.417
  - span: [2125, 2132)
  - context: ...ivers are all examples. The lecture put the count of device drivers written for **Windows** around 35,000. \#\#\# File systems The file system is an abstraction on top of t...

## File Systems (`systems/operating-systems/lecture-notes/file-systems`)

- **files and directories** -> Files and Directories (`systems/operating-systems/v4-persistent-storage/13-files-and-directories`)
  - scores: naturalness 0.980 · target 1.000 · placement 0.937 · combined 0.980
  - span: [688, 709)
  - context: ...tem reads and writes blocks (sectors) on a per-volume basis and turns them into **files and directories** . It is a thick layer of abstraction over the raw storage device. This note cove...

- **the programming interface** -> Syscall API Reference (`systems/operating-systems/v1-kernels-and-processes/3-the-programming-interface`)
  - scores: naturalness 0.988 · target 1.000 · placement 0.863 · combined 0.967
  - span: [792, 817)
  - context: ...t is a thick layer of abstraction over the raw storage device. This note covers **the programming interface** , a couple of behavioral differences between Windows and Unix, the constraints t...

- **file systems** -> File Systems, Introduction and Overview (`systems/operating-systems/v4-persistent-storage/11-file-systems-overview`)
  - scores: naturalness 0.354 · target 1.000 · placement 0.939 · combined 0.686
  - span: [2803, 2815)
  - context: ...es A file is logically a sequence of bytes, plus properties and metadata. Some **file systems** also track a type (regular file, directory, symbolic link, device). Some files...

## Handle Tables (`systems/operating-systems/lecture-notes/handle-tables`)

- **scheduling** -> Uniprocessor Scheduling (`systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.170 · target 1.000 · placement 0.764 · combined 0.509
  - span: [1957, 1967)
  - context: ...and loads it onto the CPU to run. Choosing which process runs next is called \*\* **scheduling** \*\*. The kernel itself has no process of its own; it is a block of code. The CPU...

## I/O Systems and Secondary Storage (`systems/operating-systems/lecture-notes/io-systems-secondary-storage`)

- **SCSI** -> The Multikernel, A new OS architecture for scalable multicore systems (`systems/research/barrelfish`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.181 · target 0.728 · placement 0.783 · combined 0.454
  - span: [1668, 1672)
  - context: ...s. The \*\*PCI\*\* bus is a high speed backbone, and the other buses (\*\*memory\*\*, \*\* **SCSI** \*\*, \*\*USB\*\*, and so on) branch off of it. The I/O system has to cope with a wid...

- **USB** -> Dynamic Host Configuration Protocol (DHCP) (`systems/networks/3-network/DHCP`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.166 · target 0.963 · placement 0.776 · combined 0.498
  - span: [1678, 1681)
  - context: ...CI\*\* bus is a high speed backbone, and the other buses (\*\*memory\*\*, \*\*SCSI\*\*, \*\* **USB** \*\*, and so on) branch off of it. The I/O system has to cope with a wide variety...

- **File** -> File Systems (`systems/operating-systems/lecture-notes/file-systems`)
  - scores: naturalness 0.715 · target 1.000 · placement 0.050 · combined 0.488
  - span: [5227, 5231)
  - context: ...e by disk block number, without knowing the physical location of the block. - \*\* **File** system\*\*: read and write files at a specified offset, block, or byte. Old disk...

## How the Operating System Handles Page Faults (`systems/operating-systems/lecture-notes/page-faults`)

- **paging** -> Virtual Memory and Paging (`systems/operating-systems/lecture-notes/paging`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.138 · target 0.918 · placement 0.879 · combined 0.468
  - span: [743, 749)
  - context: ...through what the OS does when a page fault fires, then covers the two big costs **paging** introduces, extra memory references and page table size, and the structures tha...

## Virtual Memory and Paging (`systems/operating-systems/lecture-notes/paging`)

- **page faults** -> How the Operating System Handles Page Faults (`systems/operating-systems/lecture-notes/page-faults`)
  - scores: naturalness 0.956 · target 1.000 · placement 0.974 · combined 0.979
  - span: [9915, 9926)
  - context: ...ularly bad locality, the working set can get very large. The goal is to reduce **page faults** by keeping each process's working set in memory. \*\*Thrashing\*\* is when a proces...

## Windows Memory Management (`systems/operating-systems/lecture-notes/windows-memory-management`)

- **File systems** -> File Systems (`systems/operating-systems/lecture-notes/file-systems`)
  - scores: naturalness 0.562 · target 1.000 · placement 0.050 · combined 0.449
  - span: [1831, 1843)
  - context: ...\*\*: like modified, except the memory manager is barred from writing it to disk. **File systems** use this to order writes; NTFS holds a page back until the log records covering...

## Objects Handles and Reference Counts (`systems/operating-systems/lecture-notes/windows-objects-handles-refcounts`)

- **handle tables** -> Handle Tables (`systems/operating-systems/lecture-notes/handle-tables`)
  - scores: naturalness 0.974 · target 1.000 · placement 0.779 · combined 0.943
  - span: [1463, 1476)
  - context: ...re. It stops before covering how handles resolve to objects through per-process **handle tables** . \#\# Related notes - \[\[systems/operating-systems/lecture-notes/handle-tables\|h...

## Hard Lessons Learned: Windows RtlZeroMemory (`systems/operating-systems/lecture-notes/windows-rtz`)

- **Windows** -> Syscall API Reference (`systems/operating-systems/v1-kernels-and-processes/3-the-programming-interface`)
  - scores: naturalness 0.441 · target 0.999 · placement 0.873 · combined 0.730
  - span: [645, 652)
  - context: ...lecture --- This is a war story from lecture about two optimizations in early **Windows** that were each fine alone and broke the system together. \#\# The two optimizati...

## What Is an Operating System? (`systems/operating-systems/v1-kernels-and-processes/1-introductions`)

- **File System** -> File Systems (`systems/operating-systems/lecture-notes/file-systems`)
  - scores: naturalness 0.597 · target 1.000 · placement 0.050 · combined 0.459
  - span: [8428, 8439)
  - context: ...services would be written in C and assembly, and would cover the following: - **File System** and Disk IO (read, write, open, close, seek, etc.) - Memory Allocator (malloc,...

- **paging** -> How the Operating System Handles Page Faults (`systems/operating-systems/lecture-notes/page-faults`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.359 · target 0.942 · placement 0.973 · combined 0.676
  - span: [14178, 14184)
  - context: ...ng memory is loaded to disk. The process management service would handle this " **paging** " of memory by keeping a table of processes and the location and metadata for th...

## The Kernel Abstraction (`systems/operating-systems/v1-kernels-and-processes/2-the-kernel-abstraction`)

- **ID** -> Handle Tables (`systems/operating-systems/lecture-notes/handle-tables`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.109 · target 1.000 · placement 0.893 · combined 0.450
  - span: [2296, 2298)
  - context: ...ks each process in a \*\*process control block\*\* (PCB). The PCB holds the process **ID** , the process state, the program counter, the stack pointer, memory management i...

## Concurrency and Threads (`systems/operating-systems/v2-concurrency/4-concurrency-and-threads`)

- **parallelism** -> Memory-Level Parallelism Benchmarks (`systems/operating-systems/benchmarks/mlp`)
  - scores: naturalness 0.540 · target 1.000 · placement 0.762 · combined 0.763
  - span: [1058, 1069)
  - context: ...e OS implements one, and when you would reach for threads versus events or data **parallelism** . \#\# Thread Use Cases - \*\*Program structure: expressing logically concurrent t...

## Multiprocessor Scheduling (`systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling`)

- **Operating Systems** -> Operating Systems (`systems/operating-systems/index`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.075 · target 1.000 · placement 0.962 · combined 0.401
  - span: [1163, 1180)
  - context: ...s --- \#\# Purpose Notes on the multiprocessor scheduling part of chapter 7 of \[ **Operating Systems** : Principles and Practice\](https://ospp.cs.washington.edu/). The uniprocessor po...

- **The** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.088 · target 0.999 · placement 1.000 · combined 0.428
  - span: [4632, 4635)
  - context: ...NUMA balancing moves pages toward their accessors, slowly and heuristically). **The** resulting rule of thumb: migration within a core's SMT siblings is nearly free,...

- **Completely Fair Scheduler** -> Cluster Scheduling and Dominant Resource Fairness (`systems/scheduling/4-cluster-and-datacenter/cluster-scheduling-and-dominant-resource-fairness`)
  - scores: naturalness 0.217 · target 0.910 · placement 0.996 · combined 0.561
  - span: [8407, 8432)
  - context: ...ing, affinity, and NUMA\]\]. \#\# A Real System: Linux CFS and EEVDF Linux's CFS ( **Completely Fair Scheduler** , 2007-2023) is the weighted-fairness thread scheduler of the \[\[systems/operatin...

## Queueing Theory (`systems/operating-systems/v2-concurrency/7-queueing-theory`)

- **queueing theory** -> Queueing Models and Tail Latency (`systems/scheduling/0-foundations/queueing-models-and-tail-latency`)
  - scores: naturalness 0.645 · target 1.000 · placement 0.992 · combined 0.856
  - span: [976, 991)
  - context: ...or\_book/www/book/chapter4/4.7.html type: book --- \#\# Purpose Notes on the **queueing theory** section of chapter 7 of \[Operating Systems: Principles and Practice\](https://os...

## Uniprocessor Scheduling (`systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling`)

- **SJF** -> FIFO, SJF, SRPT, RR, and MLFQ (`systems/scheduling/1-single-resource/fifo-sjf-srpt-rr-and-mlfq`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.101 · target 0.988 · placement 0.986 · combined 0.445
  - span: [4836, 4839)
  - context: ...denial-of-service vector against other users. \#\#\# Sample Bias When measuring **SJF** against other policies, watch for sample bias. If short tasks keep arriving, lo...

- **Python** -> Neural Networks from Scratch (`ml/deep-learning/neural-networks-from-scratch`)
  - scores: naturalness 0.358 · target 0.907 · placement 0.762 · combined 0.633
  - span: [14214, 14220)
  - context: ...erated by a small simulator in the repo venv; the simulator is the ~40 lines of **Python** below.) \| Policy \| A finishes \| B finishes \| C finishes \| Mean response time \|...

## Files and Directories (`systems/operating-systems/v4-persistent-storage/13-files-and-directories`)

- **File systems** -> File Systems (`systems/operating-systems/lecture-notes/file-systems`)
  - scores: naturalness 0.935 · target 1.000 · placement 1.000 · combined 0.977
  - span: [4416, 4428)
  - context: ...which is what the index structure provides a home for. \#\# Files: Finding Data **File systems** usually aim to: - Locate the disk blocks belonging to a file - Maximize sequen...

- **Microsoft Word** -> Operating Systems Reference (`systems/operating-systems/reference`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.161 · target 0.721 · placement 0.785 · combined 0.433
  - span: [6141, 6155)
  - context: ...rson and Dahlin note a FAT-like file system embedded in the .doc format used by **Microsoft Word** from 1997 to 2007. Drawbacks: - Usually poor locality of file data - Poor ran...

## Latency, Throughput, and Utilization (`systems/performance/latency-throughput-and-utilization`)

- **queueing theory** -> Queueing Theory (`systems/operating-systems/v2-concurrency/7-queueing-theory`)
  - scores: naturalness 0.972 · target 1.000 · placement 0.050 · combined 0.544
  - span: [9334, 9349)
  - context: ...mance, ACM Queue\](https://queue.acm.org/detail.cfm?id=1854041) - \[Brewer, CS262 **queueing theory** notes\](https://people.eecs.berkeley.edu/~brewer/cs262/queueing.pdf)

## Streaming Data (`systems/performance/streaming`)

- **memory bandwidth** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - scores: naturalness 0.658 · target 0.993 · placement 0.877 · combined 0.838
  - span: [3299, 3315)
  - context: ...inal, write temporaries, write result). Under an idealized bandwidth model with **memory bandwidth** $B$ (GB/s), the effective rate is approximately $B / (n + 2)$. The upper bound...

- **parallelism** -> Parallelism in LLM Serving Systems (`ml/serving-systems/parallelism`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.092 · target 1.000 · placement 0.980 · combined 0.432
  - span: [8698, 8709)
  - context: ...000$ records/second. The other stages spend most of their time waiting. \*\*Data **parallelism** \*\* runs the complete pipeline on different data chunks. With 8 workers: - Throu...

- **page faults** -> How the Operating System Handles Page Faults (`systems/operating-systems/lecture-notes/page-faults`)
  - scores: naturalness 0.570 · target 1.000 · placement 0.812 · combined 0.788
  - span: [11141, 11152)
  - context: ...fferently. One \`mmap\` call maps the entire file into virtual address space, and **page faults** bring data into memory on demand: \`\`\`c void\* data = mmap(NULL, file\_size, PROT...

- **For** -> Memory-Level Parallelism Benchmarks (`systems/operating-systems/benchmarks/mlp`)
  - scores: naturalness 0.218 · target 1.000 · placement 0.891 · combined 0.573
  - span: [11488, 11491)
  - context: ...system call, but you get cache-line-level granularity after the initial fault. **For** random access patterns this is often optimal. For sequential streaming, \`read\`...

- **file-to-socket** -> Syscall API Reference (`systems/operating-systems/v1-kernels-and-processes/3-the-programming-interface`)
  - scores: naturalness 0.580 · target 1.000 · placement 0.978 · combined 0.823
  - span: [11698, 11712)
  - context: ...l read-ahead more effectively. \#\# Zero-copy: following the data path Standard **file-to-socket** transfer involves multiple copies. Here's the exact path for \`read\` + \`write\`:...

- **Direct ByteBuffers** -> Batching in LLM Serving Systems (`ml/serving-systems/batching`)
  - scores: naturalness 0.608 · target 0.983 · placement 0.875 · combined 0.812
  - span: [15422, 15440)
  - context: ...aphore limits concurrent operations to 100, preventing unbounded task creation. **Direct ByteBuffers** avoid JVM heap allocation and enable potential zero-copy operations. \#\#\# JavaS...

## Cache Line Efficiency Benchmark (`systems/performance/streaming_benchmarks/cache_line_efficiency/README`)

- **Measured** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - scores: naturalness 0.257 · target 1.000 · placement 1.000 · combined 0.621
  - span: [946, 954)
  - context: ...ines you touch and whether the prefetchers can predict the next one. \#\# Setup **Measured** on an Apple laptop with 24 GB of LPDDR5 (Hynix), as reported by \`system\_profile...

- **memory-level parallelism** -> Memory-Level Parallelism Benchmarks (`systems/operating-systems/benchmarks/mlp`)
  - scores: naturalness 0.973 · target 1.000 · placement 0.900 · combined 0.970
  - span: [3160, 3184)
  - context: ...scales with the consumed fraction. seq8 against rand8 isolates prefetching and **memory-level parallelism** : same bytes loaded per line, but the dependent chain in rand8 serializes the mi...

## Tail Latency, Percentiles, and Queueing Distributions (`systems/performance/tail-latency-percentiles`)

- **queueing theory** -> Queueing Theory (`systems/operating-systems/v2-concurrency/7-queueing-theory`)
  - scores: naturalness 0.972 · target 1.000 · placement 0.050 · combined 0.544
  - span: [9322, 9337)
  - context: ...mance, ACM Queue\](https://queue.acm.org/detail.cfm?id=1854041) - \[Brewer, CS262 **queueing theory** notes\](https://people.eecs.berkeley.edu/~brewer/cs262/queueing.pdf)

## Development of the Domain Name System (`systems/research/development-of-the-dns`)

- **DNS** -> Domain Name System (DNS) (`systems/networks/5-application/DNS`)
  - scores: naturalness 0.961 · target 1.000 · placement 0.939 · combined 0.974
  - span: [693, 696)
  - context: ...per --- \#\# Purpose Reading notes on Mockapetris and Dunlap's retrospective on **DNS** . The note walks through the design requirements, the architecture, and the dist...

## Design Philosophy of DARPA Internet Protocols (`systems/research/internet-design-philosophy`)

- **UDP** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.968 · target 1.000 · placement 0.902 · combined 0.969
  - span: [3404, 3407)
  - context: ...s model. IP at the network layer gives all networks a common interface, and TCP/ **UDP** at the transport layer give all applications one. The abstraction hides the det...

- **DPDK** -> Multiple Access (`systems/networks/2-direct-links/multiple-access`)
  - scores: naturalness 0.528 · target 0.941 · placement 0.888 · combined 0.760
  - span: [3735, 3739)
  - context: ...er level for optimization, and the workarounds (ECN, kernel-bypass systems like **DPDK** , with parallels in storage like SPDK and direct access) exist precisely to punc...

- **SPDK** -> Work Stealing, Affinity, and NUMA (`systems/scheduling/2-parallel-and-multiprocessor/work-stealing-affinity-and-numa`)
  - scores: naturalness 0.421 · target 1.000 · placement 0.861 · combined 0.717
  - span: [3772, 3776)
  - context: ...rkarounds (ECN, kernel-bypass systems like DPDK, with parallels in storage like **SPDK** and direct access) exist precisely to punch through the abstraction. And the IP...

## The Locality Principle (`systems/research/locality-principle`)

- **page faults** -> How the Operating System Handles Page Faults (`systems/operating-systems/lecture-notes/page-faults`)
  - scores: naturalness 0.645 · target 1.000 · placement 0.788 · combined 0.818
  - span: [1537, 1548)
  - context: ...program's working set is larger than the physical memory available to it, so it **page faults** repeatedly and throughput collapses. \#\# Main idea Denning recounts the histor...

- **paging** -> Virtual Memory and Paging (`systems/operating-systems/lecture-notes/paging`)
  - scores: naturalness 0.561 · target 0.849 · placement 0.785 · combined 0.723
  - span: [1991, 1997)
  - context: ...eral, and it can be exploited to improve the performance of systems well beyond **paging** , particularly any system that talks to external storage. \#\# Mechanism The wor...

## Accelerating Padded Encoder-Decoder Transformer Models (`systems/research/padded-encoder-decoder`)

- **sequence-to-sequence** -> Natural Language Processing (`ml/nlp/index`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.384 · target 1.000 · placement 0.948 · combined 0.708
  - span: [2027, 2047)
  - context: ...based encoder-decoder models have become the architecture of choice for various **sequence-to-sequence** tasks, including machine translation, text summarization, and automatic speech...

- **batch processing** -> Batching in LLM Serving Systems (`ml/serving-systems/batching`)
  - scores: naturalness 0.221 · target 1.000 · placement 0.951 · combined 0.584
  - span: [2502, 2518)
  - context: ...ess fixed-length inputs (typically 30 seconds of audio) to facilitate efficient **batch processing** . This design choice carries over to the inference stage, where even a short (e....

- **transformer architecture** -> Decoder-Only Transformers (`ml/deep-learning/decoder-only-transformers`)
  - scores: naturalness 0.378 · target 1.000 · placement 0.851 · combined 0.689
  - span: [4348, 4372)
  - context: ...tes the corresponding transcript token by token. The model follows the standard **transformer architecture** with multi-head self-attention mechanisms in both the encoder and decoder, as w...

- **Graph** -> Finding Connected Components in Undirected Graphs Using BFS/DFS (`algorithms/connected-components`)
  - scores: naturalness 0.244 · target 1.000 · placement 0.998 · combined 0.610
  - span: [13613, 13618)
  - context: ...strated significant performance improvements across different audio lengths: !\[ **Graph** showing inference time speedup for different audio lengths\](alt: A line graph s...

- **encoder-decoder transformer** -> Encoder-Decoder Transformers (`ml/deep-learning/encoder-decoder-transformers`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.175 · target 1.000 · placement 0.955 · combined 0.539
  - span: [21443, 21470)
  - context: ...In this work, we addressed the inefficiency of processing padded sequences in **encoder-decoder transformer** models like OpenAI's Whisper. By analyzing attention patterns, we identified th...

- **quantization** -> Quantization in LLM Serving Systems (`ml/serving-systems/quantization`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.178 · target 1.000 · placement 0.874 · combined 0.532
  - span: [22484, 22496)
  - context: ...ficiency of padding tokens, we complement existing optimization techniques like **quantization** and weight pruning. Together, these approaches can significantly reduce the com...

## Faster Causal Self Attention (`systems/research/sparsity-notes`)

- **Automatic Large Language Model** -> Distributed Training of Large Language Models (`ml/serving-systems/distributed-training`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.081 · target 1.000 · placement 0.975 · combined 0.414
  - span: [3527, 3557)
  - context: ...d. \#\# MoA (Mixture of Sparse Attention) \[MoA: Mixture of Sparse Attention for **Automatic Large Language Model** Compression\](https://arxiv.org/abs/2406.14909) starts from the observation that...

## The Unix Timesharing System (`systems/research/unix-timesharing-system`)

- **files and directories** -> Files and Directories (`systems/operating-systems/v4-persistent-storage/13-files-and-directories`)
  - scores: naturalness 0.965 · target 1.000 · placement 0.803 · combined 0.945
  - span: [1433, 1454)
  - context: ...holds an i-node of metadata for each file. Path names don't distinguish between **files and directories** , and a mount table tracks mounted file systems. Buffering is built into the ke...

- **Buffering** -> Handle Tables (`systems/operating-systems/lecture-notes/handle-tables`)
  - scores: naturalness 0.328 · target 1.000 · placement 1.000 · combined 0.677
  - span: [1504, 1513)
  - context: ...between files and directories, and a mount table tracks mounted file systems. **Buffering** is built into the kernel and transparent to the user, with write-behind flushin...

## NUMA-Aware Scheduling and Locality (`systems/scheduling/2-parallel-and-multiprocessor/numa-aware-scheduling-and-locality`)

- **Memory Access): An Overview** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - scores: naturalness 0.517 · target 1.000 · placement 0.050 · combined 0.436
  - span: [10209, 10236)
  - context: ...ng\|False Sharing Benchmarks\]\] \#\# Sources - \[Lameter (2013), NUMA (Non-Uniform **Memory Access): An Overview** , ACM Queue 11(7)\](https://queue.acm.org/detail.cfm?id=2513149) - \[Linux kernel...

## Work Stealing, Affinity, and NUMA (`systems/scheduling/2-parallel-and-multiprocessor/work-stealing-affinity-and-numa`)

- **multiprocessor scheduling** -> Multiprocessor Scheduling (`systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling`)
  - scores: naturalness 0.958 · target 1.000 · placement 0.957 · combined 0.977
  - span: [8948, 8973)
  - context: ...emote-memory penalty if the thread stays but data moves badly That is why real **multiprocessor scheduling** often accepts some load imbalance to preserve locality. \#\# When Work Stealing...

## Fair Queueing, WFQ, and DRR (`systems/scheduling/3-network-and-packet/fair-queueing-wfq-and-drr`)

- **Packet** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 0.306 · target 0.916 · placement 1.000 · combined 0.635
  - span: [876, 882)
  - context: ...url: https://book.systemsapproach.org/ type: textbook --- \#\# Purpose **Packet** scheduling is the cleanest place to see fairness become mathematical. The core...

## Admission Control, Backpressure, and Overload Management (`systems/scheduling/4-cluster-and-datacenter/admission-control-backpressure-overload`)

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 0.975 · target 1.000 · placement 0.926 · combined 0.976
  - span: [7007, 7019)
  - context: ...o the system runs at the bottleneck's pace with bounded buffers everywhere. TCP **flow control** is the canonical form — the receiver's advertised window forces the sender to s...

- **Distributed Systems** -> Distributed Systems (`systems/distributed-systems/index`)
  - scores: naturalness 0.535 · target 1.000 · placement 0.050 · combined 0.441
  - span: [11731, 11750)
  - context: ...ng-failures/) - \[Bronson, Aghayev, Charapko, Zhu (2021), Metastable Failures in **Distributed Systems** , HotOS\](https://sigops.org/s/conferences/hotos/2021/papers/hotos21-s11-bronson....

## Cluster Scheduling and Dominant Resource Fairness (`systems/scheduling/4-cluster-and-datacenter/cluster-scheduling-and-dominant-resource-fairness`)

- **CPU scheduling** -> Uniprocessor Scheduling (`systems/operating-systems/v2-concurrency/7-uniprocessor-scheduling`)
  - scores: naturalness 0.272 · target 0.999 · placement 0.929 · combined 0.624
  - span: [1085, 1099)
  - context: ...pub43438/ type: paper --- \#\# Purpose Cluster scheduling is different from **CPU scheduling** because jobs want vectors of resources, not one scalar quantity. A job may be:...

## Request Scheduling for LLM Serving (`systems/scheduling/5-ml-and-serving/request-scheduling-for-llm-serving`)

- **memory-bandwidth-bound** -> Measuring Real DRAM Latency (`systems/operating-systems/benchmarks/README`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.102 · target 0.995 · placement 0.818 · combined 0.431
  - span: [3463, 3485)
  - context: ...e model plus that request's KV cache\* through memory. Decode alone is therefore **memory-bandwidth-bound** at any realistic batch size, and batching decodes is nearly free in time until...

- **Batching** -> Batching in LLM Serving Systems (`ml/serving-systems/batching`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.125 · target 1.000 · placement 1.000 · combined 0.483
  - span: [4264, 4272)
  - context: ...oblems, coupled through a shared memory budget. \#\# Why Batching Is Scheduling **Batching** is not just throughput optimization. It is the serving scheduler's main control...

- **paging** -> How the Operating System Handles Page Faults (`systems/operating-systems/lecture-notes/page-faults`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.103 · target 1.000 · placement 0.875 · combined 0.439
  - span: [6313, 6319)
  - context: ...but recomputation of a whole prompt is one efficient prefill, often faster than **paging** back in). vLLM preempts newest-first, protecting the requests with the most sun...

## Scheduling (`systems/scheduling/index`)

- **operating systems** -> Operating Systems (`systems/operating-systems/index`)
  - scores: naturalness 0.304 · target 1.000 · placement 0.903 · combined 0.646
  - span: [764, 781)
  - context: ...s section is for scheduling as a systems idea rather than as one chapter inside **operating systems** . The same questions keep reappearing across CPUs, routers, clusters, storage se...

## SWECC Leadership Applications 2025-2026 (`thoughts/leadership/applications`)

- **software engineering** -> Software Engineering (`software/index`)
  - scores: naturalness 0.845 · target 1.000 · placement 0.980 · combined 0.939
  - span: [547, 567)
  - context: ...ment and timeline. \#\# 2025-2026 Officer Applications Are you passionate about **software engineering** and helping others succeed in their careers? Do you want to be part of a team t...

## Abstained

20981 draft(s) were rejected at selection and kept for audit (full records in `inline-proposals.jsonl`):

- below_accept_threshold: 20802
- below_naturalness_floor: 1
- below_single_word_floor: 2
- near_existing_same_target: 57
- over_budget: 8
- overlaps_selected_span: 11
- same_target_note_cap: 100

