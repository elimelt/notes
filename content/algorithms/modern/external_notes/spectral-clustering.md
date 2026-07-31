## Spectral clustering (Thu, May 05)## [CSE 422, Winter 2024](/~jrl/cse422wi24)

## Graph conductance

As in the last lecture, consider an undirected graph \\(\\def\\seteq{\\mathrel{\\vcenter{:}}=} \\def\\cE{\\mathcal{E}} \\def\\cL{\\mathcal{L}} \\def\\R{\\mathbb{R}} \\def\\cR{\\mathcal{R}} \\def\\argmin{\\mathrm{argmin}} \\def\\llangle{\\left\\langle} \\def\\rrangle{\\right\\rangle} \\def\\1{\\mathbf{1}} \\def\\e{\\varepsilon} \\def\\vol{\\mathrm{vol}} \\def\\avint{\\mathop{\\,\\rlap{-}\\!\\!\\int}\\nolimits}\\) \\(G=(V,E)\\) with \\(n=|V|\\) vertices. One way to capture the the idea that a subset \\(S \\subseteq V\\) of vertices is a good “cluster” is through the notion of *conductance*. Define the *volume of \\(S\\)* as the quantity

\\\[\\vol(S) = \\sum\_{u \\in S} \\deg(u),\\\]

i.e., the sum of vertex degrees in $S$. Then we define the *conductance* of the set \\(S\\) by

\\\[\\phi\_G(S) \\seteq \\frac{|E(S,\\bar{S})|}{\\min(\\vol(S),\\vol(\\bar{S}))},\\\]

where \\(E(S,\\bar{S})\\) denotes the set of edges that run from \\(S\\) to its complement.

Let us define \\(\\rho\_2(G)\\) to be the minimum of the conductance as it runs over all non-empty subsets of \\(G\\):

\\\[\\rho\_2(G) \\seteq \\min\_{\\emptyset \\neq S \\subseteq V} \\phi\_G(S)\\,.\\\]

## Spectral clusters

It turns out that the eigenvectors of the Laplacian of \\(G\\) encode information about sets of small conductance. It will be more useful to work with the *normalized Laplacian*. For simplicity, let’s assume that our graph is \\(d\\)-regular, which means that \\(\\deg(v)=d\\) for every \\(v \\in V\\). Then the normalized Laplacian is just the usual (“combinatorial”) Laplacian scaled down by \\(d\\):

\\\[\\cL\_G \\seteq \\frac{1}{d} L\_G = I - \\frac{1}{d} A\\,,\\\]

where \\(A\\) is the adjacency matrix of \\(G\\). Recall that if we sort the eigenvalues of \\(\\cL\_G\\) as \\(\\lambda\_1 \\leq \\lambda\_2 \\leq \\cdots \\leq \\lambda\_n\\), then \\(\\lambda\_1=0\\) corresponds to the constant eigenvector \\(\\mathbf{x}\_1 = (1/\\sqrt{n},\\ldots,1/\\sqrt{n})\\). The next claim gives the first connection between the 2nd smallest eigenvalue \\(\\lambda\_2(G)\\) of \\(\\cL\_G\\) and the sets of minimal conductance in \\(G\\).

> **Claim:** It holds that \\(\\lambda\_2(G) \\leq 2 \\rho\_2(G)\\) for any graph \\(G\\).

To prove this claim, it will help to use the variational characterization of \\(\\lambda\_2(G)\\) from the last lecture:

\\\[\\begin{align\*} \\lambda\_2(G) &= \\min \\left\\{ \\langle \\mathbf{x}, \\cL\_G \\mathbf{x} \\rangle: \\mathbf{x} \\perp \\mathbf{x}\_1, \\|\\mathbf{x}\\|^2=1\\right\\} \\nonumber \\\\ &= \\min \\left\\{ \\frac{\\langle \\mathbf{x}, \\cL\_G \\mathbf{x} \\rangle}{\\|\\mathbf{x}\\|^2}: \\mathbf{x} \\perp \\mathbf{x}\_1\\right\\} \\nonumber \\\\ &= \\min \\left\\{ \\frac{\\langle \\mathbf{x}, \\cL\_G \\mathbf{x} \\rangle}{\\|\\mathbf{x}-\\bar{\\mathbf{x}}\\|^2}: \\mathbf{x} \\neq 0\\right\\}, \\nonumber \\end{align\*}\\\]

where \\(\\bar{\\mathbf{x}} \\seteq \\left(\\frac{1}{n} \\sum\_{u \\in V} x\_u\\right)(1,1,\\ldots,1)\\) is the vector containing the average value of the coordinates of \\(\\mathbf{x}\\) in every coordinate. Note that we have removed the condition \\(\\mathbf{x} \\perp \\mathbf{x}\_1\\) by removing the part of \\(\\mathbf{x}\\) that is not orthogonal to \\(\\mathbf{x}\_1\\):

\\\[\\mathbf{x} - \\langle \\mathbf{x}, \\mathbf{x}\_1\\rangle \\mathbf{x}\_1 = \\mathbf{x} - \\bar{\\mathbf{x}}.\\\]

Using the expression we derived last time for the quadratic form \\(\\langle \\mathbf{x}, \\cL\_G \\mathbf{x}\\rangle\\), we can rewrite the last line above as

\\\[\\begin{equation}\\label{eq:var} \\lambda\_2(G) = \\min \\left\\{ \\frac{\\frac{1}{d} \\sum\_{\\{u,v\\} \\in E} (x\_u-x\_v)^2}{\\sum\_{u \\in V} (x\_u-\\bar{x})^2}: \\mathbf{x} \\neq 0 \\right\\}, \\end{equation}\\\]

where \\(\\bar{x} = \\frac{1}{n} \\sum\_{u \\in V} x\_u\\) is the average value of the components of \\(x\\).

> **Proof:** Note that for a \\(d\\)-regular graph, we have \\(\\vol(S) = d|S|\\). Consider any subset \\(S \\subseteq V\\). We will show that \\(\\lambda\_2(G) \\leq 2 \\phi\_G(S)\\). Clearly we may assume that \\(|S|\\leq n/2\\). Define the indicator vector \\(\\mathbf{v}\_S\\) so that \\(\\mathbf{v}\_S(u)=1\\) if \\(u \\in S\\) and \\(\\mathbf{v}\_S(u)=0\\) otherwise.
> 
> Let us now plug \\(\\mathbf{v}\_S\\) into \\eqref{eq:var} to get an upper bound on \\(\\lambda\_2(G)\\):
> 
> \\\[\\begin{align\*} \\lambda\_2(G) \\leq \\frac{\\frac{1}{d} \\sum\_{\\{u,v\\} \\in E} (\\mathbf{v}\_S(u)-\\mathbf{v}\_S(v))^2}{\\sum\_{u \\in V} (\\mathbf{v}\_S(u)-\\frac{|S|}{n})^2} &= \\frac{\\frac{1}{d} |E(S,\\bar{S})|}{|S| \\left(1-\\frac{|S|}{n}\\right)^2 + (n-|S|) \\left(\\frac{|S|}{n}\\right)^2} \\\\ &= \\frac{\\frac{1}{d} |E(S,\\bar{S})|}{\\frac{|S|}{n} (n-|S|)}. \\end{align\*}\\\]
> 
> \\(\\) Since we have assumed that \\(|S| \\leq n/2\\), we know that \\(\\frac{n-|S|}{n} = 1 - \\frac{|S|}{n} \\geq 1/2\\), and therefore
> 
> \\\[\\lambda\_2(G) \\leq 2 \\frac{\\frac{1}{d} |E(S,\\bar{S})|}{|S|} = 2 \\frac{|E(S,\\bar S)|}{\\vol(S)} = 2 \\phi\_G(S)\\,.\\\]

## Cheeger’s inequality and sweep cuts

In the previous section, we saw that sets of small conductance force \\(\\lambda\_2(G)\\) to be small. It turns out that the other direction is true as well.

> **Discrete Cheeger inequality**: It holds that \\(\\rho\_2(G) \\leq \\sqrt{2 \\lambda\_2(G)}\\) for any graph \\(G\\).

While we will not prove this inequality, we will now discuss the simple algorithm behind it:

> **Algorithm SWEEP(\\(\\mathbf{x}\\)):**
> 
> Sort the vertices \\(V = \\{ v\_1, v\_2, \\ldots, v\_n \\}\\) according to the value of the corresponding coordinate in \\(\\mathbf{x}\\):
> 
> \\\[\\mathbf{x}(v\_1) \\leq \\mathbf{x}(v\_2) \\leq \\cdots \\leq \\mathbf{x}(v\_n).\\\]
> 
> This sorted order gives us \\(n-1\\) different cuts:
> 
> \\\[(\\{v\_1\\}, \\{v\_2, \\ldots, v\_n\\}), (\\{v\_1,v\_2\\}, \\{v\_3,\\ldots,v\_n\\}), \\ldots, (\\{v\_1,\\ldots,v\_{n-1}\\}, v\_n)\\\]
> 
> Now return the cut \\(S\\) among these \\(n-1\\) that has the smallest \\(\\phi\_G(S)\\) value.

The algorithm is well-defined for any vector \\(\\mathbf{x} \\in \\R^V\\). If we additionally assume that \\(\\mathbf{x} \\perp \\mathbf{x}\_1\\), then this algorithm is guaranteed to output a cut \\(S\\) that satisfies

\\\[\\phi\_G(S) \\leq \\sqrt{2 \\cR\_G(\\mathbf{x})},\\\]

where \\(\\cR\_G(\\mathbf{x})\\)—called the “Rayleigh quotient of \\(\\mathbf{x}\\)”—is defined by

\\\[\\cR\_G(\\mathbf{x}) = \\frac{\\sum\_{\\{u,v\\} \\in E} \\left(\\mathbf{x}(u) - \\mathbf{x}(v)\\right)^2}{d \\|\\mathbf{x}\\|^2}\\\]

## Multi-way spectral clustering

If we are interested in finding a clustering into more pieces, we can use higher eigenvectors. Define the *\\(k\\)-way conductance of \\(G\\)* as the quantity

\\\[\\rho\_k(G) \\seteq \\min\_{S\_1, S\_2, \\ldots, S\_k \\subseteq V} \\max \\left\\{ \\phi\_G(S\_i): i=1,\\ldots k \\right\\},\\\]

where the minimum is over all non-empty, *pairwise disjoint* subsets of \\(V\\). Then one has the following [higher-order Cheeger inequality](https://arxiv.org/pdf/1111.1055.pdf):

\\\[\\frac{\\lambda\_k(G)}{2} \\leq \\rho\_k(G) \\leq O(k^2) \\sqrt{\\lambda\_k}\\\]

It is not known whether one can reduce the factor \\(O(k^2)\\), but this is possible if we know there are at least \\(1.1 k\\) small eigenvalues:

\\\[\\rho\_k(G) \\leq O\\left(\\sqrt{\\lambda\_{1.1 k} \\log k}\\right).\\\]

One general way to recover a \\(k\\)-clustering is to first construct the *spectral embedding* along the first \\(k\\) eigenvectors: This is the map \\(F: V \\to \\R^k\\) defined by

\\\[F(u) = \\left(\\mathbf{x}\_1(u), \\mathbf{x}\_2(u), \\ldots, \\mathbf{x}\_k(u)\\right),\\\]

where \\(\\mathbf{x}\_1,\\ldots,\\mathbf{x}\_k\\) are the first \\(k\\) eigenvectors of \\(\\cL\_G\\).

Now one can look for geometric clusters, and using the right procedure, it is possible to give an algorithm that is guaranteed to produce \\(k\\) disjoint clusters with small conductance. In practice, this second geometric partitioning step often is done using some variant of the [\\(k\\)-means algorithm](https://en.wikipedia.org/wiki/K-means_clustering).