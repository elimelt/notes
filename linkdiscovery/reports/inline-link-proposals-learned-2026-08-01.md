# Inline link proposals

- Run: `inline-learned`
- Corpus: `sha256:c9264b9e68933045f077d5d41937a47460aae49d31cbe27c8d3c749dc0316df2`
- Generated: 2026-08-01T09:50:06+00:00
- Accepted: 69 across 43 source note(s)
- Abstained: 21137

## Bipartite Graphs Properties, Proofs, and Detection Algorithm (`algorithms/bipartite-graphs`)

- **Bipartite** -> Introduction to Undirected Graphs and Their Properties (`algorithms/graphs-intro`)
  - scores: naturalness 0.217 · target 1.000 · placement 1.000 · combined 0.585
  - span: [1525, 1534)
  - context: ...style y fill:\#fde8c8,stroke:\#c80 style z fill:\#fde8c8,stroke:\#c80 \`\`\` **Bipartite** structure shows up whenever the vertices naturally split into two kinds, for ex...

## Network Flow Algorithms and Applications in Graph Theory (`algorithms/network-flows`)

- **bipartite graphs** -> Bipartite Graphs Properties, Proofs, and Detection Algorithm (`algorithms/bipartite-graphs`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.142 · target 1.000 · placement 0.798 · combined 0.483
  - span: [7158, 7174)
  - context: ...t yields the minimum vertex cover (this equality of matching and cover sizes in **bipartite graphs** is Konig's theorem). \*\*Proof\*\*: Let $M$ be a maximum matching in $G$, and $f$...

## Experiments and Benchmarking in Computer Architecture (`hardware/computer-architecture/experiments-and-benchmarking`)

- **computer-architecture** -> GPU Architecture from First Principles (`hardware/gpu-architecture`)
  - scores: naturalness 0.506 · target 1.000 · placement 0.945 · combined 0.779
  - span: [975, 996)
  - context: ...you can't trust or reproduce. This note defines a minimal schema for recording **computer-architecture** experiments, whether the evidence is a wall-clock timer, a hardware performance...

- **branch misprediction** -> Branch Prediction Benchmarks (`systems/operating-systems/benchmarks/branch`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.135 · target 1.000 · placement 0.963 · combined 0.493
  - span: [6675, 6695)
  - context: ...dates the qualitative conclusions those notes draw (MLP scaling, TLB miss cost, **branch misprediction** penalty) since the relative comparisons hold regardless of the exact CPU model....

## A Working Map of Computer Architecture (`hardware/computer-architecture/index`)

- **Computer Architecture** -> GPU Architecture from First Principles (`hardware/gpu-architecture`)
  - scores: naturalness 0.283 · target 1.000 · placement 0.970 · combined 0.639
  - span: [877, 898)
  - context: ...ype: source --- \#\# Purpose This is the narrative spine for a university-level **Computer Architecture** I/II treatment, organized as a graph of questions and experiments rather than a...

- **out-of-order
  execution** -> Branch Prediction Benchmarks (`systems/operating-systems/benchmarks/branch`)
  - scores: naturalness 0.549 · target 1.000 · placement 0.050 · combined 0.445
  - span: [3035, 3059)
  - context: ...biguation discussion in \[\[hardware/computer-architecture/out-of-order-execution\| **out-of-order execution** \]\] is the single-core prerequisite for coherence and consistency questions. \#\#...

## Out-of-Order and Superscalar Execution (`hardware/computer-architecture/out-of-order-execution`)

- **hardware** -> GPU Architecture from First Principles (`hardware/gpu-architecture`)
  - scores: naturalness 0.674 · target 1.000 · placement 0.989 · combined 0.869
  - span: [875, 883)
  - context: ...mory.pdf type: paper --- \#\# Purpose A five-stage in-order pipeline (see \[\[ **hardware** /computer-architecture/pipelining-hazards-branch-prediction\|pipelining and hazar...

- **pipelining
and hazards** -> Pipelining, Hazards, and Branch Prediction (`hardware/computer-architecture/pipelining-hazards-branch-prediction`)
  - scores: naturalness 0.585 · target 1.000 · placement 0.969 · combined 0.824
  - span: [943, 965)
  - context: ...line (see \[\[hardware/computer-architecture/pipelining-hazards-branch-prediction\| **pipelining and hazards** \]\]) issues and completes instructions strictly in program order, so one stalled...

- **hardware** -> GPU Architecture from First Principles (`hardware/gpu-architecture`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.113 · target 1.000 · placement 0.844 · combined 0.451
  - span: [6918, 6926)
  - context: ...f-order analog of flushing the pipeline registers in the in-order design from \[\[ **hardware** /computer-architecture/pipelining-hazards-branch-prediction\|pipelining and hazar...

## Pipelining, Hazards, and Branch Prediction (`hardware/computer-architecture/pipelining-hazards-branch-prediction`)

- **ISA,
datapath, and control** -> Instruction Sets, Datapaths, and Control (`hardware/computer-architecture/isa-datapath-control`)
  - scores: naturalness 0.327 · target 1.000 · placement 0.803 · combined 0.648
  - span: [1465, 1491)
  - context: ...n cost. It continues from \[\[hardware/computer-architecture/isa-datapath-control\| **ISA, datapath, and control** \]\] and precedes \[\[hardware/computer-architecture/out-of-order-execution\|out-of-o...

- **hardware** -> GPU Architecture from First Principles (`hardware/gpu-architecture`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.123 · target 1.000 · placement 0.790 · combined 0.459
  - span: [1509, 1517)
  - context: ...r-architecture/isa-datapath-control\|ISA, datapath, and control\]\] and precedes \[\[ **hardware** /computer-architecture/out-of-order-execution\|out-of-order execution\]\], where re...

- **out-of-order
execution** -> Branch Prediction Benchmarks (`systems/operating-systems/benchmarks/branch`)
  - scores: naturalness 0.228 · target 1.000 · placement 0.774 · combined 0.567
  - span: [1563, 1585)
  - context: ...control\]\] and precedes \[\[hardware/computer-architecture/out-of-order-execution\| **out-of-order execution** \]\], where renaming removes most of the hazards derived here. \#\# Five-stage RV32...

## Hardware (`hardware/index`)

- **Signal conditioning** -> C-SWAP: Cost, Size, Weight and Power (`hardware/signal-conditioning/lecture-notes/lecture-1`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.114 · target 1.000 · placement 0.934 · combined 0.462
  - span: [1293, 1312)
  - context: ...ital design is mostly about discrete state, timing closure, and implementation. **Signal conditioning** is about how physical signals get shaped before a digital system can trust them...

## Eigenvalues, Eigenvectors, and Diagonalization (`math/linear-algebra/eigenvalues-eigenvectors-diagonalization`)

- **chapter 5** -> Singular Value Decomposition and the Pseudoinverse (`math/linear-algebra/svd-and-pseudoinverse`)
  - scores: naturalness 0.855 · target 1.000 · placement 0.853 · combined 0.917
  - span: [4898, 4907)
  - context: ...asis, giving the spectral decomposition $A = Q D Q^T$ with $Q$ orthogonal (\[ILA **chapter 5** \](https://textbooks.math.gatech.edu/ila/chap-eigenvalues.html); Strang covers th...

- **reference** -> Python Linear Algebra Cheatsheet (`math/linear-algebra/python-cheatsheet`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.113 · target 1.000 · placement 0.830 · combined 0.449
  - span: [7433, 7442)
  - context: ...bite in practice, per the \[numpy.linalg.eig docs\](https://numpy.org/doc/stable/ **reference** /generated/numpy.linalg.eig.html): - \`eig\` does not sort eigenvalues. Here it h...

## Orthogonality, Projections, and Least Squares (`math/linear-algebra/orthogonality-projections-least-squares`)

- **reference** -> Python Linear Algebra Cheatsheet (`math/linear-algebra/python-cheatsheet`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.108 · target 1.000 · placement 0.973 · combined 0.457
  - span: [7346, 7355)
  - context: ...SVD for exactly this reason. \[numpy.linalg.lstsq\](https://numpy.org/doc/stable/ **reference** /generated/numpy.linalg.lstsq.html) goes one step further and uses an SVD-based...

## Singular Value Decomposition and the Pseudoinverse (`math/linear-algebra/svd-and-pseudoinverse`)

- **reference** -> Python Linear Algebra Cheatsheet (`math/linear-algebra/python-cheatsheet`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.089 · target 1.000 · placement 0.771 · combined 0.407
  - span: [5178, 5187)
  - context: ...truncated pseudoinverse (\[numpy.linalg.lstsq docs\](https://numpy.org/doc/stable/ **reference** /generated/numpy.linalg.lstsq.html)). \> \[!abstract\] SVD, pseudoinverse, and lea...

- **reference** -> Python Linear Algebra Cheatsheet (`math/linear-algebra/python-cheatsheet`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.106 · target 1.000 · placement 0.975 · combined 0.454
  - span: [7892, 7901)
  - context: ...\`\`\` Conventions from the \[numpy.linalg.svd docs\](https://numpy.org/doc/stable/ **reference** /generated/numpy.linalg.svd.html) that trip people up: the function returns \`Vh\`...

## Prompting Language Models (`ml/nlp/prompting`)

- **NLP** -> Natural Language Processing (`ml/nlp/index`)
  - scores: naturalness 0.778 · target 1.000 · placement 0.050 · combined 0.503
  - span: [6101, 6104)
  - context: ...- \[Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive **NLP** Tasks\](https://arxiv.org/abs/2005.11401) - \[Liu et al. (2023), Lost in the Midd...

## Bias, Marketplace Effects, and Counterfactual Evaluation (`ml/recommender-systems/bias-and-marketplace-effects`)

- **Recommendation** -> Ranking Objectives and Implicit Feedback (`ml/recommender-systems/ranking-objectives`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.144 · target 1.000 · placement 0.945 · combined 0.502
  - span: [2954, 2968)
  - context: ...ogenize behavior without increasing utility. That is the mental model to keep. **Recommendation** logs are not a random sample from user preference. They are a sample filtered b...

- **Yahoo! Front Page** -> Practical Lessons from Predicting Clicks on Ads at Facebook (`ml/recommender-systems/predicting-clicks-on-ads-at-facebook`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.173 · target 0.999 · placement 0.891 · combined 0.529
  - span: [4157, 4174)
  - context: ...dation and report a \*\*12.5% click lift\*\* over a context-free bandit baseline on **Yahoo! Front Page** traffic. The paper also makes a second contribution that matters just as much:...

## Practical Lessons from Predicting Clicks on Ads at Facebook (`ml/recommender-systems/predicting-clicks-on-ads-at-facebook`)

- **Facebook ads CTR** -> Bias, Marketplace Effects, and Counterfactual Evaluation (`ml/recommender-systems/bias-and-marketplace-effects`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.135 · target 0.999 · placement 0.964 · combined 0.492
  - span: [853, 869)
  - context: ...rpose This note records the main modeling and systems lessons from He et al.'s **Facebook ads CTR** paper. The paper is worth reading because it is not just a model comparison. It...

## Retrieval and Ranking (`ml/recommender-systems/retrieval-and-ranking`)

- **CTR** -> Practical Lessons from Predicting Clicks on Ads at Facebook (`ml/recommender-systems/predicting-clicks-on-ads-at-facebook`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.092 · target 1.000 · placement 0.968 · combined 0.431
  - span: [8342, 8345)
  - context: ...efine calibration for ad click prediction as the ratio of the average predicted **CTR** to the average empirical CTR, with 1.0 being perfect. The reason this matters b...

- **CTR** -> Practical Lessons from Predicting Clicks on Ads at Facebook (`ml/recommender-systems/predicting-clicks-on-ads-at-facebook`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.088 · target 1.000 · placement 0.854 · combined 0.414
  - span: [8666, 8669)
  - context: ...t the price the winner pays. A budget pacer divides a spend target by predicted **CTR** to decide how aggressively to bid. A content quality gate might filter out anyt...

- **Reordering Documents** -> Recommender Systems (`ml/recommender-systems/recommender-systems`)
  - scores: naturalness 0.901 · target 1.000 · placement 0.050 · combined 0.530
  - span: [15873, 15893)
  - context: ...\[Carbonell and Goldstein (1998), The Use of MMR, Diversity-Based Reranking for **Reordering Documents** and Producing Summaries\](https://www.cs.cmu.edu/~jgc/publication/MMR\_DiversityB...

## Electric Circuit Analysis (`reference/cheatsheets/circuits/electricity`)

- **Potential** -> Resistance (`hardware/signal-conditioning/lecture-notes/lecture-3`)
  - scores: naturalness 0.409 · target 1.000 · placement 0.998 · combined 0.731
  - span: [875, 884)
  - context: ...y carry negative charge and drift the other way, from low potential to high. \*\* **Potential** \*\* is the energy per unit charge at a point in space. It's measured in volts, an...

## Patterns for Scalability and Reliability in Systems (`reference/slides/system-design`)

- **system-design** -> Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)
  - scores: naturalness 0.231 · target 1.000 · placement 0.922 · combined 0.589
  - span: [489, 502)
  - context: ...ources: - original slide deck --- This note condenses a slide deck on common **system-design** patterns for scaling and reliability into a scrollable Quartz-friendly referenc...

- **Scalability Patterns** -> Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)
  - scores: naturalness 0.676 · target 1.000 · placement 0.050 · combined 0.479
  - span: [630, 650)
  - context: ...ollable Quartz-friendly reference. \#\# Agenda 1. Client Server Architecture 2. **Scalability Patterns** 3. Limitations 4. Extending Client Server Architecture 5. Availability/Reliabil...

- **Limitations** -> Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)
  - scores: naturalness 0.532 · target 1.000 · placement 0.050 · combined 0.440
  - span: [654, 665)
  - context: ...reference. \#\# Agenda 1. Client Server Architecture 2. Scalability Patterns 3. **Limitations** 4. Extending Client Server Architecture 5. Availability/Reliability Patterns 6....

- **sharding** -> Sharding (`systems/distributed-systems/sharding`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.081 · target 1.000 · placement 0.852 · combined 0.401
  - span: [1743, 1751)
  - context: ...ate a \*partition key\* to determine which shard to write to. !\[w:900p\](./assets/ **sharding** .png) --- \#\# Scalability Patterns \#\#\# 3. Queueing Problem: My system is over...

## System Design Interviews (`reference/slides/system-design-interviews`)

- **App** -> Scaling Web Services with Distributed Architectures (`systems/distributed-systems/scaling-web-services`)
  - scores: naturalness 0.511 · target 0.992 · placement 0.050 · combined 0.433
  - span: [3566, 3569)
  - context: ...how data flows between components - e.g. Client → Load balancer → Web server → **App** server → Database Specify communication patterns - e.g. Synchronous API calls,...

- **Database** -> Databases and Data-Intensive Systems (`systems/databases/index`)
  - scores: naturalness 0.638 · target 1.000 · placement 0.050 · combined 0.469
  - span: [3579, 3587)
  - context: ...ws between components - e.g. Client → Load balancer → Web server → App server → **Database** Specify communication patterns - e.g. Synchronous API calls, asynchronous messa...

- **Discuss** -> Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)
  - scores: naturalness 0.228 · target 1.000 · placement 1.000 · combined 0.596
  - span: [4530, 4537)
  - context: ...solutions for each bottleneck - e.g. Add read replicas, implement caching layer **Discuss** single points of failure - e.g. Load balancer failover strategy with leader-fol...

- **Handle** -> Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)
  - scores: naturalness 0.533 · target 1.000 · placement 1.000 · combined 0.802
  - span: [4629, 4635)
  - context: ...ts of failure - e.g. Load balancer failover strategy with leader-follower setup **Handle** edge cases - e.g. URL collision resolution, handling expired URLs --- \#\# Form...

## Replication Strategies in Distributed Data Systems (`systems/databases/distributed-data/ch5-replication`)

- **Designing** -> Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.157 · target 1.000 · placement 0.973 · combined 0.520
  - span: [942, 951)
  - context: ...pers/OSDI04.pdf type: paper --- \#\# Purpose Reading notes on chapter 5 of \[ **Designing** Data-Intensive Applications\](https://dataintensive.net/) by Martin Kleppmann, f...

## Scalable Distributed Data Systems (`systems/databases/distributed-data/preface`)

- **Designing** -> Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.081 · target 1.000 · placement 0.956 · combined 0.411
  - span: [699, 708)
  - context: ...net/ type: book --- \#\# Purpose Reading notes on the preface to part 2 of \[ **Designing** Data-Intensive Applications\](https://dataintensive.net/) by Martin Kleppmann. I...

## Data Models and Relationships in Database Systems (`systems/databases/foundations/ch2-data-models-and-query-languages`)

- **Designing** -> Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)
  - scores: naturalness 0.252 · target 1.000 · placement 0.970 · combined 0.614
  - span: [801, 810)
  - context: ...taintensive.net/ type: book --- \#\# Purpose Reading notes on chapter 2 of \[ **Designing** Data-Intensive Applications\](https://dataintensive.net/) by Martin Kleppmann. T...

## Query Planning and Join Execution (`systems/databases/query-planning-and-joins`)

- **cost-model** -> Performance Modeling for LLM Serving Systems (`ml/serving-systems/performance-modeling`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.115 · target 1.000 · placement 0.815 · combined 0.450
  - span: [6435, 6445)
  - context: ..., even a crude cost model picked good plans, so \*\*cardinality quality dominates **cost-model** quality\*\*. The practical mitigations are unglamorous: multi-column statistics (...

## Bigtable, A Distributed Storage System for Structured Data (`systems/distributed-systems/bigtable`)

- **Bigtable** -> Scalable Distributed Data Systems (`systems/databases/distributed-data/preface`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.084 · target 1.000 · placement 0.989 · combined 0.419
  - span: [684, 692)
  - context: .../en//archive/bigtable-osdi06.pdf type: paper --- \#\# Purpose Notes on the \[ **Bigtable** paper\](https://static.googleusercontent.com/media/research.google.com/en//archi...

- **bigtable** -> Scalable Distributed Data Systems (`systems/databases/distributed-data/preface`)
  - scores: naturalness 0.260 · target 1.000 · placement 0.914 · combined 0.613
  - span: [775, 783)
  - context: ...per\](https://static.googleusercontent.com/media/research.google.com/en//archive/ **bigtable** -osdi06.pdf). I care about the data model, how tablets get located and assigned,...

## Distributed Cache Coherence (`systems/distributed-systems/distributed-cache-coherence`)

- **DNS** -> Domain Name System (DNS) (`systems/networks/5-application/DNS`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.111 · target 1.000 · placement 0.798 · combined 0.443
  - span: [871, 874)
  - context: ...is worth understanding exactly what they cost, because most large systems (NFS, **DNS** , most of the web) deliberately pay for less. \#\# Core idea When linearizabilit...

## Failure Detectors, Leases, and Leader Election (`systems/distributed-systems/failure-detectors-leases-leader-election`)

- **Gray** -> Software Engineering (`software/index`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.083 · target 0.926 · placement 0.996 · combined 0.403
  - span: [4541, 4545)
  - context: ...e traversing it cheap. \#\# Leases: authority with an expiry date A \*\*lease\*\* (\[ **Gray** and Cheriton 1989\](https://dl.acm.org/doi/10.1145/74850.74870)) is a grant of a...

## Managing Critical State (`systems/distributed-systems/managing-critical-state`)

- **publish-subscribe** -> Non-Blocking Two Phase Commit (`systems/distributed-systems/non-blocking-two-phase-commit`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.100 · target 0.983 · placement 0.962 · combined 0.440
  - span: [8816, 8833)
  - context: ...when that node dies. Queuing also generalizes into \*\*atomic broadcast\*\* and \*\* **publish-subscribe** \*\* systems, where messages must be reliably delivered to multiple nodes, useful...

## Systems (`systems/index`)

- **Performance** -> Performance Modeling for LLM Serving Systems (`ml/serving-systems/performance-modeling`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.090 · target 1.000 · placement 0.777 · combined 0.410
  - span: [1411, 1422)
  - context: ...source scheduling. Distributed systems reuse ideas from networking and storage. **Performance** work cuts across all of it. \#\# Sections - \[\[systems/operating-systems/index\|O...

## Socket Reference (`systems/networks/sockets`)

- **Computer Networks** -> Computer Networks, a Systems Approach (`systems/networks/reference`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.142 · target 1.000 · placement 0.865 · combined 0.491
  - span: [850, 867)
  - context: ...es/man2/socket.2.html), and the full client and server at the bottom come from \[ **Computer Networks** : A Systems Approach\](https://book.systemsapproach.org/). For what TCP and UDP d...

## Components of an OS (`systems/operating-systems/lecture-notes/components`)

- **scheduling** -> Cluster Scheduling and Dominant Resource Fairness (`systems/scheduling/4-cluster-and-datacenter/cluster-scheduling-and-dominant-resource-fairness`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.159 · target 1.000 · placement 0.792 · combined 0.502
  - span: [4083, 4093)
  - context: ...nt, memory management, and I/O. Higher level services (file system, networking, **scheduling** policy) run as user-space server processes. The isolation between components b...

## Operating Systems Reference (`systems/operating-systems/reference`)

- **memory management** -> Memory Management in LLM Serving Systems (`ml/serving-systems/memory-management`)
  - scores: naturalness 0.839 · target 0.981 · placement 0.050 · combined 0.512
  - span: [921, 938)
  - context: ..., concurrency\](https://www.kea.nu/files/textbooks/ospp/osppv2.pdf) - \[volume 3, **memory management** \](https://www.kea.nu/files/textbooks/ospp/osppv3.pdf) - \[volume 4, persistent st...

## What Is an Operating System? (`systems/operating-systems/v1-kernels-and-processes/1-introductions`)

- **MTTR** -> S’more Blondies (`thoughts/recipe/smore-brownie`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.103 · target 1.000 · placement 0.799 · combined 0.432
  - span: [2295, 2299)
  - context: ..., is influenced by \*\*Mean Time To Failure\*\* (MTTF) and \*\*Mean Time To Repair\*\* ( **MTTR** ). Increasing MTTF and decreasing MTTR increases availability. \*\*Security.\*\* Pr...

- **Virtualization** -> The Multikernel, A new OS architecture for scalable multicore systems (`systems/research/barrelfish`)
  - scores: naturalness 0.210 · target 1.000 · placement 0.906 · combined 0.568
  - span: [4310, 4324)
  - context: ...mes difficult, and developers often need to stop the system to inspect state. \*\* **Virtualization** \*\* helps by creating the illusion of multiple processors on one processor. This...

- **As** -> Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.080 · target 0.985 · placement 1.000 · combined 0.410
  - span: [17137, 17139)
  - context: ...ng reliability, security, portability, performance, and adoption? Explain why. **As** a user of a MacBook Pro, security, performance, and adoption are extremely impo...

## Latency, Throughput, and Utilization (`systems/performance/latency-throughput-and-utilization`)

- **queueing theory** -> Queueing Theory (`systems/operating-systems/v2-concurrency/7-queueing-theory`)
  - scores: naturalness 0.863 · target 1.000 · placement 0.050 · combined 0.522
  - span: [9334, 9349)
  - context: ...mance, ACM Queue\](https://queue.acm.org/detail.cfm?id=1854041) - \[Brewer, CS262 **queueing theory** notes\](https://people.eecs.berkeley.edu/~brewer/cs262/queueing.pdf)

## Streaming Data (`systems/performance/streaming`)

- **MB** -> Memory Bandwidth Benchmarks (`systems/operating-systems/benchmarks/bandwidth`)
  - scores: naturalness 0.902 · target 1.000 · placement 0.050 · combined 0.530
  - span: [5900, 5902)
  - context: ...s its page size differently: - \*\*Parquet\*\*: Pages are row groups (\[default 128 **MB** uncompressed\](https://parquet.apache.org/docs/)) - \*\*CSV\*\*: Pages are lines or...

## Tail Latency, Percentiles, and Queueing Distributions (`systems/performance/tail-latency-percentiles`)

- **queueing theory** -> Queueing Theory (`systems/operating-systems/v2-concurrency/7-queueing-theory`)
  - scores: naturalness 0.579 · target 1.000 · placement 0.050 · combined 0.454
  - span: [9322, 9337)
  - context: ...mance, ACM Queue\](https://queue.acm.org/detail.cfm?id=1854041) - \[Brewer, CS262 **queueing theory** notes\](https://people.eecs.berkeley.edu/~brewer/cs262/queueing.pdf)

## The Multikernel, A new OS architecture for scalable multicore systems (`systems/research/barrelfish`)

- **barrelfish** -> Exokernel: An Operating System Architecture for Application-Level Resource Management (`systems/research/exokernel`)
  - scores: naturalness 0.861 · target 0.963 · placement 0.050 · combined 0.512
  - span: [1080, 1090)
  - context: ...for scalable multicore systems\](https://people.inf.ethz.ch/troscoe/pubs/sosp09- **barrelfish** .pdf), Baumann et al., SOSP 2009. \#\# Problem Traditional OS architectures scal...

- **barrelfish** -> How to write a fast kernel (`ml/serving-systems/how-to-write-a-fast-kernel`)
  - scores: naturalness 0.692 · target 1.000 · placement 0.050 · combined 0.483
  - span: [5122, 5132)
  - context: ...for scalable multicore systems\](https://people.inf.ethz.ch/troscoe/pubs/sosp09- **barrelfish** .pdf) \#\# Related notes - \[\[systems/research/exokernel\|Exokernel\]\] - \[\[systems/...

## Power Provisioning for a Warehouse-sized Computer (`systems/research/data-center-power-provisioning`)

- **Websearch, Webmail, MapReduce** -> Batch Processing Systems and MapReduce Fundamentals (`systems/databases/derived-data/ch10-batch-processing`)
  - scores: naturalness 0.204 · target 1.000 · placement 0.920 · combined 0.564
  - span: [1896, 1925)
  - context: ...r usage across large-scale workloads at Google, covering three major workloads ( **Websearch, Webmail, MapReduce** ) plus a real mixed-use datacenter. They found consistent underutilization of pr...

## Development of the Domain Name System (`systems/research/development-of-the-dns`)

- **DNS** -> Domain Name System (DNS) (`systems/networks/5-application/DNS`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.135 · target 1.000 · placement 0.939 · combined 0.490
  - span: [693, 696)
  - context: ...per --- \#\# Purpose Reading notes on Mockapetris and Dunlap's retrospective on **DNS** . The note walks through the design requirements, the architecture, and the dist...

- **dns** -> Domain Name System (DNS) (`systems/networks/5-application/DNS`)
  - scores: naturalness 0.799 · target 1.000 · placement 0.050 · combined 0.508
  - span: [994, 997)
  - context: ...omain Name System\](https://courses.cs.washington.edu/courses/cse551/09sp/papers/ **dns** .pdf), Mockapetris and Dunlap, SIGCOMM 1988. \#\# Problem The original solution...

- **The** -> Domain Name System (DNS) (`systems/networks/5-application/DNS`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.091 · target 1.000 · placement 0.931 · combined 0.426
  - span: [2110, 2113)
  - context: ...The name server is the repository of name-to-data mappings and answers queries. **The** resolver is the interface client programs use to query name servers. The line b...

- **Every** -> Domain Name System (DNS) (`systems/networks/5-application/DNS`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.080 · target 1.000 · placement 1.000 · combined 0.413
  - span: [4177, 4182)
  - context: ...rved from its own zone data (rather than cache) as authoritative. \#\#\# Caching **Every** RR has a TTL in seconds, the maximum time a resolver may reuse the cached recor...

## End-to-End Arguments in System Design (`systems/research/end-to-end-arguments-in-sys-design`)

- **End-to-End Arguments in System Design** -> Information Theory in Networks (`systems/networks/0-foundation/information-theory`)
  - scores: naturalness 0.627 · target 0.976 · placement 0.050 · combined 0.461
  - span: [3042, 3079)
  - context: ...ossy links where end-to-end retransmission would cost far more. \#\# Sources - \[ **End-to-End Arguments in System Design** \](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf) \#\# Relate...

## Hints for Computer System Design (`systems/research/hints-for-computer-system-design`)

- **Hints for Computer System Design** -> Patterns for Scalability and Reliability in Systems (`reference/slides/system-design`)
  - scores: naturalness 0.506 · target 0.930 · placement 0.050 · combined 0.419
  - span: [868, 900)
  - context: ...on generalizes further than the usual presentation of caching. \#\# Citation - \[ **Hints for Computer System Design** \](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/acrobat-17...

## Design Philosophy of DARPA Internet Protocols (`systems/research/internet-design-philosophy`)

- **The Design Philosophy** -> Fundamentals of Data-Intensive Application Design and Scalability (`systems/databases/foundations/ch1-reliable-scalable-and-maintainable-applications`)
  - scores: naturalness 0.491 · target 1.000 · placement 0.050 · combined 0.428
  - span: [4958, 4979)
  - context: ...stem-design-an-introduction-spring-2009/pages/online-textbook/) \#\# Sources - \[ **The Design Philosophy** of the DARPA Internet Protocols\](http://ccr.sigcomm.org/archive/1995/jan95/ccr-...

## The Locality Principle (`systems/research/locality-principle`)

- **The Locality Principle** -> Hints for Computer System Design (`systems/research/hints-for-computer-system-design`)
  - scores: naturalness 0.468 · target 0.926 · placement 0.050 · combined 0.407
  - span: [1049, 1071)
  - context: ...linked the wrong PDF; the sources above are the correct ones. \#\# Citation - \[ **The Locality Principle** \](https://dl.acm.org/doi/10.1145/1070838.1070856), Peter J. Denning, Communicati...

## Accelerating Padded Encoder-Decoder Transformer Models (`systems/research/padded-encoder-decoder`)

- **Performance** -> Performance Modeling for LLM Serving Systems (`ml/serving-systems/performance-modeling`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.169 · target 1.000 · placement 0.998 · combined 0.536
  - span: [16182, 16193)
  - context: ...rmance We also evaluated our approach on resource-constrained edge devices: !\[ **Performance** on edge devices\](alt: A bar chart showing inference times on a Jetson Nano for...

## Admission Control, Backpressure, and Overload Management (`systems/scheduling/4-cluster-and-datacenter/admission-control-backpressure-overload`)

- **cascading-failures** -> Stragglers, Speculation, and Overload (`systems/scheduling/4-cluster-and-datacenter/stragglers-speculation-and-overload`)
  - scores: naturalness 0.207 · target 0.995 · placement 0.913 · combined 0.564
  - span: [6332, 6350)
  - context: ...equests at the bottom exactly when the bottom is least able to serve them. The \[ **cascading-failures** chapter's\](https://sre.google/sre-book/addressing-cascading-failures/) discipli...

## Cluster Scheduling and Dominant Resource Fairness (`systems/scheduling/4-cluster-and-datacenter/cluster-scheduling-and-dominant-resource-fairness`)

- **GB** -> Memory Bandwidth Benchmarks (`systems/operating-systems/benchmarks/bandwidth`)
  - scores: naturalness 0.562 · target 0.378 · placement 0.762 · combined 0.500
  - span: [3389, 3391)
  - context: ...); user A's tasks need (1 CPU, 4 GB) — memory-dominant; user B's need (3 CPU, 1 **GB** ) — CPU-dominant: \| step \| granted to \| A tasks \| A dom. share \| B tasks \| B do...

- **GB** -> Memory Bandwidth Benchmarks (`systems/operating-systems/benchmarks/bandwidth`)
  - FLAG: suggest a better anchor — the target looks correct but the anchor scored below the naturalness floor (spec §6 Q25); review the wording rather than auto-linking.
  - scores: naturalness 0.082 · target 1.000 · placement 0.969 · combined 0.414
  - span: [3845, 3847)
  - context: ...0.667 \| 2 \| 0.667 \| 9/9 \| 14/18 \| Final allocation: A gets 3 tasks (3 CPU, 12 **GB** ), B gets 2 tasks (6 CPU, 2 GB), dominant shares equal at $2/3$, and the cluster...

- **GB** -> S’more Blondies (`thoughts/recipe/smore-brownie`)
  - scores: naturalness 0.597 · target 0.212 · placement 0.948 · combined 0.411
  - span: [3875, 3877)
  - context: ...18 \| Final allocation: A gets 3 tasks (3 CPU, 12 GB), B gets 2 tasks (6 CPU, 2 **GB** ), dominant shares equal at $2/3$, and the cluster's CPU is exhausted — no furth...

## Abstained

21137 draft(s) were rejected at selection and kept for audit (full records in `inline-proposals.jsonl`):

- below_accept_threshold: 21135
- over_budget: 2

