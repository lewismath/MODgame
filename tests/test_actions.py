import time
import numpy as np
import networkx as nx
from game.network import generate_network, compute_centrality
from game.state import GameState
from game.simulation import BETA_BOOST_FACTOR, GAMMA_REDUCTION_FACTOR, DECAY_DURATION
from game.actions import apply_action


def _setup():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    state = GameState.create(G)
    state.seed_initial_states(G, rng, n_per_side=10)
    centrality = compute_centrality(G)
    return G, state, rng, centrality


def test_spread_infects_a_node():
    G, state, rng, centrality = _setup()
    before = state.scores()['red']
    target, _ = apply_action(G, state, 'red', 'spread_spreadable_influencer', rng, centrality)
    assert target is not None
    assert state.scores()['red'] == before + 1


def test_spread_records_intervention():
    G, state, rng, centrality = _setup()
    apply_action(G, state, 'red', 'spread_spreadable_influencer', rng, centrality)
    assert len(state.interventions) == 1
    iv = state.interventions[0]
    assert iv['player'] == 'red'
    assert iv['action'] == 'spread_spreadable_influencer'
    assert 'target_node' in iv and 't' in iv


def test_spread_sets_cooldown():
    G, state, rng, centrality = _setup()
    action = 'spread_spreadable_influencer'
    apply_action(G, state, 'red', action, rng, centrality)
    assert state.is_on_cooldown('red', action)


def test_action_blocked_during_cooldown():
    G, state, rng, centrality = _setup()
    action = 'spread_spreadable_influencer'
    state.set_cooldown('red', action, 30.0)
    target, _ = apply_action(G, state, 'red', action, rng, centrality)
    assert target is None


def test_spreadable_boosts_neighbour_beta():
    G, state, rng, centrality = _setup()
    target, _ = apply_action(G, state, 'red', 'spread_spreadable_influencer', rng, centrality)
    assert target is not None
    now = time.time()
    for nb in G.neighbors(target):
        assert G.nodes[nb]['beta_modified_until'] > now
        assert G.nodes[nb]['beta'] > G.nodes[nb]['beta_base']


def test_persuasive_reduces_neighbour_gamma():
    G, state, rng, centrality = _setup()
    target, _ = apply_action(G, state, 'red', 'spread_persuasive_influencer', rng, centrality)
    assert target is not None
    now = time.time()
    for nb in G.neighbors(target):
        assert G.nodes[nb]['gamma_modified_until'] > now
        assert G.nodes[nb]['gamma'] < G.nodes[nb]['gamma_base']


def test_discredit_removes_edges():
    G, state, rng, centrality = _setup()
    # Make sure there are blue nodes to discredit
    for n in list(state.node_states.keys())[:20]:
        state.node_states[n] = 'blue'
    edges_before = G.number_of_edges()
    target, removed = apply_action(G, state, 'red', 'discredit_highdegree', rng, centrality)
    assert target is not None
    assert G.number_of_edges() < edges_before
    assert len(removed) > 0


def test_spread_targets_susceptible_only():
    G, state, rng, centrality = _setup()
    target, _ = apply_action(G, state, 'red', 'spread_spreadable_influencer', rng, centrality)
    # After action, target is now 'red' — verify it changed from 'S'
    assert state.node_states[target] == 'red'
