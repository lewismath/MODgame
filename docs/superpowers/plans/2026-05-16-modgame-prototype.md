# MODgame Web Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real-time 2-player browser game simulating information spread on a network, with a Python/Flask-SocketIO backend and D3.js frontend.

**Architecture:** Flask-SocketIO runs the SIS simulation in a background thread (~200ms ticks), emitting compact graph state to the browser over WebSockets. All game logic is server-side; the browser only renders and forwards button presses. Node positions are fixed after an initial layout pass.

**Tech Stack:** Python 3.11+, Flask 3, Flask-SocketIO 5, eventlet, NetworkX 3, NumPy; D3.js 7 and Socket.IO 4 via CDN.

---

## File Structure

```
MODgame/
├── app.py                     # Flask app, SocketIO handlers, game orchestration
├── game/
│   ├── __init__.py
│   ├── network.py             # SBM generation, layout, centrality, serialization
│   ├── state.py               # GameState: node states, cooldowns, scoring, timing
│   ├── simulation.py          # SIS tick, parameter decay
│   ├── actions.py             # Spread/discredit targeting and application
│   └── persistence.py         # JSON game log writer
├── templates/
│   └── index.html             # Single-page HTML shell
├── static/
│   ├── css/style.css
│   └── js/
│       ├── network.js         # D3.js SVG renderer, state updates
│       ├── buttons.js         # Button panel, cooldown progress bars
│       └── game.js            # Socket.IO client, event routing, score/timer
├── tests/
│   ├── __init__.py
│   ├── test_network.py
│   ├── test_state.py
│   ├── test_simulation.py
│   ├── test_actions.py
│   └── test_persistence.py
├── games/                     # Created at runtime; one JSON per game
└── requirements.txt
```

**Key interface contracts:**
- `apply_action` returns `(target_node: int | None, removed_edges: list[list[int]])` so the server can emit edge removals to the client.
- Each graph node carries: `beta`, `beta_base`, `beta_peak`, `gamma`, `gamma_base`, `gamma_trough`, `beta_modified_until`, `gamma_modified_until`, `block`.
- State tick payload: `{node_states, scores, time_remaining, cooldowns}`.

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `game/__init__.py`
- Create: `tests/__init__.py`
- Create: `games/.gitkeep`

- [ ] **Step 1: Write requirements.txt**

```
flask==3.0.3
flask-socketio==5.3.6
eventlet==0.35.2
networkx==3.3
numpy==1.26.4
pytest==8.2.0
```

- [ ] **Step 2: Create directory structure**

```bash
mkdir -p game tests games static/css static/js templates
touch game/__init__.py tests/__init__.py games/.gitkeep
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 4: Verify imports**

```bash
python -c "import flask, flask_socketio, networkx, numpy; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git init
git add requirements.txt game/__init__.py tests/__init__.py games/.gitkeep
git commit -m "chore: project scaffold"
```

---

## Task 2: Network Generation

**Files:**
- Create: `game/network.py`
- Create: `tests/test_network.py`

- [ ] **Step 1: Write failing tests**

`tests/test_network.py`:
```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/test_network.py -v
```

Expected: All 9 tests FAIL with `ModuleNotFoundError: No module named 'game.network'`

- [ ] **Step 3: Implement game/network.py**

```python
import networkx as nx
import numpy as np

N_COMMUNITIES = 5
N_PER_COMMUNITY = 35      # 175 nodes total
WITHIN_P = 0.3
BETWEEN_P = 0.05
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
    pos = nx.spring_layout(G, seed=42, k=1.5 / len(G) ** 0.5, iterations=100)
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
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_network.py -v
```

Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add game/network.py tests/test_network.py
git commit -m "feat: network generation — SBM, per-node beta/gamma, layout, centrality"
```

---

## Task 3: Game State

**Files:**
- Create: `game/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing tests**

`tests/test_state.py`:
```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/test_state.py -v
```

Expected: All 10 tests FAIL with `ModuleNotFoundError: No module named 'game.state'`

- [ ] **Step 3: Implement game/state.py**

```python
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
        nodes = list(G.nodes())
        chosen = rng.choice(nodes, size=n_per_side * 2, replace=False)
        for n in chosen[:n_per_side]:
            self.node_states[int(n)] = 'red'
        for n in chosen[n_per_side:]:
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
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_state.py -v
```

Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add game/state.py tests/test_state.py
git commit -m "feat: GameState — node states, cooldowns, scoring, timing"
```

---

## Task 4: SIS Simulation

**Files:**
- Create: `game/simulation.py`
- Create: `tests/test_simulation.py`

- [ ] **Step 1: Write failing tests**

`tests/test_simulation.py`:
```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/test_simulation.py -v
```

Expected: All 6 tests FAIL with `ModuleNotFoundError: No module named 'game.simulation'`

- [ ] **Step 3: Implement game/simulation.py**

```python
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
        if now < data['beta_modified_until']:
            elapsed = now - (data['beta_modified_until'] - DECAY_DURATION)
            frac = max(0.0, 1.0 - elapsed / DECAY_DURATION)
            data['beta'] = data['beta_base'] + (data['beta_peak'] - data['beta_base']) * frac
        else:
            data['beta'] = data['beta_base']

        if now < data['gamma_modified_until']:
            elapsed = now - (data['gamma_modified_until'] - DECAY_DURATION)
            frac = max(0.0, 1.0 - elapsed / DECAY_DURATION)
            data['gamma'] = data['gamma_base'] + (data['gamma_trough'] - data['gamma_base']) * frac
        else:
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
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_simulation.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add game/simulation.py tests/test_simulation.py
git commit -m "feat: SIS simulation — neutral-first dynamics, parameter decay"
```

---

## Task 5: Player Actions

**Files:**
- Create: `game/actions.py`
- Create: `tests/test_actions.py`

- [ ] **Step 1: Write failing tests**

`tests/test_actions.py`:
```python
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
    # Target should have been susceptible before the action
    # After action it is now 'red' — verify it was susceptible by checking it changed
    assert state.node_states[target] == 'red'
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/test_actions.py -v
```

Expected: All 8 tests FAIL with `ModuleNotFoundError: No module named 'game.actions'`

- [ ] **Step 3: Implement game/actions.py**

```python
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
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_actions.py -v
```

Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add game/actions.py tests/test_actions.py
git commit -m "feat: player actions — spread targeting, discredit, parameter boost/decay wiring"
```

---

## Task 6: Data Persistence

**Files:**
- Create: `game/persistence.py`
- Create: `tests/test_persistence.py`

- [ ] **Step 1: Write failing tests**

`tests/test_persistence.py`:
```python
import json
import os
import tempfile
import numpy as np
from game.persistence import save_game


def _sample_args():
    network = {
        'nodes': [{'id': 0, 'community': 0, 'beta': 0.15, 'gamma': 0.10, 'x': 0.1, 'y': 0.2}],
        'edges': [[0, 1]],
    }
    initial_states = {0: 'S', 1: 'red'}
    interventions = [{'t': 3.1, 'player': 'red', 'action': 'spread_spreadable_influencer', 'target_node': 0}]
    outcome = {'red': 90, 'blue': 60, 'S': 25, 'winner': 'red'}
    return network, initial_states, interventions, outcome


def test_save_game_creates_file():
    network, initial_states, interventions, outcome = _sample_args()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_game('test-id', 99, network, initial_states, interventions, outcome, games_dir=tmpdir)
        assert os.path.exists(path)


def test_save_game_valid_json():
    network, initial_states, interventions, outcome = _sample_args()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_game('test-id', 99, network, initial_states, interventions, outcome, games_dir=tmpdir)
        with open(path) as f:
            data = json.load(f)
        assert data['game_id'] == 'test-id'
        assert data['random_seed'] == 99
        assert 'network' in data
        assert 'initial_states' in data
        assert 'interventions' in data
        assert 'outcome' in data


def test_save_game_initial_states_keys_are_strings():
    network, initial_states, interventions, outcome = _sample_args()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_game('test-id', 99, network, initial_states, interventions, outcome, games_dir=tmpdir)
        with open(path) as f:
            data = json.load(f)
        assert all(isinstance(k, str) for k in data['initial_states'].keys())
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/test_persistence.py -v
```

Expected: All 3 tests FAIL with `ModuleNotFoundError: No module named 'game.persistence'`

- [ ] **Step 3: Implement game/persistence.py**

```python
import json
import os

GAMES_DIR = 'games'


def save_game(
    game_id: str,
    random_seed: int,
    network: dict,
    initial_states: dict,
    interventions: list[dict],
    outcome: dict,
    games_dir: str = GAMES_DIR,
) -> str:
    os.makedirs(games_dir, exist_ok=True)
    data = {
        'game_id': game_id,
        'random_seed': random_seed,
        'network': network,
        'initial_states': {str(k): v for k, v in initial_states.items()},
        'interventions': interventions,
        'outcome': outcome,
    }
    safe_id = game_id.replace(':', '-').replace(' ', '_')
    path = os.path.join(games_dir, f'{safe_id}.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    return path
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_persistence.py -v
```

Expected: All 3 tests PASS

- [ ] **Step 5: Run full test suite to confirm nothing broken**

```bash
pytest -v
```

Expected: All 36 tests PASS

- [ ] **Step 6: Commit**

```bash
git add game/persistence.py tests/test_persistence.py
git commit -m "feat: game persistence — JSON log with network, states, interventions, outcome"
```

---

## Task 7: Flask-SocketIO Server

**Files:**
- Create: `app.py`

No unit tests for this task — it is integration-tested manually in Task 12. Focus is wiring the backend modules together correctly.

- [ ] **Step 1: Implement app.py**

```python
import eventlet
eventlet.monkey_patch()

import time
import numpy as np
from datetime import datetime
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

from game.network import generate_network, compute_layout, compute_centrality, network_to_dict
from game.state import GameState, ACTIONS
from game.simulation import tick
from game.actions import apply_action
from game.persistence import save_game

app = Flask(__name__)
app.config['SECRET_KEY'] = 'modgame-dev-secret'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

TICK_INTERVAL = 0.2   # seconds
ROUND_DURATION = 150.0  # seconds

# Single-game global state (prototype: one game at a time)
_G = None
_state: GameState | None = None
_rng: np.random.Generator | None = None
_network_dict: dict | None = None
_initial_states: dict | None = None
_centrality: dict | None = None


def _new_game():
    global _G, _state, _rng, _network_dict, _initial_states, _centrality
    seed = int(np.random.randint(0, 2**31))
    _rng = np.random.default_rng(seed)
    _G = generate_network(_rng)
    pos = compute_layout(_G)
    _network_dict = network_to_dict(_G, pos)
    _centrality = compute_centrality(_G)
    _state = GameState.create(_G, duration=ROUND_DURATION)
    _state.random_seed = seed
    _state.game_id = datetime.now().isoformat(timespec='seconds')
    _state.seed_initial_states(_G, _rng, n_per_side=3)
    _initial_states = dict(_state.node_states)


def _simulation_loop():
    while _state and not _state.is_over():
        now = time.time()
        tick(_G, _state, _rng, now)
        payload = {
            'node_states': {str(k): v for k, v in _state.node_states.items()},
            'scores': _state.scores(),
            'time_remaining': round(_state.time_remaining(), 1),
            'cooldowns': {
                player: {
                    action: round(max(0.0, expires - now), 2)
                    for action, expires in cd.items()
                }
                for player, cd in _state.cooldowns.items()
            },
        }
        socketio.emit('state', payload)
        socketio.sleep(TICK_INTERVAL)
    if _state:
        _end_game()


def _end_game():
    scores = _state.scores()
    winner = 'red' if scores['red'] >= scores['blue'] else 'blue'
    outcome = {**scores, 'winner': winner}
    save_game(
        _state.game_id, _state.random_seed,
        _network_dict, _initial_states,
        _state.interventions, outcome,
    )
    socketio.emit('game_over', outcome)


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('start_game')
def handle_start_game():
    _new_game()
    socketio.emit('game_init', {
        'network': _network_dict,
        'initial_states': {str(k): v for k, v in _state.node_states.items()},
        'duration': ROUND_DURATION,
    })
    socketio.start_background_task(_simulation_loop)


@socketio.on('action')
def handle_action(data):
    if not _state or _state.is_over():
        return
    player = data.get('player')
    action = data.get('action')
    if player not in ('red', 'blue') or action not in ACTIONS:
        return
    target, removed_edges = apply_action(_G, _state, player, action, _rng, _centrality)
    if target is not None:
        socketio.emit('action_result', {
            'player': player,
            'action': action,
            'target': target,
            'removed_edges': removed_edges,
        })


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
```

- [ ] **Step 2: Start the server and check it loads without errors**

```bash
python app.py
```

Expected output includes:
```
 * Running on http://127.0.0.1:5000
```

Stop with Ctrl-C.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: Flask-SocketIO server — game loop, action handling, end-game persistence"
```

---

## Task 8: HTML Template and CSS

**Files:**
- Create: `templates/index.html`
- Create: `static/css/style.css`

- [ ] **Step 1: Create templates/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MODgame</title>
  <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
  <div id="hud">
    <div id="score-red" class="score red-text">RED: 0</div>
    <div id="timer">2:30</div>
    <div id="score-blue" class="score blue-text">BLUE: 0</div>
  </div>

  <div id="main">
    <div id="buttons-red" class="button-panel"></div>
    <div id="graph-container">
      <svg id="graph"></svg>
    </div>
    <div id="buttons-blue" class="button-panel"></div>
  </div>

  <div id="overlay" class="hidden">
    <div id="overlay-content">
      <h1 id="winner-text"></h1>
      <p id="final-scores"></p>
      <button id="play-again">Play Again</button>
    </div>
  </div>

  <div id="start-screen">
    <h1>MODgame</h1>
    <p>Red player: left buttons &nbsp;|&nbsp; Blue player: right buttons</p>
    <button id="start-btn">Start Game</button>
  </div>

  <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <script src="/static/js/network.js"></script>
  <script src="/static/js/buttons.js"></script>
  <script src="/static/js/game.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create static/css/style.css**

```css
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #111;
  color: #eee;
  font-family: monospace;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

#hud {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 24px;
  background: #1a1a1a;
  font-size: 1.4rem;
  font-weight: bold;
}

.red-text { color: #e84040; }
.blue-text { color: #4080e8; }

#timer { font-size: 1.8rem; }

#main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

#graph-container {
  flex: 1;
  position: relative;
}

#graph {
  width: 100%;
  height: 100%;
}

.button-panel {
  width: 160px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
  padding: 12px;
  background: #1a1a1a;
}

.action-btn {
  position: relative;
  width: 100%;
  padding: 10px 8px;
  font-family: monospace;
  font-size: 0.72rem;
  text-align: center;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #fff;
  overflow: hidden;
}

.action-btn.red-btn { background: #7a1a1a; }
.action-btn.blue-btn { background: #1a3a7a; }
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.cooldown-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 4px;
  background: rgba(255,255,255,0.6);
  width: 0%;
  transition: width 0.1s linear;
}

#overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

#overlay.hidden { display: none; }

#overlay-content {
  text-align: center;
  font-size: 1.2rem;
}

#overlay-content h1 { font-size: 3rem; margin-bottom: 1rem; }
#play-again {
  margin-top: 2rem;
  padding: 12px 32px;
  font-size: 1.2rem;
  cursor: pointer;
  background: #333;
  color: #eee;
  border: 1px solid #666;
  border-radius: 4px;
}

#start-screen {
  position: fixed;
  inset: 0;
  background: #111;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  z-index: 20;
}

#start-screen h1 { font-size: 3rem; }
#start-btn {
  padding: 14px 40px;
  font-size: 1.3rem;
  cursor: pointer;
  background: #333;
  color: #eee;
  border: 1px solid #888;
  border-radius: 4px;
}
```

- [ ] **Step 3: Start server and open http://localhost:5000 in browser**

```bash
python app.py
```

Expected: Start screen is visible with "MODgame" heading and "Start Game" button. Page has dark background. No JS errors in browser console.

- [ ] **Step 4: Commit**

```bash
git add templates/index.html static/css/style.css
git commit -m "feat: HTML shell and CSS layout — HUD, button panels, graph area, overlays"
```

---

## Task 9: Network Visualization

**Files:**
- Create: `static/js/network.js`

- [ ] **Step 1: Implement static/js/network.js**

```javascript
const Network = (() => {
  let svg, linkSel, nodeSel;
  let xScale, yScale;
  let edgeSet; // Set of "u-v" strings for fast removal
  let degreeMap = {};

  const STATE_COLOR = { S: '#888888', red: '#e84040', blue: '#4080e8' };
  const MIN_R = 4, MAX_R = 14;

  function init(networkData) {
    const container = document.getElementById('graph-container');
    const W = container.clientWidth;
    const H = container.clientHeight;
    const PAD = 40;

    svg = d3.select('#graph')
      .attr('width', W)
      .attr('height', H);
    svg.selectAll('*').remove();

    const xs = networkData.nodes.map(n => n.x);
    const ys = networkData.nodes.map(n => n.y);
    xScale = d3.scaleLinear().domain([Math.min(...xs), Math.max(...xs)]).range([PAD, W - PAD]);
    yScale = d3.scaleLinear().domain([Math.min(...ys), Math.max(...ys)]).range([PAD, H - PAD]);

    // Precompute degree for radius scaling
    networkData.nodes.forEach(n => { degreeMap[n.id] = 0; });
    networkData.edges.forEach(([u, v]) => { degreeMap[u]++; degreeMap[v]++; });
    const maxDeg = Math.max(...Object.values(degreeMap), 1);
    const rScale = d3.scaleLinear().domain([0, maxDeg]).range([MIN_R, MAX_R]);

    edgeSet = new Set(networkData.edges.map(([u, v]) => edgeKey(u, v)));

    const g = svg.append('g');

    linkSel = g.append('g').attr('class', 'links')
      .selectAll('line')
      .data(networkData.edges)
      .join('line')
        .attr('x1', ([u]) => xScale(networkData.nodes[u].x))
        .attr('y1', ([u]) => yScale(networkData.nodes[u].y))
        .attr('x2', ([, v]) => xScale(networkData.nodes[v].x))
        .attr('y2', ([, v]) => yScale(networkData.nodes[v].y))
        .attr('stroke', '#444')
        .attr('stroke-width', 1)
        .attr('stroke-opacity', 1.0)
        .attr('data-key', ([u, v]) => edgeKey(u, v));

    nodeSel = g.append('g').attr('class', 'nodes')
      .selectAll('circle')
      .data(networkData.nodes)
      .join('circle')
        .attr('cx', n => xScale(n.x))
        .attr('cy', n => yScale(n.y))
        .attr('r', n => rScale(degreeMap[n.id]))
        .attr('fill', STATE_COLOR.S)
        .attr('data-id', n => n.id);
  }

  function update(nodeStates) {
    nodeSel.attr('fill', n => STATE_COLOR[nodeStates[n.id]] || STATE_COLOR.S);
  }

  function removeEdges(edges) {
    edges.forEach(([u, v]) => {
      const key = edgeKey(u, v);
      edgeSet.delete(key);
    });
    linkSel.attr('stroke-opacity', function() {
      const key = d3.select(this).attr('data-key');
      return edgeSet.has(key) ? 1.0 : 0.0;
    });
  }

  function edgeKey(u, v) {
    return u < v ? `${u}-${v}` : `${v}-${u}`;
  }

  return { init, update, removeEdges };
})();
```

- [ ] **Step 2: Start server, open http://localhost:5000, click "Start Game"**

```bash
python app.py
```

Expected: After clicking "Start Game", the network graph appears — grey circles connected by lines, with larger circles for higher-degree nodes. No JS errors in console.

- [ ] **Step 3: Commit**

```bash
git add static/js/network.js
git commit -m "feat: D3.js network visualization — fixed layout, degree-scaled nodes, edge removal"
```

---

## Task 10: Button Panel

**Files:**
- Create: `static/js/buttons.js`

- [ ] **Step 1: Implement static/js/buttons.js**

```javascript
const Buttons = (() => {
  const BUTTON_DEFS = [
    { action: 'spread_spreadable_influencer', label: 'Spread\nSpreadable\nInfluencer' },
    { action: 'spread_spreadable_connector',  label: 'Spread\nSpreadable\nConnector'  },
    { action: 'spread_persuasive_influencer', label: 'Spread\nPersuasive\nInfluencer' },
    { action: 'spread_persuasive_connector',  label: 'Spread\nPersuasive\nConnector'  },
    { action: 'discredit_highdegree',         label: 'Discredit\nHub'                 },
    { action: 'discredit_highbetweenness',    label: 'Discredit\nBridge'              },
  ];

  // Maps action string -> {btn, bar} elements, per player
  const refs = { red: {}, blue: {} };

  function init(onAction) {
    _build('red', 'buttons-red', onAction);
    _build('blue', 'buttons-blue', onAction);
  }

  function _build(player, containerId, onAction) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    BUTTON_DEFS.forEach(({ action, label }) => {
      const btn = document.createElement('button');
      btn.className = `action-btn ${player}-btn`;
      btn.innerHTML = label.replace(/\n/g, '<br>');

      const bar = document.createElement('div');
      bar.className = 'cooldown-bar';
      btn.appendChild(bar);

      btn.addEventListener('click', () => {
        if (!btn.disabled) onAction(player, action);
      });

      container.appendChild(btn);
      refs[player][action] = { btn, bar };
    });
  }

  function updateCooldowns(cooldowns) {
    // cooldowns: { red: { action: seconds_remaining, ... }, blue: { ... } }
    ['red', 'blue'].forEach(player => {
      const cd = cooldowns[player] || {};
      Object.entries(cd).forEach(([action, remaining]) => {
        const ref = refs[player][action];
        if (!ref) return;
        const { btn, bar } = ref;
        const totalCooldown = 10.0; // matches COOLDOWN_DURATIONS
        const fraction = Math.min(1, remaining / totalCooldown);
        bar.style.width = `${fraction * 100}%`;
        btn.disabled = remaining > 0;
      });
    });
  }

  return { init, updateCooldowns };
})();
```

- [ ] **Step 2: Start server, open http://localhost:5000, click "Start Game"**

```bash
python app.py
```

Expected: Two columns of 6 buttons appear — red-tinted on the left, blue-tinted on the right. Labels read "Spread Spreadable Influencer" etc. Buttons are clickable (no cooldown indicator yet without pressing).

- [ ] **Step 3: Commit**

```bash
git add static/js/buttons.js
git commit -m "feat: button panel — 6 actions per player, cooldown progress bars"
```

---

## Task 11: Game Client

**Files:**
- Create: `static/js/game.js`

- [ ] **Step 1: Implement static/js/game.js**

```javascript
(() => {
  const socket = io();

  const startScreen = document.getElementById('start-screen');
  const startBtn = document.getElementById('start-btn');
  const overlay = document.getElementById('overlay');
  const winnerText = document.getElementById('winner-text');
  const finalScores = document.getElementById('final-scores');
  const playAgain = document.getElementById('play-again');
  const timerEl = document.getElementById('timer');
  const scoreRed = document.getElementById('score-red');
  const scoreBlue = document.getElementById('score-blue');

  Buttons.init((player, action) => {
    socket.emit('action', { player, action });
  });

  startBtn.addEventListener('click', () => {
    socket.emit('start_game');
    startScreen.style.display = 'none';
  });

  playAgain.addEventListener('click', () => {
    overlay.classList.add('hidden');
    startScreen.style.display = 'flex';
  });

  socket.on('game_init', ({ network, initial_states, duration }) => {
    Network.init(network);
    Network.update(initial_states);
  });

  socket.on('state', ({ node_states, scores, time_remaining, cooldowns }) => {
    Network.update(node_states);
    Buttons.updateCooldowns(cooldowns);

    scoreRed.textContent = `RED: ${scores.red}`;
    scoreBlue.textContent = `BLUE: ${scores.blue}`;

    const mins = Math.floor(time_remaining / 60);
    const secs = Math.floor(time_remaining % 60).toString().padStart(2, '0');
    timerEl.textContent = `${mins}:${secs}`;
  });

  socket.on('action_result', ({ removed_edges }) => {
    if (removed_edges && removed_edges.length > 0) {
      Network.removeEdges(removed_edges);
    }
  });

  socket.on('game_over', ({ red, blue, S, winner }) => {
    winnerText.textContent = `${winner.toUpperCase()} WINS`;
    winnerText.style.color = winner === 'red' ? '#e84040' : '#4080e8';
    finalScores.textContent = `Red: ${red}  |  Blue: ${blue}  |  Neutral: ${S}`;
    overlay.classList.remove('hidden');
  });
})();
```

- [ ] **Step 2: Commit**

```bash
git add static/js/game.js
git commit -m "feat: game client — SocketIO events, score/timer display, end screen"
```

---

## Task 12: Integration Smoke Test

Manual verification that the full game loop works end-to-end.

- [ ] **Step 1: Start the server**

```bash
python app.py
```

Expected: Server starts on port 5000, no errors.

- [ ] **Step 2: Open http://localhost:5000 in a browser**

Expected: Start screen shows. No console errors.

- [ ] **Step 3: Click "Start Game"**

Expected:
- Start screen dismisses
- Network graph renders (~175 nodes, visible community clusters, a few red and blue nodes)
- HUD shows timer counting down from 2:30
- Score counters show small non-zero values for red and blue
- 6 red buttons on left, 6 blue buttons on right, all enabled

- [ ] **Step 4: Click red and blue buttons and observe**

Expected:
- Clicking a button disables it and shows a cooldown bar filling from right to left
- New nodes change colour on the graph within one tick (~200ms)
- Cooldown bar empties over ~10 seconds; button re-enables

- [ ] **Step 5: Click a "Discredit" button**

Expected:
- Some edges near the targeted node disappear (opacity drops to 0)
- `action_result` event visible in browser console with `removed_edges` list

- [ ] **Step 6: Let the timer expire**

Expected:
- Game-over overlay appears with winner name and final scores
- A JSON file appears in the `games/` directory

- [ ] **Step 7: Verify game log**

```bash
ls games/
cat games/*.json | python -m json.tool | head -40
```

Expected: Valid JSON with `game_id`, `random_seed`, `network`, `initial_states`, `interventions` (entries for each button press), and `outcome`.

- [ ] **Step 8: Click "Play Again"**

Expected: Start screen returns; clicking "Start Game" starts a fresh game with a new network.

- [ ] **Step 9: Run full test suite one final time**

```bash
pytest -v
```

Expected: All 36 tests PASS.

- [ ] **Step 10: Commit**

```bash
git add .
git commit -m "feat: complete MODgame prototype — backend simulation, Flask-SocketIO server, D3.js frontend"
```
