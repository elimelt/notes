# Clocks

There are two main approaches to time in a distributed system: **physical clocks** and **virtual (logical) clocks**.

## Physical Clocks

Actual clocks running in most computers drift apart by ~30 ppm due to their temperature sensitivity. Although more accurate clocks (atomic, GPS, etc.) are available, they are expensive and are only *maybe* present in some data centers.

The crux of the problem is that physical clocks are not perfectly synchronized, and the sending of messages between processes can introduce unpredictable delays. In general, network latency is unpredictable, but with a lower bound.

A practical, albeit naive approach might be to use NTP and have clients query a set of time servers. Then, take the minimum (or some average, subtracting outliers) of the readings received. This can synchronize to ~50 microseconds in a LAN.

Such a system was implemented with **Google Huygens**. Some interesting optimizations they added include:

- Time-stamping packets in the NIC to avoid OS scheduling overhead
- Only included evenly-spaced packets in their sampling as a heuristic for no queuing delay
- Estimate relative clock phase and drift between pairs
- Sample pairs and use linear algebra to correct peer-to-peer clock skew

This enabled them to achieve a 50 ns clock skew 99% of the time. This is okay if time is only used as a hint, but shows that even with all of the above optimizations, it isn't good enough.

To drive this point home, due to the massive scale Google operates at (1 billion RPCs/sec = 10 million clock skews above 50ns per sec), even for a minimum sized message that takes 2 ns to send in a high-performance network, thousands of instructions can be executed on a single server's processor.

## Virtual Clocks

We want to design systems such that the ordering of events that can be concurrently executed **doesn't** matter, and the ordering of events that must be performed sequentially is enforced on all possible executions.

Virtual clocks are a framework for reasoning about the order of events using **no** assumptions about physical clock skew or message delays in way way that both respects causality, and relies only on local information.

### Happens before

We say that event `a` **happens before** event `b` if:

1. `a` happens earlier than `b` in the same process
2. `a` is the sending of a message and `b` is the receipt of that message
3. `a` happens before `c` and `c` happens before `b`, aka transitivity

This is a **partial order**.

### Happens concurrently

Two events `a` and `b` are said to happen concurrently if neither `a` happens before `b` nor `b` happens before `a`.

### Logical Clock Implementation

- Keep a local clock $T$, and increment it whenever an event happens.
- On all messages sent, include a timestamp $T_m$.
- On receipt of a message, set $T = \max(T, T_m) + 1$.

### Vector Clocks

Note that with the above implementation of a logic clock system, it was not the case that $T(a) < T(b) \to $ $a$ happened before $b$. With vector clocks, we have $T(a) < T(b) \leftrightarrow a$ happened before $b$ by precisely representing transitive causal relationships between events. This is used in practice for eventual and causal consistency (ie Git, Amazon Dynamo, etc.).

#### Algorithm

Clock is a vector `C`, with length = # of nodes in the system

- On node `i`, increment `C[i]` on each event
- On receipt of message with clock `C_m` on node `i`:
  - increment `C[i]`
  - for each `j != i`, `C[j] = max(C[j], C_m[j])`

```java
public class VectorClock {
  public final int[] clock;

  public VectorClock(int n) {
    clock = new int[n];
  }

  public void increment(int i) {
    clock[i]++;
  }

  public void handleMessage(VectorClock other) {
    for (int i = 0; i < clock.length; i++)
      clock[i] = Math.max(clock[i], other.clock[i]);
  }
}
```

```java
public class Node {
  private int id;
  private VectorClock vc;

  public Node(int id, int n) {
    this.id = id;
    this.vc = new VectorClock(n);
  }

  public void event() {
    vc.increment(id);
  }

  public void merge(Node other) {
    vc.handleMessage(other.vc);
  }

  public void send(Node other) {
    other.vc.handleMessage(vc.clock);
  }

  public boolean[] didHappenBefore(Node other) {
    boolean[] res = new boolean[2];
    res[0] = true;
    res[1] = true;

    for (int i = 0; i < vc.clock.length; i++) {
      if (vc.clock[i] > other.vc.clock[i])
        res[0] = false;
       else if (vc.clock[i] < other.vc.clock[i])
        res[1] = false;
    }

    return res;
  }
}
```