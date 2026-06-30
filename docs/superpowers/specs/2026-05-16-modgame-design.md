# MODgame Web Prototype — Design Spec

*2026-05-16*

---

## Overview

A real-time 2-player browser game about information spread, intended as a science exhibit. Red and blue players compete to convert a networked population of agents to their side by seeding messages and disrupting the opponent's spread. A round lasts 2–3 minutes; the player with the most converted nodes at the end wins.

---

## Architecture

```
┌─────────────────────────────────────────┐
│              Browser (single page)       │
│                                         │
│  ┌──────────────┐   ┌────────────────┐  │
│  │  D3.js graph │   │  Button panel  │  │
│  │  (SVG)       │   │  (6×2 buttons) │  │
│  └──────┬───────┘   └───────┬────────┘  │
│         │  state updates    │ actions   │
└─────────┼───────────────────┼───────────┘
          │    WebSocket (Flask-SocketIO)
┌─────────┼───────────────────┼───────────┐
│         ▼                   ▼           │
│  ┌──────────────────────────────────┐   │
│  │          Flask server            │   │
│  │  - receives player actions       │   │
│  │  - validates cooldowns           │   │
│  │  - applies actions to graph      │   │
│  └──────────────┬───────────────────┘   │
│                 │                       │
│  ┌──────────────▼───────────────────┐   │
│  │        Simulation engine         │   │
│  │  - background thread, ~200ms tick│   │
│  │  - SIS dynamics on NetworkX graph│   │
│  │  - emits state each tick         │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

- Single Flask process; simulation runs in a background thread via `socketio.start_background_task`
- Each tick emits a compact state dict: per-node state (S/red/blue), current β/γ, cooldown timers, score
- All game logic lives server-side; the browser only renders and forwards button presses
- Node positions computed once before play begins (force simulation, then frozen)

---

## Network

- **Model:** Stochastic block model via `networkx.stochastic_block_model()`
- **Size:** ~150–200 nodes, 4–6 communities
- **Edge probabilities:** within-community ~0.3, between-community ~0.05
- **Layout:** Force-directed layout computed once at game start; node positions fixed for the duration of play. Community grouping is spatially apparent.

---

## Simulation Model

### Node parameters

Each node is assigned baseline β (transmission rate) and γ (recovery rate) drawn from truncated normal distributions at game start (bounded away from 0 and 1). These persist across the game and can be temporarily modified by player actions.

### SIS dynamics (per tick, ~200ms)

State space per node: **S** (susceptible/neutral), **red**, **blue**.

1. For each susceptible node, sample one infected neighbour at random (if any exist). Attempt transmission using that neighbour's current local β. On success, infect the susceptible node with the neighbour's colour.
2. For each infected node, attempt recovery to S using the node's current local γ.
3. A node can only hold one state. A red node cannot be directly converted to blue — it must recover to S first (neutral-first model).

### Parameter decay

Player action effects on β/γ decay linearly back to baseline over ~10 seconds.

---

## Player Actions

### Button layout (6 buttons per player)

| Button | Action |
|--------|--------|
| 1 | Spread **spreadable** message from **influencer** |
| 2 | Spread **spreadable** message from **connector** |
| 3 | Spread **persuasive** message from **influencer** |
| 4 | Spread **persuasive** message from **connector** |
| 5 | Discredit **high-degree** opponent node |
| 6 | Discredit **high-betweenness** opponent node |

Each button has an independent cooldown timer. A button is unavailable (greyed out) until its cooldown expires.

### Spread actions

Target selection: draw a random sample of ~20% of susceptible nodes (min 5); pick the highest-degree (influencer) or highest-betweenness (connector) node from the sample.

- **Spreadable** — infect the target node with player colour; temporarily elevate β of all its neighbours
- **Persuasive** — infect the target node with player colour; temporarily reduce γ of all its neighbours

### Discredit actions

Target selection: draw a random sample of ~20% of opponent-infected nodes (min 5); pick the highest-degree or highest-betweenness node from the sample.

- Remove a fraction of the target node's edges permanently (edges are deleted from the graph)

---

## Frontend

- **Network:** D3.js SVG. Nodes coloured by state (grey = S, red, blue). Node radius scales with degree. Edge opacity decreases as edges are removed.
- **Buttons:** Two columns of 6 buttons, styled red and blue. Each button shows a cooldown progress indicator. Buttons are non-interactive during cooldown.
- **Score:** Live counts of red / blue / S nodes displayed throughout. Countdown timer visible.
- **End screen:** Full-screen result overlay at game end showing final counts and winner. "Play again" button restarts with a fresh network.

---

## Game Loop

### Setup

1. Server generates network, samples per-node β/γ, seeds initial red and blue nodes, records random seed and initial state
2. Server emits full graph to client; client renders it
3. Both players press "ready"; game starts

### Play

- Simulation thread runs continuously, emitting state updates ~every 200ms
- Button presses arrive as SocketIO events; validated server-side against cooldowns; applied immediately to graph
- Intervention logged to in-memory list on each action

### End

1. Timer expires; simulation stops
2. Final state and intervention log flushed to JSON file in `games/`
3. Server emits game-over event; client shows result overlay

---

## Data Persistence

One JSON file per game, written to `games/` at game end:

```json
{
  "game_id": "2026-05-16T14:32:00",
  "random_seed": 42,
  "network": {
    "nodes": [{"id": 0, "community": 2, "beta": 0.18, "gamma": 0.12}, ...],
    "edges": [[0, 4], [0, 7], ...]
  },
  "initial_states": {"0": "S", "1": "red", "2": "blue", ...},
  "interventions": [
    {"t": 4.2, "player": "red", "action": "spread_persuasive_influencer", "target_node": 47},
    {"t": 9.1, "player": "blue", "action": "discredit_highbetweenness", "target_node": 12}
  ],
  "outcome": {"red": 87, "blue": 63, "susceptible": 50, "winner": "red"}
}
```

Games are fully replayable given the stored network, initial states, interventions, and random seed.

---

## Open Questions

- Exact cooldown duration per button (to be tuned during development)
- Number and distribution of initially infected nodes
- Whether scores are shown live or revealed only at game end
- Visual styling beyond red/blue (fonts, background, node border styles)
