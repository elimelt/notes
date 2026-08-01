---
title: Transactions, Serializability, and Isolation Levels
category: Database Systems
tags:
  - transactions
  - serializability
  - isolation levels
  - concurrency control
  - correctness
date: 2026-08-01
status: draft
description: What transactions guarantee, the concrete anomaly schedules isolation levels exclude, why the ANSI definitions are broken, conflict serializability and 2PL, and what real databases actually give you at each level.
sources:
  - title: Berenson et al. (1995), A Critique of ANSI SQL Isolation Levels
    url: https://arxiv.org/abs/cs/0701157
    type: paper
  - title: Kleppmann, Designing Data-Intensive Applications, chapter 7
    url: https://dataintensive.net/
    type: book
  - title: Bernstein, Hadzilacos, and Goodman (1987), Concurrency Control and Recovery in Database Systems
    url: https://www.microsoft.com/en-us/research/people/philbe/book/
    type: book
---

## Purpose

The transaction-processing foundation for the database branch: what a transaction promises, exactly which interleavings each isolation level rules out, and the theory (conflict serializability, two-phase locking) that makes "serializable" a checkable property rather than a slogan. Anomalies are given as concrete schedules, in the notation of the [Critique paper](https://arxiv.org/abs/cs/0701157): $r_1[x]$ means transaction 1 reads $x$, $w_1[x]$ writes it, $c_1$ commits, $a_1$ aborts. The mechanism that dominates practice, multiversioning, is covered in [[systems/databases/mvcc-snapshot-isolation|MVCC and Snapshot Isolation]].

## ACID, briefly and skeptically

A transaction groups reads and writes into a unit that commits or aborts atomically. The ACID mnemonic: atomicity (all-or-nothing on abort or crash), consistency (application invariants preserved — a property of the application's transactions, not something the database can supply), isolation (concurrent transactions do not interfere), durability (committed data survives crashes). [Kleppmann](https://dataintensive.net/) is blunt that the terms are used loosely enough that "ACID" is closer to marketing than specification; the substantive engineering lives in what *isolation* means.

## The anomaly zoo, as schedules

Isolation levels are defined by which of these interleavings they exclude. Prose definitions are ambiguous — that ambiguity is the subject of the Critique paper — so here are the schedules ([Berenson et al. 1995](https://arxiv.org/abs/cs/0701157), §3):

**P0, dirty write.** $w_1[x] \ldots w_2[x] \ldots (c_1 \text{ or } a_1)$. T2 overwrites uncommitted data. If T1 then aborts, what should $x$ roll back to? Every real system excludes this at every level.

**P1, dirty read.** $w_1[x] \ldots r_2[x] \ldots (a_1, c_2)$. T2 read a value that never existed in any committed state. Example: T1 transfers 40 between two accounts; T2 reads one account before the transfer and one after, seeing money in flight.

**P2, fuzzy (non-repeatable) read.** $r_1[x] \ldots w_2[x] \ldots c_2 \ldots r_1[x]$. T1 reads $x$ twice and gets different answers.

**P3, phantom.** $r_1[P] \ldots w_2[y \in P] \ldots c_2 \ldots r_1[P]$. T1 evaluates a predicate ("employees with salary > 100k"); T2 inserts a row matching it; T1 re-evaluates and sees a row that appeared mid-transaction. The difference from P2: the conflict is on a *predicate*, not an existing item, so item-level locks cannot prevent it.

**P4, lost update.** $r_1[x] \ldots w_2[x] \ldots w_1[x] \ldots c_1$. Both transactions do read-modify-write on a counter starting at 100: T1 computes 100+10, T2 computes and commits 100+20, then T1 writes 110. T2's update vanished.

**A5A, read skew.** $r_1[x] \ldots w_2[x] \ldots w_2[y] \ldots c_2 \ldots r_1[y]$. T1 reads $x$ before T2's update and $y$ after it: a non-atomic view across two items related by an invariant (e.g., $x + y = 100$).

**A5B, write skew.** $r_1[x] \ldots r_2[y] \ldots w_1[y] \ldots w_2[x] \ldots (c_1, c_2)$. Each transaction reads a constraint involving both items and writes the *other* item. Neither writes what the other wrote, so no write-write conflict exists, yet the combined effect can violate an invariant that each transaction individually checked. This is the anomaly snapshot isolation famously permits; the worked example is in [[systems/databases/mvcc-snapshot-isolation|MVCC and Snapshot Isolation]].

The paper distinguishes broad interpretations (P, the pattern *could* cause an anomaly) from strict ones (A, the anomaly actually materialized in the committed history), and shows the ANSI standard's English wording only pins down the strict readings — which is too weak. Locking implementations exclude the broad patterns.

## Isolation levels as exclusion sets

The ANSI SQL levels, defined by which phenomena they exclude ([Critique](https://arxiv.org/abs/cs/0701157), Table 3, using the corrected broad interpretations; P0 is excluded everywhere):

| Level | P1 dirty read | P2 fuzzy read | P3 phantom | P4 lost update | A5B write skew |
| --- | --- | --- | --- | --- | --- |
| Read uncommitted | possible | possible | possible | possible | possible |
| Read committed | excluded | possible | possible | possible | possible |
| Repeatable read | excluded | excluded | possible | excluded | excluded |
| Snapshot isolation | excluded | excluded | mostly excluded | excluded | **possible** |
| Serializable | excluded | excluded | excluded | excluded | excluded |

The Critique's central results: the ANSI definitions read strictly are so weak that a system could claim serializability while permitting real anomalies, and **snapshot isolation does not fit the ladder at all** — it excludes everything read committed and repeatable read exclude, plus most phantoms, yet still allows write skew, so it is neither above nor below repeatable read. Oracle shipped SI under the name "serializable" for decades, which the paper politely documents.

## Serializability theory

A schedule (interleaving of committed transactions' operations) is **serializable** if it is equivalent to some serial execution. The tractable version is **conflict serializability**: two operations conflict if they are from different transactions, touch the same item, and at least one writes. A schedule is conflict serializable iff its precedence graph — nodes are transactions, with an edge $T_i \to T_j$ whenever an operation of $T_i$ conflicts with and precedes one of $T_j$ — is acyclic ([Bernstein, Hadzilacos, Goodman](https://www.microsoft.com/en-us/research/people/philbe/book/), ch. 2). Acyclic means a topological order exists, and that order is the equivalent serial schedule. Checking the lost-update schedule above: $r_1[x] w_2[x]$ gives $T_1 \to T_2$, and $w_2[x] w_1[x]$ gives $T_2 \to T_1$ — a cycle, hence not serializable, which is the formal version of "the update got lost."

## Mechanisms

**Two-phase locking.** Each transaction acquires shared locks to read and exclusive locks to write, and once it releases any lock it may acquire no more (growing phase, then shrinking phase). The 2PL theorem: any 2PL execution is conflict serializable — the lock point (moment of holding all locks) gives the serial order. Practice uses **strict 2PL**, holding all locks to commit, which additionally prevents cascading aborts: no one reads or overwrites data whose writer might still roll back. Phantoms need more than item locks, because the conflict is with rows that do not exist yet; real systems lock index ranges (next-key locking in InnoDB) as a practical approximation of predicate locks.

**Optimistic concurrency control.** Run without locks against a private workspace, then validate at commit: if a concurrent committed transaction wrote anything this one read, abort and retry. Wins when conflicts are rare (aborts cost less than lock overhead and blocking); loses under contention, where wasted work compounds.

**Serializable snapshot isolation.** The modern middle ground: run under snapshot isolation, track read-write antidependencies at runtime, and abort a transaction when the dangerous double-antidependency structure appears (Cahill et al. 2008). PostgreSQL's SERIALIZABLE level has worked this way since 9.1 — details in [[systems/databases/mvcc-snapshot-isolation|MVCC and Snapshot Isolation]].

## What databases actually give you

The names on the knob and the semantics behind it diverge enough to be a recurring source of production bugs:

| System | Default | "Repeatable read" is | "Serializable" is |
| --- | --- | --- | --- |
| PostgreSQL | read committed | snapshot isolation | SSI (true serializability) |
| MySQL/InnoDB | repeatable read | MVCC snapshot reads + next-key locks | strict 2PL |
| Oracle | read committed | (not offered) | snapshot isolation |
| SQL Server | read committed (locking) | 2PL-based | strict 2PL + range locks |

Two takeaways. Defaults are weak: read committed permits lost updates, read skew, and write skew, so any read-modify-write needs `SELECT ... FOR UPDATE`, an atomic update statement, or a stronger level. And names lie: Oracle's serializable is SI (write skew possible), PostgreSQL's repeatable read is SI (stronger than ANSI repeatable read for phantoms, but it will not detect write skew either).

## Related notes

- [[systems/databases/mvcc-snapshot-isolation|MVCC and Snapshot Isolation]]
- [[systems/distributed-systems/consistency|Consistency]]
- [[systems/distributed-systems/non-blocking-two-phase-commit|Non-Blocking Two-Phase Commit]]
- [[systems/databases/foundations/ch3-storage-and-retrieval|Storage and Retrieval]]

## Sources

- [Berenson, Bernstein, Gray, Melton, O'Neil, O'Neil (1995), A Critique of ANSI SQL Isolation Levels](https://arxiv.org/abs/cs/0701157)
- [Kleppmann, Designing Data-Intensive Applications, ch. 7](https://dataintensive.net/)
- [Bernstein, Hadzilacos, Goodman (1987), Concurrency Control and Recovery in Database Systems](https://www.microsoft.com/en-us/research/people/philbe/book/)
- [Cahill, Röhm, Fekete (2008), Serializable Isolation for Snapshot Databases](https://dl.acm.org/doi/10.1145/1376616.1376690)
- [PostgreSQL docs, Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [MySQL 8.4 docs, InnoDB Transaction Isolation Levels](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)
