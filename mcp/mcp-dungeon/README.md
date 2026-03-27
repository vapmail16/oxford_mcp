# MCP Dungeon Explorer

A 2D dungeon game where an **AI agent plays using MCP tools**.
Every move, attack, and item pickup is a tool call — exactly like a real MCP setup.

## What it demonstrates

- Tools defined with name + description + Zod-style schema
- Agent discovers tools at runtime (listTools equivalent)
- Agent reads descriptions to decide what to call
- Tool calls visible in real time on the right panel
- Works with real Claude (Anthropic) OR a scripted demo agent (no API key needed)
- Optional: after each run, **OpenAI** can summarize the tool-call transcript (“session review”)

## Configuration

1. Copy the example env file and edit secrets (never commit `.env` — it is gitignored at the repo root):

```bash
cd mcp-dungeon
cp .env.example .env
```

2. Set at least:

| Variable | Role |
|----------|------|
| `ANTHROPIC_API_KEY` | Powers the dungeon agent (tool use). Without it, the scripted demo runs. |
| `ANTHROPIC_MODEL` | Anthropic model id (e.g. a current Haiku or Sonnet id from Anthropic’s docs). |
| `OPENAI_API_KEY` | Optional — if set, the server sends the run’s tool trace to OpenAI for a short **session review** after the game ends. |
| `OPENAI_MODEL` | Optional — defaults to `gpt-4o-mini`. |
| `PORT` | HTTP port (default `3333`). |

## Run

```bash
cd mcp-dungeon
npm install
npm start
```

Open http://localhost:3333 in your browser.

You can still export variables in the shell instead of using `.env`; `dotenv` loads `mcp-dungeon/.env` on startup.

### Troubleshooting

| Symptom | What to do |
|--------|------------|
| **DEMO MODE** even with a key | Ensure `mcp-dungeon/.env` exists (same folder as `server.js`), contains `ANTHROPIC_API_KEY=...` on one line with no spaces around `=`, then restart. |
| **`EADDRINUSE` / port 3333 in use** | Another `node server.js` is still running, or another app uses 3333. Quit it or run `PORT=3334 npm start`. On macOS: `lsof -i :3333` to see the process. |
| After **win/lose**, the UI jumped back to the **start screen** and cleared the MCP trace | The old **Play Again** button ran a full reset. Use **Continue — view map & MCP trace** to dismiss the overlay only; use **↺ New game** or the header **Reset** when you want a fresh run. |

## The 6 MCP tools

| Tool | What it does |
|---|---|
| `move(direction)` | Navigate north/south/east/west |
| `attack(target)` | Fight an enemy in the current room |
| `pick_up(item)` | Collect an item into inventory |
| `use_item(item)` | Use a potion or equip gear |
| `inspect_room()` | Get full description of current room |
| `check_inventory()` | See carried items and stats |

## The dungeon

4×4 grid. Find the **ancient_key** at (3,1), defeat or avoid enemies,
and escape through the **Iron Door** at (3,3).

## Files

```
mcp-dungeon/
├── server.js       — Game logic, tools, agent loop, Express + WebSocket
├── public/
│   └── index.html  — Canvas dungeon + live MCP tool call panel
└── package.json
```
