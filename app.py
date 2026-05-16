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
