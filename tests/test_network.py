import numpy as np
import networkx as nx
from game.network import generate_network, compute_layout, compute_centrality, network_to_dict


def test_network_size():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    assert 150 <= len(G.nodes()) <= 200


def test_network_has_block_attribute():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    assert all('block' in G.nodes[n] for n in G.nodes())


def test_node_beta_gamma_in_range():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    for n in G.nodes():
        assert 0.0 < G.nodes[n]['beta'] <= 1.0
        assert 0.0 < G.nodes[n]['gamma'] <= 1.0


def test_node_base_equals_current_at_start():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    for n in G.nodes():
        assert G.nodes[n]['beta'] == G.nodes[n]['beta_base']
        assert G.nodes[n]['gamma'] == G.nodes[n]['gamma_base']


def test_node_peak_trough_initialized_to_base():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    for n in G.nodes():
        assert G.nodes[n]['beta_peak'] == G.nodes[n]['beta_base']
        assert G.nodes[n]['gamma_trough'] == G.nodes[n]['gamma_base']


def test_node_modification_timestamps_zero():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    for n in G.nodes():
        assert G.nodes[n]['beta_modified_until'] == 0.0
        assert G.nodes[n]['gamma_modified_until'] == 0.0


def test_layout_covers_all_nodes():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    pos = compute_layout(G)
    assert set(pos.keys()) == set(G.nodes())


def test_compute_centrality_structure():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    c = compute_centrality(G)
    assert 'betweenness' in c
    assert set(c['betweenness'].keys()) == set(G.nodes())


def test_network_to_dict_structure():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    pos = compute_layout(G)
    d = network_to_dict(G, pos)
    assert 'nodes' in d and 'edges' in d
    assert len(d['nodes']) == len(G.nodes())
    assert all(k in d['nodes'][0] for k in ('id', 'community', 'beta', 'gamma', 'x', 'y'))
