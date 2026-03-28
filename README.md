# Oxford bundle (IT Support Agent + MCP session assets)

This folder is a **standalone copy** of the Oxford-relevant parts of the cohort repo:

| Path | Purpose |
|------|---------|
| `capstone_project/` | Full-stack IT Support Agent (FastAPI backend, React UI, TypeScript MCP stdio server, RAG, tests, docs). |
| `mcp/` | Oxford MCP session materials: session plan, dungeon demo, architecture HTML, slides/talking points. |


## First-time setup

1. **Backend** (uses your current `python3` / `pip` — no virtualenv required)

   ```bash
   cd capstone_project/backend
   python3 -m pip install -r requirements.txt
   # If .env is not present: cp .env.example .env  # then edit (OPENAI_API_KEY, etc.)
   ```

   Optional: create a venv (`.venv`) first if you prefer an isolated environment; the commands below stay the same once it is activated.

2. **Frontend**

   ```bash
   cd capstone_project/frontend
   npm install
   ```

3. **MCP server (TypeScript stdio)** — required for the real MCP path unless you set `USE_SIMULATED_MCP=1` in backend `.env`.

   ```bash
   cd capstone_project/mcp_server
   npm install
   ```

## Run (typical dev)

The Python package is named `backend`. **`import backend` only works if `capstone_project/` is on `PYTHONPATH`**, or you use the entry points below.

**Terminal 1 — API** (pick one)

From **`capstone_project/`** (recommended):

```bash
cd capstone_project
python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

From **`capstone_project/backend/`** (after `pip install`, same folder): use **`main:app`**, not `backend.main:app` — otherwise Python tries to import `backend` before `main.py` runs and fails.

```bash
cd capstone_project/backend
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

(`python3 -m uvicorn` uses the same interpreter you installed dependencies into. If you use a venv, activate it first, then run the same command. Use a space before the port number: `--port 8000`.)

**MCP (Agentic chat):** You do **not** start a separate MCP server process. After `npm install` in `capstone_project/mcp_server`, the backend spawns `npx tsx src/index.ts` over stdio when a tool runs. Set **`USE_SIMULATED_MCP=1`** in `backend/.env` only if you want in-process Python stubs and no Node (see setup step 3 above).

**Terminal 2 — UI**

```bash
cd capstone_project/frontend
npm run dev
```

Open the URL shown (often `http://localhost:5173`). The backend defaults to `http://localhost:8000`.

## KB RAG (Qdrant) ingestion

Agentic chat uses **two** retrieval paths: **KB** (markdown in Qdrant collection `it_support_kb`) and **DB** (SQLite messages). If you see `kb:Collection it_support_kb not found` or `kb_len: 0` while DB RAG works, the vector index is missing or empty — run ingestion.

**What gets indexed:** Markdown under `capstone_project/docs/backend/rag/docs/` (VPN guides, Wi‑Fi SOPs, etc.), chunked and embedded with the model in `backend/.env` (e.g. `OPENAI_API_KEY` / `EMBEDDING_MODEL`).

**Where it is stored:** Local disk mode uses `backend/qdrant_storage/` (relative `QDRANT_PATH` in `backend/.env` resolves under `backend/`, not your shell cwd — see `backend/rag/config_paths.py`). Each checkout has **its own** store; copying code does **not** copy embeddings.

**Command** (from `capstone_project/` — same layout in this bundle and in the main cohort repo):

```bash
cd capstone_project
python3 -m backend.rag.ingest --reset
```

`--reset` deletes the existing local Qdrant data for that tree, then rebuilds `it_support_kb`. Omit `--reset` only if you are appending to an existing compatible index (same embedding dimensions).

**Two trees on disk:** If you use both this bundle and the parent cohort project, run ingestion in **each** when you set up or after a fresh copy without `qdrant_storage`:

| Tree | Example path |
|------|----------------|
| This Oxford bundle | `.../oxford_capstone/capstone_project/` |
| Main cohort repo (sibling) | `.../genai_cohort_5/capstone_project/` |

```bash
# Example: cohort repo (adjust if your folder layout differs)
cd ../genai_cohort_5/capstone_project
python3 -m backend.rag.ingest --reset
```

**Processing flow (for automation or docs):** install backend deps → configure `backend/.env` → `npm install` in `mcp_server` if using real MCP → run the ingest command above → start API/UI as in [Run](#run-typical-dev).

## Troubleshooting / issue log

| Date | What went wrong | How to avoid |
|------|-------------------|--------------|
| 2026-03-25 | `pip install` failed: `httpx==0.26.0` conflicts with `mcp` (`httpx>=0.27.1`). | Use `httpx>=0.27.1` in `backend/requirements.txt` (pinned range in file). |
| 2026-03-25 | `uvicorn main:app` from `backend/` raised `ModuleNotFoundError: No module named 'backend'`. | `main.py` prepends `capstone_project` to `sys.path`; from `backend/` use `python3 -m uvicorn main:app` (not `backend.main:app`). Or `cd capstone_project` and use `backend.main:app`. |
| 2026-03-25 | After loosening deps, `pytest` failed during collection: `Package` has no `obj` (pytest-asyncio + pytest 8.0). | Use `pytest>=8.2` and `pytest-asyncio>=0.24` in `backend/requirements.txt`; pin `mcp>=1.26` with matching `uvicorn>=0.31.1` and `python-multipart>=0.0.9`. |
| 2026-03-25 | KB RAG missing: `Collection it_support_kb not found` after moving/copying the repo. | Run `python3 -m backend.rag.ingest --reset` from `capstone_project/` (see [KB RAG](#kb-rag-qdrant-ingestion)). Each checkout needs its own `backend/qdrant_storage/`. |
| 2026-03-25 | `test_response_agent_formats_ticket_only_response` failed: custom `ticket_result.message` omitted `ticket_id` from the formatted string. | `ResponseAgent.format_response` now appends `**Ticket #{id}**` when the id is not already in the message text. |
| 2026-03-25 | `test_rag_agent_high_confidence_for_good_match` sometimes failed: real LLM confidence scores vary run-to-run. | Test mocks `calculate_confidence` at 0.85 so the suite stays deterministic. |
| 2026-03-26 | Push to GitHub blocked: folder was not a git repo; `gh auth status` reported invalid token in keyring for the active account. | Run `git init` at bundle root (or clone an empty repo), commit with a root `.gitignore` that ignores `**/.env`, then `gh auth login -h github.com` and `gh repo create … --push` or add `origin` and `git push -u origin main`. |
| 2026-03-27 | After successful `pytest`, teardown printed `AttributeError: '_thread.RLock' object has no attribute '_recursion_count'` from `multiprocess.resource_tracker` on Python 3.12. | Treat as non-blocking teardown noise (tests still pass). Keep `pytest-xdist` / `multiprocess` updated; if noisy in CI, run without worker/process plugins for local smoke runs. |
| 2026-03-27 | Re-observed at end of full suite run (`206 passed, 1 skipped`) as the same `multiprocess.resource_tracker` teardown warning on Python 3.12. | Keep mitigation unchanged: non-blocking; monitor plugin/runtime upgrades and suppress by avoiding process plugins for quick local runs when needed. |

## Optional: MCP Dungeon (teaching demo)

```bash
cd mcp/mcp-dungeon
# If .env is missing: cp .env.example .env  # optional keys; scripted demo works without
npm install
npm start
```

See `mcp/mcp-dungeon/README.md` and `mcp/OXFORD_MCP_SESSION_PLAN.md`.

## Syncing from the main cohort repo

This tree was copied without `node_modules`, virtualenvs, or `qdrant_storage`. `.env` files may be copied separately from `genai_cohort_5` when you want matching keys locally. To refresh code from the cohort repo, re-run `rsync` with those excludes, then copy `.env` again if needed. After a sync, re-run **[KB RAG ingestion](#kb-rag-qdrant-ingestion)** in this bundle if you need the local vector index (it is not copied by rsync).

## Git

This bundle is **not** automatically a git repo. To version it separately: `git init` here and add your own `.gitignore` — **always ignore `.env`** so keys are never pushed.
