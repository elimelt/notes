# BGP

Let $AS_i \to AS_j$ be the best path from $AS_i$ to $AS_j$. Then, the BGP routing protocol is defined as follows:


- Customers = $P_c = \{P_1^{c}, P_2^{c}, \ldots, P_n^{c}\}$
- Providers = $P_{pr} = \{P_1^{p}, P_2^{p}, \ldots, P_n^{p}\}$
- Peers = $P_{pe}\{P_1^{r}, P_2^{r}, \ldots, P_n^{r}\}$

Prefer Customer > Peer > Provider, and select the ONE path with the minimum number of AS hops.

The BGP protocol is a path vector protocol, which means that it advertises the entire path to a destination, not just the next hop. This is useful for detecting routing loops.

You should advertise the best path to your neighbors, and your neighbors should advertise the best path to you, but this is not always the case. This is because BGP is a policy-based protocol, and the best path may not be the path that the AS wants to use. In particular...

### Policy-Based Routing

- Customer paths should be advertised to customers, peers, and providers. This is because customers pay for the service, so it is in the best interest of the provider to advertise this path.
- Peer paths should only be advertised to customers, since you stand to gain nothing from letting peers use the path, and you'd have to pay to use the path for providers
- Provider paths should also only be advertised to customers, since you need to pay to use the path of your provider, and you only make money from customers.