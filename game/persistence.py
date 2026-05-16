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
