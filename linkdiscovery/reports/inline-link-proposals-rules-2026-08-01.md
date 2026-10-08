# Inline link proposals

- Run: `inline-baseline`
- Corpus: `sha256:1e78346f593363cdc686623ede1407775b1d1081f200f8c52394700e51aadba8`
- Generated: 2026-08-01T19:48:57+00:00
- Accepted: 45 across 42 source note(s)
- Abstained: 1925

## Problem Set 4 Notes (`algorithms/practice/4`)

- **connected components** -> Finding Connected Components in Undirected Graphs Using BFS/DFS (`algorithms/connected-components`)
  - scores: naturalness 0.700 · target 0.479 · placement 0.949 · combined 0.683
  - span: [7439, 7459)
  - context: ...$p\_1$ may or may not be $v$). Cutting $T\_2$ on $f$ to get $T\_2'$, we have two **connected components** $K\_1$, $K\_2$, both of which are trees. Now, we can add $e$ to $T\_2'$, and by (1...

## Graphs and Trees Problem Notes (`algorithms/problems/graphs-and-trees`)

- **graph theory** -> Graph Theory (`reference/cheatsheets/algorithms/graphs`)
  - scores: naturalness 1.000 · target 0.423 · placement 0.965 · combined 0.742
  - span: [426, 438)
  - context: ...eton.edu/~wayne/kleinberg-tardos/ --- \#\# Purpose Work through a pair of short **graph theory** exercises. The first is a full \[\[algorithms/induction\|inductive proof\]\]. The se...

## A Working Map of Computer Architecture (`hardware/computer-architecture/index`)

- **SystemVerilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.509 · target 0.650 · placement 0.857 · combined 0.657
  - span: [1542, 1555)
  - context: ...predictors, out-of-order machinery), the microarchitecture is described in RTL ( **SystemVerilog** , Chisel), and RTL becomes gates through synthesis. Measurement runs the other d...

## Interconnects, NoCs, DMA, and Memory Controllers (`hardware/computer-architecture/interconnects-noc-dma`)

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 1.000 · target 0.423 · placement 0.883 · combined 0.720
  - span: [5585, 5597)
  - context: ...eing re-arbitrated every cycle. This is a basic form of \*\*virtual cut-through\*\* **flow control** — a whole packet is either granted the resource or not, rather than being inter...

## Instruction Sets, Datapaths, and Control (`hardware/computer-architecture/isa-datapath-control`)

- **SystemVerilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.509 · target 0.650 · placement 0.894 · combined 0.667
  - span: [1277, 1290)
  - context: ...different styles: \[CVA6\](https://github.com/openhwgroup/cva6) as a hand-written **SystemVerilog** single-issue pipeline, \[Rocket\](https://github.com/chipsalliance/rocket-chip) a...

## Out-of-Order and Superscalar Execution (`hardware/computer-architecture/out-of-order-execution`)

- **pipelining
and hazards** -> Pipelining, Hazards, and Branch Prediction (`hardware/computer-architecture/pipelining-hazards-branch-prediction`)
  - scores: naturalness 0.700 · target 0.501 · placement 0.969 · combined 0.698
  - span: [943, 965)
  - context: ...line (see \[\[hardware/computer-architecture/pipelining-hazards-branch-prediction\| **pipelining and hazards** \]\]) issues and completes instructions strictly in program order, so one stalled...

## Open-Source CPU RTL Reading Lab (`hardware/computer-architecture/rtl-reading-lab`)

- **SystemVerilog** -> SystemVerilog (`hardware/digital-design/369/system-verilog`)
  - scores: naturalness 0.509 · target 0.650 · placement 0.970 · combined 0.685
  - span: [2867, 2880)
  - context: ...8075606\` \| Ibex and Rocket both target small in-order cores but differ in HDL ( **SystemVerilog** vs. Chisel). BOOM is explicitly "Berkeley Out-of-Order Machine," built as an Oo...

## Algorithmic State Machines (`hardware/digital-design/371/algorithmic-state-machines`)

- **combinational logic** -> Combinational Logic (`hardware/digital-design/369/combinational-logic`)
  - scores: naturalness 0.819 · target 0.650 · placement 0.846 · combined 0.766
  - span: [2916, 2935)
  - context: ...diate data (the variables), the datapath implements every register operation as **combinational logic** attached to register inputs, and a control FSM sequences the register operation...

## Static Timing Analysis (`hardware/digital-design/371/static-timing-analysis`)

- **combinational logic** -> Combinational Logic (`hardware/digital-design/369/combinational-logic`)
  - scores: naturalness 0.819 · target 0.650 · placement 0.897 · combined 0.782
  - span: [2446, 2465)
  - context: ...ou find the longest. The canonical path runs from a launching register through **combinational logic** to a capturing register, with both registers on the same clock: \`\`\`mermaid flo...

## GPU Architecture from First Principles (`hardware/gpu-architecture`)

- **combinational logic** -> Combinational Logic (`hardware/digital-design/369/combinational-logic`)
  - scores: naturalness 0.819 · target 0.650 · placement 0.858 · combined 0.770
  - span: [7178, 7197)
  - context: ...e RTL substrate above: fetching and decoding an instruction costs registers and **combinational logic** regardless of how many lanes execute it, so amortizing that cost over 32 lanes...

## Distributed Training of Large Language Models (`ml/serving-systems/distributed-training`)

- **Sharding** -> Sharding (`systems/distributed-systems/sharding`)
  - scores: naturalness 0.529 · target 0.650 · placement 0.953 · combined 0.689
  - span: [4671, 4679)
  - context: ...than two H100-80GB GPUs' worth of memory before a single activation is stored. **Sharding** this state across $N\_d$ data-parallel workers with ZeRO stage 3 (or equivalentl...

## GPU Architecture and Programming (`ml/serving-systems/gpu-basics`)

- **Memory management** -> Memory Management in LLM Serving Systems (`ml/serving-systems/memory-management`)
  - scores: naturalness 0.700 · target 0.506 · placement 1.000 · combined 0.708
  - span: [8489, 8506)
  - context: ...ping to hardware, highest performance ceiling, heaviest implementation burden. **Memory management** : \`\`\`cpp // Memory allocation cudaMalloc // device memory allocation c...

## GPU Kernel Programming with Triton and CUDA (`ml/serving-systems/triton`)

- **Memory management** -> Memory Management in LLM Serving Systems (`ml/serving-systems/memory-management`)
  - scores: naturalness 0.700 · target 0.506 · placement 1.000 · combined 0.708
  - span: [3091, 3108)
  - context: ...shes. \#\# CUDA CUDA gives the same program with every decision made manually. **Memory management** is explicit: \`cudaMalloc\`, \`cudaFree\`, and \`cudaMallocHost\` for pinned host mem...

## Electric Circuit Analysis (`reference/cheatsheets/circuits/electricity`)

- **Resistance** -> Resistance (`hardware/signal-conditioning/lecture-notes/lecture-3`)
  - scores: naturalness 0.461 · target 0.650 · placement 0.998 · combined 0.669
  - span: [1535, 1545)
  - context: ...It's measured in amperes (A, Amp), a compound unit of charge per unit time. \*\* **Resistance** \*\* is the opposition to the flow of electricity. It's measured in ohms ($\\Omega$...

## Batch Processing Systems and MapReduce Fundamentals (`systems/databases/derived-data/ch10-batch-processing`)

- **Google File System** -> Google File System (GFS) Overview (`systems/distributed-systems/google-file-system`)
  - scores: naturalness 0.700 · target 0.536 · placement 0.837 · combined 0.680
  - span: [3254, 3272)
  - context: ...ng access, optimized for throughput over latency, and follows the design of the **Google File System** . It differs from an object store like Amazon S3 in that computation runs on the...

## Bigtable, A Distributed Storage System for Structured Data (`systems/distributed-systems/bigtable`)

- **load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.906 · combined 0.838
  - span: [2274, 2288)
  - context: ...amically partitioned into ranges called \*tablets\*, the unit of distribution and **load balancing** . Reads over short row ranges therefore touch only a few machines. Users should...

## Google File System (GFS) Overview (`systems/distributed-systems/google-file-system`)

- **file systems** -> File Systems (`systems/operating-systems/lecture-notes/file-systems`)
  - scores: naturalness 0.724 · target 0.650 · placement 0.930 · combined 0.759
  - span: [1067, 1079)
  - context: ...tributed-systems/bigtable\|Bigtable\]\]. \#\# Problem GFS departs from traditional **file systems** because Google's workload departs from traditional workloads: - It runs on com...

- **load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.767 · combined 0.793
  - span: [6837, 6851)
  - context: ...at enables garbage collection, re-replication after failures, and migration for **load balancing** . The obvious objection is that memory bounds the filesystem's size. In practic...

## Managing Critical State (`systems/distributed-systems/managing-critical-state`)

- **distributed systems** -> Distributed Systems (`systems/distributed-systems/index`)
  - scores: naturalness 0.467 · target 0.650 · placement 0.951 · combined 0.661
  - span: [6868, 6887)
  - context: ...tributed storage systems often order operations by timestamp, and this fails in **distributed systems** because of clock drift. Google's Spanner attacks the timestamp uncertainty head...

## Sharding (`systems/distributed-systems/sharding`)

- **Load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.912 · combined 0.840
  - span: [2563, 2577)
  - context: ...-\> server address\` on every client, with many more table entries than servers. **Load balancing** then becomes table assignment: give fewer entries to servers whose entries hold...

## Systems (`systems/index`)

- **load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.902 · combined 0.837
  - span: [1229, 1243)
  - context: ...nch because the same policy questions show up in CPU runtimes, packet handling, **load balancing** , and model serving. Networking and operating systems meet in queues, interrupts...

## Network Components and Protocols (`systems/networks/0-foundation/1-network-components-and-protocols`)

- **the global internet** -> The Global Internet (`systems/networks/3-network/global-internet`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.789 · combined 0.800
  - span: [2711, 2730)
  - context: ...you get an \*\*internetwork\*\*, or \*\*internet\*\*. The Internet with a capital I is **the global internet** . \#\#\# Switched networks \*\*Switched networks\*\* forward messages node to node un...

- **UDP** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.457 · target 0.650 · placement 0.944 · combined 0.654
  - span: [4821, 4824)
  - context: ...------------\> Y \<- (peers) (comm using Y) \`\`\` Examples of protocols: TCP, **UDP** , HTTP, FTP, SMTP, POP3, IMAP, DNS, DHCP, ARP, ICMP, IP, Ethernet, WiFi, Bluetoo...

## Error Detection and Correction (`systems/networks/2-direct-links/errors`)

- **the physical layer** -> The Physical Layer (`systems/networks/0-foundation/2-physical-layer`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.969 · combined 0.857
  - span: [7441, 7459)
  - context: ...are rare and retransmission is cheap. In practice, error correction dominates **the physical layer** , where LDPC codes appear in 802.11, DVB, and WiMAX, and convolutional codes are...

## Framing in Network Protocols (`systems/networks/2-direct-links/framing`)

- **The physical layer** -> The Physical Layer (`systems/networks/0-foundation/2-physical-layer`)
  - scores: naturalness 1.000 · target 0.650 · placement 1.000 · combined 0.866
  - span: [611, 629)
  - context: ...url: https://book.systemsapproach.org/ type: textbook --- \#\# Purpose **The physical layer** delivers a stream of bits. The link layer has to know where each frame starts a...

## Dynamic Host Configuration Protocol (DHCP) (`systems/networks/3-network/DHCP`)

- **UDP** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.457 · target 0.650 · placement 0.972 · combined 0.661
  - span: [1192, 1195)
  - context: ...es, and DHCP is the protocol that manages the assignments. DHCP runs on top of **UDP** , with the server on port 67 and the client on port 68. It has to work before th...

## The Global Internet (`systems/networks/3-network/global-internet`)

- **switched ethernet** -> Switched Ethernet (`systems/networks/2-direct-links/switching`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.888 · combined 0.833
  - span: [1060, 1077)
  - context: ...hing the internet through a single IP address (NAT in home networks) or through **switched ethernet** in an enterprise LAN. Service providers build the infrastructure and route traf...

## Routing (`systems/networks/3-network/routing`)

- **UDP** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.457 · target 0.650 · placement 0.941 · combined 0.654
  - span: [6818, 6821)
  - context: ...numNewRoutes; ++i) mergeRoute(&newRoute\[i\]); \} \`\`\` Actual RIP runs on **UDP** port 520, and its messages carry a list of route entries: \`\`\`text RIP Message:...

## UDP (`systems/networks/4-transport/UDP`)

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.827 · combined 0.813
  - span: [1023, 1035)
  - context: ...nothing else. There is no connection setup, no ordering, no retransmission, no **flow control** , and no congestion control. A datagram either arrives once, arrives duplicated,...

## Transport Layer Overview (`systems/networks/4-transport/transport-overview`)

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.813 · combined 0.808
  - span: [1559, 1571)
  - context: ...re continuous ordered streams of bytes, and TCP provides them with reliability, **flow control** , and congestion control layered on top of the network's best-effort delivery....

## Hyper Text Transfer Protocol (HTTP) (`systems/networks/5-application/HTTP`)

- **load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.961 · combined 0.855
  - span: [5405, 5419)
  - context: ...he client. Putting an intermediary between clients and servers also helps with **load balancing** , security, and privacy, and it moves cached data physically closer to clients....

## Application Layer Overview (`systems/networks/5-application/overview`)

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.959 · combined 0.854
  - span: [861, 873)
  - context: ...-transport/TCP\|TCP\]\] can transfer arbitrary-length data and get reliability and **flow control** for free. Some applications do not need those guarantees, and some actively can...

## QUIC, HTTP/2, and HTTP/3 (`systems/networks/5-application/quic-http2-http3`)

- **UDP** -> UDP (`systems/networks/4-transport/UDP`)
  - scores: naturalness 0.457 · target 0.650 · placement 0.950 · combined 0.656
  - span: [4577, 4580)
  - context: ...9000) is a connection-oriented, encrypted, multiplexed transport that runs over **UDP** . UDP is not the point — it is the deployment vehicle: middleboxes drop or mangl...

## Networks (`systems/networks/index`)

- **the physical layer** -> The Physical Layer (`systems/networks/0-foundation/2-physical-layer`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.879 · combined 0.830
  - span: [883, 901)
  - context: ...tion/information-theory\|Information theory\]\] explains the capacity bound behind **the physical layer** . \[\[systems/networks/4-transport/TCP\|TCP\]\] and \[\[systems/networks/4-transport/AC...

## File Systems (`systems/operating-systems/lecture-notes/file-systems`)

- **files and directories** -> Files and Directories (`systems/operating-systems/v4-persistent-storage/13-files-and-directories`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.937 · combined 0.848
  - span: [688, 709)
  - context: ...tem reads and writes blocks (sectors) on a per-volume basis and turns them into **files and directories** . It is a thick layer of abstraction over the raw storage device. This note cove...

- **the programming interface** -> Syscall API Reference (`systems/operating-systems/v1-kernels-and-processes/3-the-programming-interface`)
  - scores: naturalness 0.700 · target 0.470 · placement 0.863 · combined 0.657
  - span: [792, 817)
  - context: ...t is a thick layer of abstraction over the raw storage device. This note covers **the programming interface** , a couple of behavioral differences between Windows and Unix, the constraints t...

## Virtual Memory and Paging (`systems/operating-systems/lecture-notes/paging`)

- **page faults** -> How the Operating System Handles Page Faults (`systems/operating-systems/lecture-notes/page-faults`)
  - scores: naturalness 0.700 · target 0.463 · placement 0.974 · combined 0.681
  - span: [9915, 9926)
  - context: ...ularly bad locality, the working set can get very large. The goal is to reduce **page faults** by keeping each process's working set in memory. \*\*Thrashing\*\* is when a proces...

## Objects Handles and Reference Counts (`systems/operating-systems/lecture-notes/windows-objects-handles-refcounts`)

- **handle tables** -> Handle Tables (`systems/operating-systems/lecture-notes/handle-tables`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.779 · combined 0.797
  - span: [1463, 1476)
  - context: ...re. It stops before covering how handles resolve to objects through per-process **handle tables** . \#\# Related notes - \[\[systems/operating-systems/lecture-notes/handle-tables\|h...

## Multiprocessor Scheduling (`systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling`)

- **load balancing** -> Load Balancing (`systems/distributed-systems/load-balancing`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.817 · combined 0.810
  - span: [4870, 4884)
  - context: ...pensive and \*persistently\* so. That hierarchy is precisely how Linux structures **load balancing** (below): rebalance eagerly at small distances, reluctantly at large ones. \*\*Wh...

## Files and Directories (`systems/operating-systems/v4-persistent-storage/13-files-and-directories`)

- **File systems** -> File Systems (`systems/operating-systems/lecture-notes/file-systems`)
  - scores: naturalness 0.724 · target 0.650 · placement 1.000 · combined 0.778
  - span: [4416, 4428)
  - context: ...which is what the index structure provides a home for. \#\# Files: Finding Data **File systems** usually aim to: - Locate the disk blocks belonging to a file - Maximize sequen...

## Cache Line Efficiency Benchmark (`systems/performance/streaming_benchmarks/cache_line_efficiency/README`)

- **memory-level parallelism** -> Memory-Level Parallelism Benchmarks (`systems/operating-systems/benchmarks/mlp`)
  - scores: naturalness 0.700 · target 0.571 · placement 0.900 · combined 0.711
  - span: [3160, 3184)
  - context: ...scales with the consumed fraction. seq8 against rand8 isolates prefetching and **memory-level parallelism** : same bytes loaded per line, but the dependent chain in rand8 serializes the mi...

## Exokernel: An Operating System Architecture for Application-Level Resource Management (`systems/research/exokernel`)

- **kernel abstractions** -> Hardware Modes (`systems/operating-systems/lecture-notes/kernel-abstraction`)
  - scores: naturalness 0.700 · target 0.453 · placement 0.988 · combined 0.679
  - span: [3102, 3121)
  - context: ...style XK fill:\#e3f2fd,stroke:\#1565c0 \`\`\` \#\# Why this helps General-purpose **kernel abstractions** carry overhead in two ways. First, resources are so thoroughly abstracted that...

## The Unix Timesharing System (`systems/research/unix-timesharing-system`)

- **files and directories** -> Files and Directories (`systems/operating-systems/v4-persistent-storage/13-files-and-directories`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.803 · combined 0.805
  - span: [1433, 1454)
  - context: ...holds an i-node of metadata for each file. Path names don't distinguish between **files and directories** , and a mount table tracks mounted file systems. Buffering is built into the ke...

## Work Stealing, Affinity, and NUMA (`systems/scheduling/2-parallel-and-multiprocessor/work-stealing-affinity-and-numa`)

- **multiprocessor scheduling** -> Multiprocessor Scheduling (`systems/operating-systems/v2-concurrency/7-multiprocessor-scheduling`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.957 · combined 0.854
  - span: [8948, 8973)
  - context: ...emote-memory penalty if the thread stays but data moves badly That is why real **multiprocessor scheduling** often accepts some load imbalance to preserve locality. \#\# When Work Stealing...

## Admission Control, Backpressure, and Overload Management (`systems/scheduling/4-cluster-and-datacenter/admission-control-backpressure-overload`)

- **flow control** -> Flow Control (`systems/networks/4-transport/flow-control`)
  - scores: naturalness 1.000 · target 0.650 · placement 0.926 · combined 0.844
  - span: [7007, 7019)
  - context: ...o the system runs at the bottleneck's pace with bounded buffers everywhere. TCP **flow control** is the canonical form — the receiver's advertised window forces the sender to s...

## Abstained

1925 draft(s) were rejected at selection and kept for audit (full records in `inline-proposals.jsonl`):

- below_accept_threshold: 1902
- below_single_word_floor: 2
- near_existing_same_target: 11
- same_target_note_cap: 10

