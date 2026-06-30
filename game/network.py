import networkx as nx
import numpy as np

N_COMMUNITIES = 5
N_PER_COMMUNITY = 35      # 175 nodes total
WITHIN_P = 0.3
BETWEEN_P = 0.02
BETA_MEAN, BETA_STD = 0.15, 0.05
GAMMA_MEAN, GAMMA_STD = 0.10, 0.03


def generate_network(rng: np.random.Generator) -> nx.Graph:
    sizes = [N_PER_COMMUNITY] * N_COMMUNITIES
    p = [[WITHIN_P if i == j else BETWEEN_P for j in range(N_COMMUNITIES)]
         for i in range(N_COMMUNITIES)]
    G = nx.stochastic_block_model(sizes, p, seed=int(rng.integers(0, 2**31)))
    for n in G.nodes():
        beta = float(np.clip(rng.normal(BETA_MEAN, BETA_STD), 0.02, 0.5))
        gamma = float(np.clip(rng.normal(GAMMA_MEAN, GAMMA_STD), 0.01, 0.4))
        G.nodes[n].update({
            'beta': beta, 'beta_base': beta, 'beta_peak': beta,
            'gamma': gamma, 'gamma_base': gamma, 'gamma_trough': gamma,
            'beta_modified_until': 0.0,
            'gamma_modified_until': 0.0,
        })
    return G


def compute_layout(G: nx.Graph) -> dict[int, tuple[float, float]]:
    communities: dict[int, list[int]] = {}
    for n in G.nodes():
        communities.setdefault(int(G.nodes[n]['block']), []).append(n)

    n_comm = len(communities)
    local_scale = 0.35  # each cluster's radius as a fraction of the inter-center distance
    pos: dict[int, tuple[float, float]] = {}

    for i, c in enumerate(sorted(communities)):
        angle = 2 * np.pi * i / n_comm
        cx, cy = np.cos(angle), np.sin(angle)
        nodes = communities[c]
        local = nx.spring_layout(G.subgraph(nodes), seed=42, iterations=50)

        xs = [p[0] for p in local.values()]
        ys = [p[1] for p in local.values()]
        extent = max(max(abs(x) for x in xs), max(abs(y) for y in ys), 1e-9)

        for n, (x, y) in local.items():
            pos[n] = (cx + (x / extent) * local_scale,
                      cy + (y / extent) * local_scale)

    return {n: (float(x), float(y)) for n, (x, y) in pos.items()}


def compute_centrality(G: nx.Graph) -> dict:
    return {'betweenness': nx.betweenness_centrality(G, normalized=True)}


def network_to_dict(G: nx.Graph, pos: dict[int, tuple[float, float]]) -> dict:
    return {
        'nodes': [
            {
                'id': n,
                'community': int(G.nodes[n]['block']),
                'beta': G.nodes[n]['beta_base'],
                'gamma': G.nodes[n]['gamma_base'],
                'x': pos[n][0],
                'y': pos[n][1],
            }
            for n in G.nodes()
        ],
        'edges': [[u, v] for u, v in G.edges()],
    }
