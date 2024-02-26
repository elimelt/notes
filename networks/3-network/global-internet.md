# The Global Internet

It isn't possible to scale to the billions of devices with routing protocols like RIP and OSPF. Both of these would require routers to maintain a complete list of all the networks in the internet, which isn't feasible.

The modern internet is mainly composed of *end-user sites* and *service providers*. The end-user sites are typically collections of devices that are connected to the internet through either a single IP address (NAT in home networks), or switched ethernet in enterprise LAN settings. The service providers are the companies that provide the infrastructure for the internet, and are responsible for routing traffic between end-user sites. Service providers have many high performance routers in metro areas, connected to eachother and other service providers through high-speed links.

## Routing Areas

As described with OSPF, a network can be divided into areas to reduce the size of the routing table. This is also done in the global internet, but on a much larger scale. The internet is divided into *routing areas* called **Autonomous Systems** (AS). An AS is a collection of routers and networks that are under the control of a single organization. Each AS has its own routing protocol, and is responsible for routing traffic within the AS. The routers within an AS are typically connected to eachother through high-speed links, and are connected to other ASes through *border routers*.

## Inter-Domain Routing


The internet is a collection of interconnected ASes, which are independently managed and operated organizations. The routers in an AS are responsible for routing traffic within the AS, and the border routers are responsible for routing traffic between ASes. The protocol used to route traffic between ASes is called **BGP** (Border Gateway Protocol).

See BGP.md

