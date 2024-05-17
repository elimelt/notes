# Network Flow - Max Flow and Min Cut

**Max Flow** and **Min Cut** are two important concepts in graph theory with wide reaching applications. Many problems are reduced to either of them, such as...

- **Transportation Networks**: flow of goods, data, or people through a network, i.e. all kinds of traffic flow 
- **Telecommunications**: flow of data through a network
- **Image Segmentation**: partitioning an image into regions
- **Data Mining**: clustering and classification

## Minimum Cut

Given a directed weighted graph $G = (V, E)$ with edge weights $c(e)$ for $e \in E$, as well as two distinguished nodes $s$ and $t$, find a cut separating $s, t$ that cuts the minimum capacity of edges.