import networkx as nx
import matplotlib.pyplot as plt

def create_graph_from_adjacency_list(adj_list) -> nx.Graph:
    G = nx.Graph()
    for node, neighbors in adj_list.items():
        for neighbor in neighbors:
            G.add_edge(node, neighbor)
    return G

def create_graph_from_adjacency_matrix(adj_matrix) -> nx.Graph:
    G = nx.Graph()
    for i in range(len(adj_matrix)):
        for j in range(len(adj_matrix[i])):
            if adj_matrix[i][j] == 1:
                G.add_edge(i, j)
    return G