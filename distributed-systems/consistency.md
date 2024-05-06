# Consistency

**Consistency**: the allowed semantics of operations that mutate a data store/shared object.

Consistency specifies the interface (as opposed to implementation) for behavior of your system. It is essentially the contract between the programmer and implementer. An **anomaly** is a violation of the consistency semantics of the system

## Types of Consistency

| Type                 | Description                               | 
|----------------------|-------------------------------------------|
| Strong Consistency   | The system behaves as if there is a single server. Systems that maintain a single consistent log of operations are often strongly consistent. |
| Weak Consistency     | Definitions vary, but basically just *not* strong consistency.  |
| Eventual Consistency | Weak consistency with any anomalies guaranteed to be temporary. |

## Coordinating through a KV Store

```python
def Produce(key, lock, command):
  result = application.execute(command)
  storage.put(key, result)
  storage.put(lock, True)

def Consume(key, lock):
  while storage.get(lock) is False:
    pass
  return storage.get(key)
```

With strong consistency semantics, the above approach works fine. However, with eventual consistency, and particularly for any system without multi-key transactions, we might see the update for `storage.get(done)` before the update for `storage.get(key)`, leading to unexpected behavior.

## Formalization

[Read here](https://lamport.azurewebsites.net/pubs/interprocess.pdf) for more info/theory.

For a given RPC, the initial request starts at time $t$ and the reply returns at time $t + x$. We cannot be sure what happens during $(t, t + x)$, since the request/reply could be lost and retransmitted, and intermediate coordination sometimes has to take place.

With only a single server, you don't know precisely when the operation takes place, but we expect it to be some time in $(t, t + x)$. However, weaker consistency models relax this assumption, also sometimes allowing different readers to see different results concurrently.

We use different models because of the following tradeoffs:

- Performance: Consistency requires coordination, so there is often a tradeoff between the level of consistency and the performance of the system
- Availability: If some client is offline or some network failure occurs, we might be forced to abandon strong consistency
- Programmability: Weaker consistency models are harder to reason about and program with

### Lamport's Register Semantics

Registers hold a single value, and we define operations $r_i, $w(v)$ as the $i$th read, and a write to the register with value $v$. Each operation has some starting time and ending time.

- A read is **safe** if it is not concurrent with any write, and thus obtains the previously written value.
- A read is **regular** if it is either safe, or if concurrent with a write, obtains either the old or new value.
- A read/write is **atomic** if operations are safe, or if reads and writes behave as if they occur in some definite order.


| Semantics | Constraints          |
|-----------|----------------------|
| safe      | $r_1 \to v_1$         |
| regular   | $r_1 \to v_1 \land (r_2 \to v_1 \lor r_2 \to v_2) \land (r_3 \to v_1 \lor r_3 \to v_2)$ |
| atomic    | $r_1 \to v_1 \land (r_2 \to v_1 \lor r_2 \to v_2) \land (r_3 \to v_1 \lor r_3 \to v_2) \land (r_2 \to v_2 \implies t_3 \to v_2)$ |

```plaintext
            r1           r2     r3
          |----|       |----| |----|
   w(v1)                w(v2)
|------|             |---------|
```