---
title: MVCC and Snapshot Isolation
category: Database Systems
tags:
  - mvcc
  - snapshot isolation
  - concurrency control
  - versioning
  - garbage collection
date: 2026-08-01
status: draft
description: Multiversion concurrency control as a mechanism, covering version chains and visibility rules, PostgreSQL's xmin/xmax implementation, why snapshot isolation is not serializability, SSI, and the garbage-collection tax every design pays.
sources:
  - title: Neumann, Muhlbauer, Kemper (2015), Fast Serializable MVCC for Main-Memory Database Systems
    url: https://db.in.tum.de/~muehlbau/papers/mvcc.pdf
    type: paper
  - title: PostgreSQL docs, Concurrency Control (MVCC)
    url: https://www.postgresql.org/docs/current/mvcc-intro.html
    type: docs
  - title: Kleppmann, Designing Data-Intensive Applications, chapter 7
    url: https://dataintensive.net/
    type: book
  - title: Wu et al. (2017), An Empirical Evaluation of In-Memory Multi-Version Concurrency Control
    url: https://www.vldb.org/pvldb/vol10/p781-wu.pdf
    type: paper
---

## Purpose

Multiversion concurrency control is the mechanism behind the isolation levels most databases actually run, and it deserves its own note rather than a paragraph inside [[systems/databases/transactions-serializability-isolation|Transactions, Serializability, and Isolation Levels]]. The core trade: writers create new versions instead of overwriting, so readers get a consistent snapshot without taking locks — in the [PostgreSQL docs' phrasing](https://www.postgresql.org/docs/current/mvcc-intro.html), "reading never blocks writing and writing never blocks reading." The price is version storage, visibility checks on every read, and a garbage-collection obligation that never goes away.

## Versions and visibility

Every MVCC design answers three questions: where do old versions live, how does a reader decide which version to see, and when can a version be reclaimed.

**Version chains.** Each logical row is a chain of physical versions, ordered either newest-to-oldest (readers of current data stop at the head; the common OLTP choice) or oldest-to-newest. Storage falls into three families ([Wu et al. 2017](https://www.vldb.org/pvldb/vol10/p781-wu.pdf)): append-only (every version is a full tuple in the main store — PostgreSQL), delta/undo storage (newest version in place, older versions reconstructed from undo records — Oracle, InnoDB, HyPer), and time-travel (full old versions moved to a separate area). Delta storage makes writes cheap and keeps the main store compact but taxes readers of old snapshots with reconstruction; append-only is the reverse.

**Visibility.** Versions are stamped with the transaction IDs that created and (logically) deleted them. A transaction's snapshot is defined by which transaction IDs had committed when the snapshot was taken; a version is visible if its creator committed before the snapshot and its deleter (if any) did not. Concretely in PostgreSQL, every heap tuple carries hidden columns `xmin` (creating XID) and `xmax` (deleting/updating XID, or 0), and a snapshot is the triple (oldest running XID, next XID, list of in-progress XIDs); the visibility check is a comparison of the tuple's `xmin`/`xmax` against that triple. An `UPDATE` is a delete plus insert: it sets `xmax` on the old version and writes a new tuple with fresh `xmin`, leaving both in the heap.

**Reclamation.** A version is garbage once no live snapshot can see it — its deleter committed before the oldest snapshot still running. This single rule generates most operational MVCC pain, below.

## Snapshot isolation, precisely

Under snapshot isolation, a transaction reads entirely from its start-of-transaction snapshot, and concurrent transactions may not both write the same item: the **first-committer-wins** rule (or first-updater-wins with row locks) aborts the loser of a write-write overlap. This buys a lot: dirty reads, fuzzy reads, read skew, and lost updates are all excluded, since reads are frozen in time and conflicting writes cannot both commit.

What it does not buy is serializability, and the counterexample is worth internalizing. The on-call doctors case ([Kleppmann ch. 7](https://dataintensive.net/), after Cahill): a hospital requires at least one doctor on call. Alice and Bob are both on call. Each runs: read the roster (snapshot shows two on call), verify "someone else is still on"), set *own* row to off-call, commit. The write sets are disjoint — Alice writes Alice's row, Bob writes Bob's — so first-committer-wins fires on nothing, both commit, and zero doctors are on call. Each transaction was correct serially; the interleaving is the **write skew** anomaly A5B from [[systems/databases/transactions-serializability-isolation|the transactions note]]. The read of the snapshot went stale in exactly the dimension the other transaction wrote. SI also permits a subtler read-only anomaly (Fekete et al. 2004): a read-only transaction can observe a state inconsistent with any serial order of the other two.

The fix without giving up MVCC is **serializable snapshot isolation** (Cahill, Röhm, Fekete 2008): every SI anomaly requires a transaction with both an inbound and an outbound read-write antidependency (it read something a concurrent transaction wrote, and something it read was overwritten by another). Track antidependencies at runtime and abort one participant whenever that dangerous structure forms. The test is conservative — false-positive aborts happen — but never admits a real anomaly. PostgreSQL's SERIALIZABLE has been SSI since 9.1, implemented with non-blocking SIREAD predicate locks; the application contract is that any transaction may fail with a serialization error and must be retried.

## An engine sketch

A minimal in-memory MVCC storage engine, following [HyPer's design](https://db.in.tum.de/~muehlbau/papers/mvcc.pdf) (delta storage, newest-to-oldest):

```text
main store:   row slots hold the NEWEST version in place
              slot -> [value | version-pointer]

undo buffers: per-transaction append-only buffers of before-images
              entry: (slot, old value, creator XID, next-pointer)

write(txn, slot, v):
    acquire slot for txn (abort other writer: first-updater-wins)
    append (slot, current value, txn.id) to txn.undo
    link entry at head of slot's version chain; store v in place

read(txn, slot):
    v = in-place value; e = chain head
    while e exists and e.creator not visible to txn.snapshot:
        v = e.old_value; e = e.next        (walk back in time)
    return v

commit(txn):  stamp txn.undo entries with commit timestamp
abort(txn):   replay txn.undo in reverse onto the main store
```

The pleasant property: transactions that only touch current data never walk a chain, so the single-version fast path stays fast, and versions exist only for recently changed rows. HyPer reports the whole apparatus — including SSI-style serializability validation via precision locking — costs roughly 20% versus its single-version baseline on TPC-C while still exceeding 100k transactions/s, against roughly 5x degradation for 2PL in the same system ([Neumann et al. 2015](https://db.in.tum.de/~muehlbau/papers/mvcc.pdf), §4). Their conclusion is quotable: with MVCC this cheap, "there is little need to prefer SI over full serializability any longer."

## MVCC versus lock-based designs

- **Reads.** MVCC readers take no locks and never block, which is the whole point; analytics can run against a snapshot while OLTP writes proceed. Under 2PL, one long reader stalls every writer that touches its read set.
- **Writes.** Comparable per-write cost (version creation vs. lock acquisition), but MVCC writers never wait for readers. Write-write conflicts abort rather than block, shifting cost to retries under contention.
- **Storage and GC.** The structural downside. A lock-based single-version engine updates in place and is done; MVCC accumulates dead versions that some background process must find and reclaim — VACUUM in PostgreSQL, purge in InnoDB, epoch-based reclamation in in-memory engines. [Wu et al.](https://www.vldb.org/pvldb/vol10/p781-wu.pdf) found GC to be the dominant scalability factor across in-memory MVCC designs.
- **Long-running transactions.** The GC rule makes every design hostage to its oldest snapshot: one forgotten `idle in transaction` session or day-long analytics query pins the reclamation horizon, and dead versions pile up in every table, regardless of which tables the old transaction touched.

PostgreSQL makes the operational consequences concrete. Dead tuples live in the heap until VACUUM removes them, so update-heavy tables bloat under an old snapshot. And because XIDs are 32-bit, VACUUM must also **freeze** old tuples (mark them visible-to-all) before the counter wraps around after about two billion transactions — an unvacuumable table eventually forces the system into a protective shutdown mode. The [routine-vacuuming docs](https://www.postgresql.org/docs/current/routine-vacuuming.html) treat this as a first-class operational duty, which is the honest framing: MVCC moves concurrency cost out of the lock manager and into storage maintenance.

## Related notes

- [[systems/databases/transactions-serializability-isolation|Transactions, Serializability, and Isolation Levels]]
- [[systems/databases/foundations/ch3-storage-and-retrieval|Storage and Retrieval]]
- [[systems/distributed-systems/bigtable|Bigtable]]
- [[systems/distributed-systems/consistency|Consistency]]

## Sources

- [Neumann, Muhlbauer, Kemper (2015), Fast Serializable Multi-Version Concurrency Control for Main-Memory Database Systems](https://db.in.tum.de/~muehlbau/papers/mvcc.pdf)
- [PostgreSQL docs: MVCC introduction](https://www.postgresql.org/docs/current/mvcc-intro.html), [transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html), [routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- [Kleppmann, Designing Data-Intensive Applications, ch. 7](https://dataintensive.net/)
- [Wu, Arulraj, Lin, Xian, Pavlo (2017), An Empirical Evaluation of In-Memory Multi-Version Concurrency Control](https://www.vldb.org/pvldb/vol10/p781-wu.pdf)
- [Cahill, Röhm, Fekete (2008), Serializable Isolation for Snapshot Databases](https://dl.acm.org/doi/10.1145/1376616.1376690)
