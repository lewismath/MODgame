import time
import numpy as np
import networkx as nx
from dataclasses import dataclass, field

ACTIONS = [
    'spread_spreadable_influencer',
    'spread_spreadable_connector',
    'spread_persuasive_influencer',
    'spread_persuasive_connector',
    'discredit_highdegree',
    'discredit_highbetweenness',
]

COOLDOWN_DURATIONS: dict[str, float] = {action: 10.0 for action in ACTIONS}


@dataclass
class GameState:
    node_states: dict[int, str]
    cooldowns: dict[str, dict[str, float]]
    interventions: list[dict]
    start_time: float
    duration: float
    random_seed: int = 0
    game_id: str = ''

    @classmethod
    def create(cls, G: nx.Graph, duration: float = 150.0) -> 'GameState':
        return cls(
            node_states={n: 'S' for n in G.nodes()},
            cooldowns={
                player: {action: 0.0 for action in ACTIONS}
                for player in ('red', 'blue')
            },
            interventions=[],
            start_time=time.time(),
            duration=duration,
        )

    def seed_initial_states(self, G: nx.Graph, rng: np.random.Generator, n_per_side: int = 3):
        communities: dict[int, list[int]] = {}
        for n in G.nodes():
            communities.setdefault(int(G.nodes[n]['block']), []).append(n)
        comm_ids = sorted(communities)
        n_comm = len(comm_ids)
        # Pick two communities as far apart as possible on the circle layout
        red_comm = comm_ids[0]
        blue_comm = comm_ids[(n_comm + 1) // 2]
        for n in rng.choice(communities[red_comm], size=min(n_per_side, len(communities[red_comm])), replace=False):
            self.node_states[int(n)] = 'red'
        for n in rng.choice(communities[blue_comm], size=min(n_per_side, len(communities[blue_comm])), replace=False):
            self.node_states[int(n)] = 'blue'

    def scores(self) -> dict[str, int]:
        counts: dict[str, int] = {'red': 0, 'blue': 0, 'S': 0}
        for s in self.node_states.values():
            counts[s] += 1
        return counts

    def time_remaining(self) -> float:
        return max(0.0, self.duration - (time.time() - self.start_time))

    def is_over(self) -> bool:
        return self.time_remaining() <= 0.0

    def is_on_cooldown(self, player: str, action: str) -> bool:
        return time.time() < self.cooldowns[player][action]

    def set_cooldown(self, player: str, action: str, duration: float):
        self.cooldowns[player][action] = time.time() + duration
