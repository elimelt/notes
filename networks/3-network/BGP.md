# Border Gateway Protocol (BGP)

You can view the internet as a graph of interconnected Autonomous Systems (ASes). Each AS can act on its own, and is responsible for routing traffic within itself. The routers within an AS are typically connected to eachother through high-speed links, and are connected to other ASes through *border routers*.

ASes are able to assume the role of a customer, provider, or peer to other ASes.

- **Transit Traffic**: Traffic that passes through an AS to reach another AS.
- **Local Traffic**: Traffic that is destined for a device within the AS.
- **Stub AS**: An AS that only has one connection to another AS, and does not allow transit traffic.
- **Multihomed AS**: An AS that has connections to more than one other AS, but that will not carry transit traffic.
- **Transit AS**: An AS that is connected to more than one other AS and carries both local and transit traffic.

The protocol used to route traffic between ASes is called **BGP** (Border Gateway Protocol). Unlike OSPF and RIP, BGP doesn't find the "best" path to a destination, but rather finds the "best" path according to the policies of the ASes involved. In fact, BGP only advertises based on *reachability*, and not on *cost*, since cost is not a well-defined concept across ASes.


### BGP Overview

Each AS has one or more **border routers** that handle ingress and egress traffic to and from other ASes. ASes also need to have at least one **BGP speaker** that is responsible for exchanging routing information with other ASes. Border routers and BGP speakers are often the same device, but they don't have to be.

BGP is a path vector protocol, which means that it advertises the entire path to a destination (as a sequence of ASes), not just the next hop. This prevents routing loops and allows for policy-based routing through the entire path a packet takes.

BGP speakers aren't obligated to advertise any given path, but they are obligated to advertise the best path according to their policies. They can also cancel advertisements using a *withdraw route* message.

BGP works over TCP, and uses a keep-alive mechanism. If a BGP speaker doesn't receive a keep-alive message from a neighbor within a certain time frame, it will assume that the neighbor is down and will stop advertising the routes it learned from that neighbor.

#### Relationships

- **Provider-Customer**: A provider AS provides transit traffic to a customer AS. The customer AS pays the provider AS for the service. The provider advertises all the routes it knows about to the customer, and advertises routes it learns from the customer to everyone.
- **Customer-Provider**: A customer AS receives transit traffic from a provider AS. Customers advertise own prefixes and routes learned from its customers (if any) to their provider, advertise routes learned from their provider to their customers (if any), but don't advertise routes learned from one provider to another provider.
- **Peer-Peer**: Two ASes are peers if they exchange traffic between their customers, but do not exchange traffic between their own networks. Peers advertise routes learned from their customers to their peer, advertise routes learned from their peer to their customers, but don't advertise routes from their peers to any provider or vice versa.

## BGP Algorithm

Let $AS_i \to AS_j$ be the best path from $AS_i$ to $AS_j$. Then, the BGP routing protocol is defined as follows:

- Customers = $P_c = \{P_1^{c}, P_2^{c}, \ldots, P_n^{c}\}$
- Providers = $P_{pr} = \{P_1^{p}, P_2^{p}, \ldots, P_n^{p}\}$
- Peers = $P_{pe}\{P_1^{r}, P_2^{r}, \ldots, P_n^{r}\}$

Prefer Customer > Peer > Provider, and select the ONE path with the minimum number of AS hops.

### Policy-Based Routing Summary

- Customer paths should be advertised to customers, peers, and providers. This is because customers pay for the service, so it is in the best interest of the provider to advertise this path.
- Peer paths should only be advertised to customers, since you stand to gain nothing from letting peers use the path, and you'd have to pay to use the path for providers
- Provider paths should also only be advertised to customers, since you need to pay to use the path of your provider, and you only make money from customers.