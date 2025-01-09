# [source](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/acrobat-17.pdf)

###### Hints for Computer System Design

---

### Key Insights

#### Caching

Store $\[f, x, f(x)\]$ tuples in a cache.

If $f$ isn't a pure function, invalidate with the following:

$$
f(x + \Delta) = g(x, \Delta, f(x))
$$

For example, $x$ is an `int[]`, $\Delta$ is a write $(i, v)$, and $f$ is a function `int sum(int[] x)`. Then $g(x, \Delta, f(x))$ is `f(x) + v - x[i]`.

Caches should ideally have adaptive sizes.

A classic example is the caching in hardware that uses $\[Fetch, \text{address}, \text{content of address}\]$ tuples. Similarly, virtual memory uses $\[Page, \text{address}, \text{content of address}\]$ tuples.

However, more complicated applications of caching exist. In real-time systems, you're often trying to cache the state of a system given small changes corresponding to events. The key here is to try and invalidate as few entries as possible in response to events.


### Lecture Review Notes

#### Why is system design hard?

- external interface isn't well defined 
    - requirements aren't clear
    - Things are often not well-designed
- The measure of success is not very clear
    - Many different ways to interact with a system
    - Many systems, even in production, have bugs

#### Throw one away

- Always be prepared to discard your prototype
- Throw ideas at the wall and go with what sticks


### Open Questions

-
-

### Further Reading

- MicroLog
- https://github.com/DPDK/dpdk
