# MODgame Design Decisions

Decisions made during brainstorming session 2026-05-16. Each entry lists the chosen option and the alternatives considered, so any decision can be revisited.

---

## Tech Stack

**Chosen:** Python + web frontend (Flask-SocketIO backend, D3.js frontend)

Alternatives considered:
- Pure JavaScript — simulation and visualization both in browser, no server needed, simpler deployment
- Python notebook first — prototype simulation in Jupyter to validate model, then wire up web frontend

---

## Real-time Architecture

**Chosen:** Flask-SocketIO + D3.js

- Flask-SocketIO runs simulation in a background thread (~200ms tick), emitting graph state via WebSocket
- D3.js renders fixed-position SVG network; button presses sent back over same socket
- Node positions computed once at game start and fixed for the duration of play

Alternatives considered:
- FastAPI + native WebSockets + vis.js — cleaner async model, but more manual protocol handling
- Flask + Server-Sent Events + D3.js — simpler (no WebSocket library), but button feedback has slightly higher latency

---

## SIS Conversion Model

**Chosen:** Neutral first — a node must recover to susceptible (S) before it can be converted to the other side. Nodes cycle: red → S → blue → S → red.

Alternatives considered:
- Superinfection — red nodes can be directly converted to blue with some probability; faster swings
- Contested/blocked — competing virus has reduced transmission probability against already-infected nodes

---

## Node Parameters (β and γ)

**Chosen:** Per-node heterogeneous values drawn from truncated normal distributions at game start. These are each node's baseline values; player actions can temporarily shift neighbours' parameters.

Alternatives considered:
- Homogeneous — all nodes share the same β and γ
- Community-level — parameters vary by community but are uniform within each community

---

## Player Action Interface

**Chosen:** One button = one fully-specified action (no two-step selection)

Alternatives considered:
- Two-step selection — first button selects action type, second selects target class; more deliberate but slower

**Button layout (6 buttons per player):**

| Button | Action |
|--------|--------|
| 1 | Spread **spreadable** message from **influencer** (high-degree) |
| 2 | Spread **spreadable** message from **connector** (high-betweenness) |
| 3 | Spread **persuasive** message from **influencer** |
| 4 | Spread **persuasive** message from **connector** |
| 5 | Discredit **high-degree** opponent node |
| 6 | Discredit **high-betweenness** opponent node |

---

## Message Mechanics

**Chosen:** Seed a node + local parameter shift for that node's neighbours

- Seeding a node infects it with the player's colour
- Spreadable message → temporarily elevates β of the seeded node's neighbours (~10s linear decay)
- Persuasive message → temporarily reduces γ of the seeded node's neighbours (~10s linear decay)

Alternatives considered:
- Seed only — infects a node but doesn't modify any parameters
- Global boost — temporarily raises β or lowers γ for all of that player's infected nodes

---

## Spread Targeting

**Chosen:** Random sample of nodes, pick highest-degree or highest-betweenness from sample (not strictly the global highest)

- Spread from influencer → highest-degree susceptible node in sample
- Spread from connector → highest-betweenness susceptible node in sample

---

## Discredit Targeting

**Chosen:** Two buttons: target high-degree OR high-betweenness opponent-infected node (from random sample)

- Discredit removes a fraction of the target node's edges permanently
- Target selected as highest-degree (or highest-betweenness) opponent node in a random sample

Alternatives considered:
- Always target the single highest-degree opponent node — predictable but less varied
- Random from top-N opponent nodes — more randomness

---

## Action Limiting

**Chosen:** Per-button cooldown (each button has its own timer, resets after use)

Alternatives considered:
- Shared action budget — pool of action points regenerating over time
- Fixed action interval — one action per player per N seconds regardless of button

---

## Network

**Chosen:** Stochastic block model, ~150–200 nodes, 4–6 communities

- High within-community edge probability (~0.3), low between-community probability (~0.05)
- Community membership visible in layout (nodes grouped spatially)
- Fixed layout computed once at game start

Alternatives considered:
- Small (~50–80 nodes, 3–4 communities) — faster, easier to read, good for prototyping
- Large (400+ nodes, 6–8 communities) — impressive visually, but individual nodes hard to distinguish

---

## Round Duration

**Chosen:** Short — 2–3 minutes

Alternatives considered:
- Medium — 4–5 minutes
- Long — 8–10 minutes

---

## Data Persistence

**Chosen:** One JSON file per game, written to `games/` directory at game end

Fields stored:
- `game_id` — ISO timestamp
- `random_seed` — for full reproducibility of SIS stochastic dynamics
- `network` — nodes (with community, baseline β, baseline γ) and edges
- `initial_states` — per-node starting state (S / red / blue)
- `interventions` — list of `{t, player, action, target_node}` logged in real time
- `outcome` — final counts and winner

---

## Open Questions / Not Yet Decided

- Exact cooldown durations per button
- Initial infected node count and distribution (how many nodes start red/blue vs susceptible)
- Win condition display and end-game screen design
- Whether to show real-time scores during play or reveal only at end
- Visual style / colour scheme beyond red vs blue
