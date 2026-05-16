import numpy as np
from game.network import generate_network
from game.state import GameState, ACTIONS, COOLDOWN_DURATIONS


def _setup():
    rng = np.random.default_rng(42)
    G = generate_network(rng)
    return G, GameState.create(G), rng


def test_initial_states_all_susceptible():
    G, state, _ = _setup()
    assert all(s == 'S' for s in state.node_states.values())


def test_initial_states_covers_all_nodes():
    G, state, _ = _setup()
    assert set(state.node_states.keys()) == set(G.nodes())


def test_seed_initial_states_counts():
    G, state, rng = _setup()
    state.seed_initial_states(G, rng, n_per_side=3)
    scores = state.scores()
    assert scores['red'] == 3
    assert scores['blue'] == 3


def test_scores_sum_to_total():
    G, state, rng = _setup()
    state.seed_initial_states(G, rng, n_per_side=3)
    scores = state.scores()
    assert scores['red'] + scores['blue'] + scores['S'] == len(G.nodes())


def test_cooldown_set_and_check():
    G, state, _ = _setup()
    action = ACTIONS[0]
    assert not state.is_on_cooldown('red', action)
    state.set_cooldown('red', action, 30.0)
    assert state.is_on_cooldown('red', action)


def test_cooldown_does_not_cross_players():
    G, state, _ = _setup()
    state.set_cooldown('red', ACTIONS[0], 30.0)
    assert not state.is_on_cooldown('blue', ACTIONS[0])


def test_cooldown_does_not_cross_actions():
    G, state, _ = _setup()
    state.set_cooldown('red', ACTIONS[0], 30.0)
    assert not state.is_on_cooldown('red', ACTIONS[1])


def test_is_not_over_immediately():
    G, state, _ = _setup()
    assert not state.is_over()


def test_time_remaining_positive():
    G, state, _ = _setup()
    assert state.time_remaining() > 0


def test_all_actions_have_cooldown_duration():
    assert set(COOLDOWN_DURATIONS.keys()) == set(ACTIONS)
