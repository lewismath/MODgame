import time
import numpy as np
import networkx as nx
from .state import GameState, COOLDOWN_DURATIONS, ACTIONS
from .simulation import BETA_BOOST_FACTOR, GAMMA_REDUCTION_FACTOR, DECAY_DURATION
from .network import compute_centrality

SAMPLE_FRACTION = 0.20
MIN_SAMPLE = 5


def apply_action(
    G: nx.Graph,
    state: GameState,
    player: str,
    action: str,
    rng: np.random.Generator,
    centrality_cache: dict,
) -> tuple[int | None, list[list[int]]]:
    """Apply a player action. Returns (target_node, removed_edges)."""
    if state.is_on_cooldown(player, action):
        return None, []

    opponent = 'blue' if player == 'red' else 'red'
    now = time.time()
    target: int | None = None
    removed_edges: list[list[int]] = []

    if 'spread' in action:
        target = _pick_spread_target(G, state, action, rng, centrality_cache)
        if target is not None:
            state.node_states[target] = player
            _boost_neighbours(G, target, action, now)

    elif 'discredit' in action:
        target = _pick_discredit_target(G, state, opponent, action, rng, centrality_cache)
        if target is not None:
            removed_edges = _remove_edges(G, target, rng, centrality_cache)

    if target is not None:
        state.set_cooldown(player, action, COOLDOWN_DURATIONS[action])
        state.interventions.append({
            't': round(time.time() - state.start_time, 3),
            'player': player,
            'action': action,
            'target_node': target,
        })

    return target, removed_edges


def _pick_spread_target(
    G: nx.Graph,
    state: GameState,
    action: str,
    rng: np.random.Generator,
    centrality_cache: dict,
) -> int | None:
    susceptible = [n for n, s in state.node_states.items() if s == 'S']
    if not susceptible:
        return None
    sample = _sample(susceptible, rng)
    if 'influencer' in action:
        return max(sample, key=lambda n: G.degree(n))
    return max(sample, key=lambda n: centrality_cache['betweenness'].get(n, 0.0))


def _pick_discredit_target(
    G: nx.Graph,
    state: GameState,
    opponent: str,
    action: str,
    rng: np.random.Generator,
    centrality_cache: dict,
) -> int | None:
    opponent_nodes = [n for n, s in state.node_states.items() if s == opponent]
    if not opponent_nodes:
        return None
    sample = _sample(opponent_nodes, rng)
    if 'highdegree' in action:
        return max(sample, key=lambda n: G.degree(n))
    return max(sample, key=lambda n: centrality_cache['betweenness'].get(n, 0.0))


def _sample(nodes: list[int], rng: np.random.Generator) -> list[int]:
    n = max(MIN_SAMPLE, int(len(nodes) * SAMPLE_FRACTION))
    n = min(n, len(nodes))
    idx = rng.choice(len(nodes), size=n, replace=False)
    return [nodes[i] for i in idx]


def _boost_neighbours(G: nx.Graph, target: int, action: str, now: float):
    for nb in G.neighbors(target):
        if 'spreadable' in action:
            G.nodes[nb]['beta_peak'] = G.nodes[nb]['beta_base'] * BETA_BOOST_FACTOR
            G.nodes[nb]['beta'] = G.nodes[nb]['beta_peak']
            G.nodes[nb]['beta_modified_until'] = now + DECAY_DURATION
        else:  # persuasive
            G.nodes[nb]['gamma_trough'] = G.nodes[nb]['gamma_base'] * GAMMA_REDUCTION_FACTOR
            G.nodes[nb]['gamma'] = G.nodes[nb]['gamma_trough']
            G.nodes[nb]['gamma_modified_until'] = now + DECAY_DURATION


def _remove_edges(
    G: nx.Graph,
    target: int,
    rng: np.random.Generator,
    centrality_cache: dict,
) -> list[list[int]]:
    neighbours = list(G.neighbors(target))
    if not neighbours:
        return []
    n_remove = max(1, len(neighbours) // 3)
    to_remove = list(rng.choice(neighbours, size=n_remove, replace=False))
    edges = [[target, nb] for nb in to_remove]
    G.remove_edges_from(edges)
    centrality_cache['betweenness'] = nx.betweenness_centrality(G, normalized=True)
    return edges
