import numpy as np
import networkx as nx
from .state import GameState

DECAY_DURATION = 10.0
BETA_BOOST_FACTOR = 2.0
GAMMA_REDUCTION_FACTOR = 0.5


def tick(G: nx.Graph, state: GameState, rng: np.random.Generator, now: float):
    _decay_parameters(G, now)
    _update_infections(G, state, rng)


def _decay_parameters(G: nx.Graph, now: float):
    for n in G.nodes():
        data = G.nodes[n]
        if data['beta_modified_until'] > 0.0 and now < data['beta_modified_until']:
            elapsed = now - (data['beta_modified_until'] - DECAY_DURATION)
            frac = max(0.0, 1.0 - elapsed / DECAY_DURATION)
            data['beta'] = data['beta_base'] + (data['beta_peak'] - data['beta_base']) * frac
        elif data['beta_modified_until'] > 0.0:
            data['beta'] = data['beta_base']

        if data['gamma_modified_until'] > 0.0 and now < data['gamma_modified_until']:
            elapsed = now - (data['gamma_modified_until'] - DECAY_DURATION)
            frac = max(0.0, 1.0 - elapsed / DECAY_DURATION)
            data['gamma'] = data['gamma_base'] + (data['gamma_trough'] - data['gamma_base']) * frac
        elif data['gamma_modified_until'] > 0.0:
            data['gamma'] = data['gamma_base']


def _update_infections(G: nx.Graph, state: GameState, rng: np.random.Generator):
    new_states = dict(state.node_states)
    nodes = list(G.nodes())
    rng.shuffle(nodes)
    for node in nodes:
        current = state.node_states[node]
        if current == 'S':
            infected_nbs = [nb for nb in G.neighbors(node)
                            if state.node_states[nb] in ('red', 'blue')]
            if infected_nbs:
                nb = infected_nbs[int(rng.integers(len(infected_nbs)))]
                if rng.random() < G.nodes[nb]['beta']:
                    new_states[node] = state.node_states[nb]
        elif current in ('red', 'blue'):
            if rng.random() < G.nodes[node]['gamma']:
                new_states[node] = 'S'
    state.node_states = new_states
