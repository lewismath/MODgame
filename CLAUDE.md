# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MODgame** is a real-time 2-player browser-based game about information spread, intended as a museum/science exhibit running on a large touchscreen or arcade-style setup with physical buttons. Players compete to convert a networked population of agents to their side (red vs blue).

The project is currently in the design/prototyping stage. The only existing file is `misinfo_game_notes.md`, which contains the full concept spec.

## Game Design

**Mechanics:**
- Two simultaneous players act on a shared network in real-time
- Players spread messages (seeding from high-degree or high-betweenness nodes) or disrupt the other side by removing edges ("discrediting" nodes)
- Message choices: *spreadable* (high transmission rate) vs *persuasive* (long infectious period)
- Game ends after a fixed duration; player with most converted nodes wins

**Network/Simulation Model:**
- Stochastic block model with visible community structure
- 2-virus SIS (Susceptible-Infected-Susceptible) dynamics
- Transmission rate ↔ message spreadability; infectious period ↔ persuasiveness

**UI Constraints:**
- Designed for a large screen; network can be moderately sized
- Input via 4–6 physical buttons per player (not node-clicking) — the web prototype should reflect this
- Minimalist aesthetic; reference: [VaxGame](https://github.com/digitalepidemiologylab/VaxGame)

## Running the Prototype

```bash
# Start the server (EVENTLET_NO_GREENDNS=yes required on macOS due to dnspython/trio conflict)
EVENTLET_NO_GREENDNS=yes python app.py
```

Open http://localhost:5000 in a browser. Click "Start Game".

```bash
# Run backend tests
pytest -v
```

## Stack

- **Backend:** Flask + Flask-SocketIO (eventlet), NetworkX, NumPy
- **Frontend:** D3.js 7, Socket.IO 4 (both via CDN)
- **Game logs:** `games/` directory — one JSON file per round

## Architecture

```
game/network.py     — SBM generation, layout, centrality, serialization
game/state.py       — GameState dataclass: node states, cooldowns, scoring
game/simulation.py  — SIS tick (~200ms), parameter decay
game/actions.py     — Spread/discredit targeting and application
game/persistence.py — JSON game log writer
app.py              — Flask-SocketIO server, game loop orchestration
static/js/network.js  — D3.js SVG network renderer
static/js/buttons.js  — Button panel, cooldown progress bars
static/js/game.js     — Socket.IO client, score/timer/end screen
```

## Design Decisions

See `docs/superpowers/specs/2026-05-16-modgame-design-decisions.md` for all design decisions and alternatives considered (network model, SIS conversion rule, button layout, action mechanics, etc.).
