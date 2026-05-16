import time
import numpy as np
from game.network import generate_network
from game.state import GameState
from game.simulation import tick, BETA_BOOST_FACTOR, GAMMA_REDUCTION_FACTOR, DECAY_DURATION


def _setup():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    state = GameState.create(G)
    state.seed_initial_states(G, rng, n_per_side=5)
    return G, state, rng


def test_tick_preserves_node_count():
    G, state, rng = _setup()
    before = len(state.node_states)
    tick(G, state, rng, time.time())
    assert len(state.node_states) == before


def test_tick_only_valid_states():
    G, state, rng = _setup()
    for _ in range(20):
        tick(G, state, rng, time.time())
    assert all(s in ('S', 'red', 'blue') for s in state.node_states.values())


def test_susceptible_node_can_be_infected():
    rng = np.random.default_rng(0)
    G = generate_network(rng)
    state = GameState.create(G)
    assert len(list(G.neighbors(0))) > 0, "Node 0 must have neighbours for this test"
    # Force all neighbours of node 0 to red with beta=1
    for nb in G.neighbors(0):
        state.node_states[nb] = 'red'
        G.nodes[nb]['beta'] = 1.0
    state.node_states[0] = 'S'
    G.nodes[0]['gamma'] = 0.0
    for _ in range(30):
        tick(G, state, rng, time.time())
    assert state.node_states[0] == 'red'


def test_neutral_first_no_direct_conversion():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    state = GameState.create(G)
    assert len(list(G.neighbors(0))) > 0, "Node 0 must have neighbours for this test"
    state.node_states[0] = 'red'
    G.nodes[0]['gamma'] = 0.0  # prevent recovery
    for nb in G.neighbors(0):
        state.node_states[nb] = 'blue'
        G.nodes[nb]['beta'] = 1.0
    for _ in range(50):
        tick(G, state, rng, time.time())
    # Node 0 cannot flip directly to blue
    assert state.node_states[0] == 'red'


def test_expired_beta_modification_resets_to_base():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    state = GameState.create(G)
    n = 0
    base = G.nodes[n]['beta_base']
    G.nodes[n]['beta'] = base * BETA_BOOST_FACTOR
    G.nodes[n]['beta_peak'] = base * BETA_BOOST_FACTOR
    G.nodes[n]['beta_modified_until'] = time.time() - 1.0  # expired
    tick(G, state, rng, time.time())
    assert abs(G.nodes[n]['beta'] - base) < 1e-9


def test_expired_gamma_modification_resets_to_base():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    state = GameState.create(G)
    n = 0
    base = G.nodes[n]['gamma_base']
    G.nodes[n]['gamma'] = base * GAMMA_REDUCTION_FACTOR
    G.nodes[n]['gamma_trough'] = base * GAMMA_REDUCTION_FACTOR
    G.nodes[n]['gamma_modified_until'] = time.time() - 1.0  # expired
    tick(G, state, rng, time.time())
    assert abs(G.nodes[n]['gamma'] - base) < 1e-9
