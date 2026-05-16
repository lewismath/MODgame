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
