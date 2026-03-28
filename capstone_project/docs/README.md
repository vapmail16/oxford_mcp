# IT Support Agent - GenAI Cohort 5 Capstone Project

## 🎯 Project Overview

An intelligent IT Support Agent built using **Test-Driven Development (TDD)** principles. This application helps employees diagnose issues, search the knowledge base, create tickets, and execute fixes—all powered by RAG (Retrieval-Augmented Generation), LangGraph agents, and MCP tools.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React Frontend                      │
│         (Chat UI + Ticket Dashboard)                 │
└────────────────────┬────────────────────────────────┘
                     │ HTTP / SSE streaming
┌────────────────────▼────────────────────────────────┐
│              FastAPI Backend                         │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │           LangGraph Orchestrator             │   │
│  │                                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │   │
│  │  │ Triage   │ │   RAG    │ │  Ticket     │  │   │
│  │  │  Agent   │→│  Agent   │ │  Agent      │  │   │
│  │  └──────────┘ └──────────┘ └─────────────┘  │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  Chroma Vector   │  │    MCP Tool Server       │ │
│  │  Store (RAG)     │  │  (tickets, sys-check,    │ │
│  │                  │  │   password-reset, logs)  │ │
│  └──────────────────┘  └──────────────────────────┘ │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │        SQLite  (tickets + chat history)      │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 🧪 **Built with Test-Driven Development (TDD)**

This project follows **gold standard TDD** practices:

### **Red → Green → Refactor**

1. **🔴 RED**: Write a failing test first
2. **🟢 GREEN**: Write minimal code to pass the test
3. **🔵 REFACTOR**: Improve code while keeping tests green

**Current Status**: 🟢 **ACTIVE DEVELOPMENT (core flows implemented)**
- ✅ FastAPI + React demo workflow is running
- ✅ Unit/integration suite passes locally (`206 passed, 1 skipped`)
- ✅ KB RAG + DB RAG + agentic MCP demo tracks available

### **Why TDD?**

- **Confidence**: Every feature has tests before deployment
- **Quality**: Bugs caught early in development
- **Documentation**: Tests describe how the system works
- **Refactoring**: Safe to improve code with test coverage
- **Design**: Forces thinking about interfaces before implementation

---

## 📁 Project Structure

```
it-support-agent/
├── backend/
│   ├── database/          # (To be implemented - TDD Green phase)
│   │   ├── __init__.py
│   │   ├── models.py      # Ticket, Message, Enums
│   │   └── crud.py        # Database operations
│   ├── rag/               # (To be implemented)
│   │   ├── __init__.py
│   │   ├── ingest.py      # Document ingestion
│   │   ├── retriever.py   # RAG retrieval & generation
│   │   └── docs/          # Knowledge base documents
│   │       ├── wifi_troubleshooting.md
│   │       ├── vpn_setup_guide.md
│   │       ├── password_reset_sop.md
│   │       ├── laptop_setup_checklist.md
│   │       ├── common_error_codes.md
│   │       └── software_install_policies.md
│   ├── agents/            # (To be implemented)
│   │   ├── __init__.py
│   │   ├── orchestrator.py    # LangGraph orchestrator
│   │   ├── triage_agent.py    # Issue classification
│   │   ├── rag_agent.py       # Knowledge base search
│   │   ├── ticket_agent.py    # Ticket creation
│   │   └── response_agent.py  # Response formatting
│   ├── mcp_server/        # (To be implemented)
│   │   ├── server.ts
│   │   └── tools/
│   ├── main.py            # FastAPI app (To be implemented)
│   ├── requirements.txt   # ✅ Created
│   └── .env.example       # ✅ Created
├── frontend/              # (Week 8)
│   ├── src/
│   │   ├── components/
│   │   └── App.jsx
│   └── package.json
├── tests/                 # ✅ Test infrastructure created
│   ├── conftest.py        # ✅ Shared fixtures
│   ├── unit/              # ✅ Unit tests
│   │   ├── test_database_models.py  # ✅ 22 tests written (Red phase)
│   │   ├── test_database_crud.py    # (Next)
│   │   ├── test_rag_ingest.py
│   │   ├── test_rag_retriever.py
│   │   ├── test_agent_triage.py
│   │   ├── test_agent_rag.py
│   │   ├── test_agent_ticket.py
│   │   └── test_agent_response.py
│   ├── integration/       # Integration tests
│   │   ├── test_rag_pipeline.py
│   │   ├── test_agent_orchestrator.py
│   │   └── test_api_endpoints.py
│   ├── e2e/               # End-to-end tests
│   │   └── test_chat_workflows.py
│   └── ai_quality/        # AI quality tests
│       ├── test_ragas_metrics.py
│       └── test_hallucination_detection.py
├── IT_SUPPORT_TDD_SPEC.md      # ✅ TDD specification
├── HOW_IT_WORKS.md             # ✅ Runtime architecture and flow notes
├── it_support_capstone_plan.md # ✅ Original plan
├── pytest.ini                  # ✅ Pytest configuration
├── .gitignore                  # ✅ Created
├── docker-compose.yml          # (Week 10)
└── README.md                   # ✅ This file
```

---

## 🚀 Local development setup

### Command cheat sheet (copy-paste)

Run everything from the **`capstone_project/`** directory unless noted. Use **`pyenv shell 3.12.0`** (or your Python) if you rely on pyenv.

```bash
# Go to project root
cd capstone_project

# Python deps (once per venv)
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt

# Env: copy template and set OPENAI_API_KEY (required for embeddings + chat LLM)
cp backend/.env.example backend/.env
# Edit backend/.env — at minimum OPENAI_API_KEY=sk-...

# --- RAG (KB) setup: ingest markdown → Qdrant, then smoke-test retrieval ---
# 1) Build or refresh the index (needs OPENAI_API_KEY in backend/.env)
python -m backend.rag.ingest --reset

# 2) Verify retrieval without starting the API (prints first ~400 chars of context)
python -c "import backend.env_bootstrap; from backend.rag.retriever import get_rag_context; print(get_rag_context('VPN error 422', k=3)[0][:400])"

# --- DB RAG (structured): tickets + chat messages → Qdrant collection `it_support_db` ---
# Rebuilds that collection on each request (demo). Needs OPENAI_API_KEY + SQLite data (e.g. chat/tickets).
python -c "import backend.env_bootstrap; from backend.database import SessionLocal; from backend.rag.db_retriever import get_db_rag_context; db=SessionLocal(); ctx, src = get_db_rag_context(db, 'VPN or password themes', k=3); db.close(); print('sources:', src); print(ctx[:500] if ctx else '(no rows — use the app to create tickets/messages first)')"

# --- API ---
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# --- Frontend (new terminal) ---
cd frontend
npm install
npm run dev
# App: http://localhost:5173  →  API: http://localhost:8000

# --- Tests (from capstone_project/) ---
pytest tests/unit -q
```

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (frontend + optional TypeScript MCP server)
- **OpenAI API key** (or configure Ollama in `backend/.env` for local models)

### 1. Backend (FastAPI)

From the **`capstone_project/`** directory (not `backend/`):

```bash
cd capstone_project
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt

cp backend/.env.example backend/.env
# Edit backend/.env: set OPENAI_API_KEY, optionally MODEL_PROVIDER / OLLAMA_*, QDRANT_PATH
# Agentic MCP uses real stdio by default; set USE_SIMULATED_MCP=1 only to skip Node.
```

`backend/env_bootstrap.py` loads **`backend/.env`** automatically when you run the app or pytest, so you do not need to export variables manually for normal use.

**Run the API** (also from `capstone_project/`):

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET http://localhost:8000/health`
- Chat + demo tracks: `POST http://localhost:8000/chat`
- Teaching lab: routes under `/teaching/...`

**Qdrant (KB RAG):** relative `QDRANT_PATH` in `.env` resolves under **`backend/`** (see `backend/rag/config_paths.py`), e.g. `backend/qdrant_storage`. (Re)build the index with `python -m backend.rag.ingest --reset`.

**DB RAG (`demo_track`: `rag_db`):** `backend/rag/db_retriever.py` embeds recent **tickets** and **messages** from SQLite into Qdrant collection **`it_support_db`** (separate from the markdown KB). Each request deletes and rebuilds that collection for predictable demos; use the chat/ticket flows first so the DB is not empty. Tests: `pytest tests/unit/test_db_rag_retrieval.py tests/unit/test_chat_demo_router.py -q`.

**Real MCP (default for Agentic chat):** `cd mcp_server && npm install`; ensure `npx` is on `PATH`. The backend calls the TypeScript MCP server over stdio for each tool. Set **`USE_SIMULATED_MCP=1`** in `backend/.env` only if you cannot run Node (in-process Python stubs). Pytest sets `USE_SIMULATED_MCP=1` automatically so CI does not spawn `npx`.

**Agentic MCP (`demo_track`: `agentic_mcp`) — talking points:**

| Question | Short answer |
|----------|----------------|
| **Why an MCP server?** | One protocol so tools are implemented once and invoked from Python (or other clients) over stdio. |
| **What runs for each chat?** | **`run_mcp_three_agent_pipeline`**: `agent_triage` → **Python RAG** (same `get_rag_context` + `get_db_rag_context` as `rag_kb` / `rag_db`) → `agent_log_ticket` + SQLite → `agent_compose_response` (MCP); optional **LLM** merge when retrieval returns text. See `mcp_trace.steps`. |
| **Where is simulation?** | Only when **`USE_SIMULATED_MCP=1`** or `ActionAgent(use_real_mcp=False)`. Default in production is **real stdio**. |
| **Best prompts** | e.g. VPN disconnect, password reset — you should see three steps in `mcp_trace` and a `ticket_id` when the DB is available. |

### 2. Frontend (Vite + React)

```bash
cd capstone_project/frontend
npm install
npm run dev
```

Opens **http://localhost:5173** with API calls proxied to port **8000** (`/chat`, `/tickets`, `/health`, `/teaching`).

### 3. Tests

From `capstone_project/` with the venv activated:

```bash
pytest
```

`pytest.ini` sets `pythonpath = .` so `import backend` works without setting `PYTHONPATH`. For a quick smoke:

```bash
pytest tests/unit/test_chat_demo_tracks.py tests/unit/test_teaching_api_basics.py -q
```

---

## 📖 Documentation

- **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)**: Current runtime flow and file map
- **[IT_SUPPORT_TDD_SPEC.md](IT_SUPPORT_TDD_SPEC.md)**: TDD testing specification
- **[it_support_capstone_plan.md](it_support_capstone_plan.md)**: Original plan and milestone intent

---

## 🧪 Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Priority P0 (critical) tests
pytest -m priority_p0

# Database tests
pytest -m database

# AI quality tests (slower)
pytest tests/ai_quality/ --slow
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=backend --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Current Test Statistics

- **Total Tests**: 207
- **Passing**: 206
- **Skipped**: 1
- **Last Full Run**: local `pytest -q` on 2026-03-28

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite + Tailwind CSS |
| API | FastAPI + chat/ticket endpoints |
| Orchestration | LangGraph-style multi-agent flow + chat demo router |
| RAG | LangChain + Qdrant |
| Embeddings | OpenAI / nomic-embed-text |
| LLM | OpenAI GPT-4o / Ollama |
| MCP | TypeScript MCP SDK |
| Database | SQLite + SQLAlchemy |
| Testing | pytest + pytest-cov + RAGAS |
| Deployment | Local dev setup (Docker optional) |

---

## 📝 Development Workflow (TDD)

### For Each New Feature:

1. **Write Test First (Red)** 🔴
   ```bash
   # Create test file
   touch tests/unit/test_new_feature.py

   # Write failing test
   # Run and verify it fails
   pytest tests/unit/test_new_feature.py -v
   ```

2. **Implement Code (Green)** 🟢
   ```bash
   # Write minimal code to pass test
   # Run test again
   pytest tests/unit/test_new_feature.py -v

   # Expected: Test passes ✅
   ```

3. **Refactor (Blue)** 🔵
   ```bash
   # Improve code quality
   # Run tests to ensure nothing broke
   pytest tests/unit/test_new_feature.py -v
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: Add new feature (TDD)"
   ```

---

## 🎯 Current Status & Next Steps

### ✅ Completed

1. Database models/CRUD, RAG ingestion/retrieval, and chat tracks are implemented
2. Agentic MCP pipeline is integrated with ticket creation + trace output
3. Frontend demo menu/track UX and teaching routes are wired
4. Full test suite is passing locally (with one intentional skip)

### 📋 Next Actions

1. Keep docs in sync with runtime behavior and endpoint contracts
2. Add focused tests for any new demo-track behavior before implementation
3. Improve deployment/ops guidance once target hosting is finalized

---

## 📊 Project Milestones

- [x] Core API, DB, and retrieval pipelines implemented
- [x] Agentic MCP demo track and tool orchestration implemented
- [x] Frontend chat demo tracks integrated
- [x] Teaching pipeline routes included
- [ ] Deployment hardening and environment-specific runbooks

---

## 🤝 Contributing

This project follows strict TDD practices:

1. **Never write production code without a failing test**
2. **Write the simplest code to pass the test**
3. **Refactor only when tests are green**
4. **All commits must have passing tests**
5. **Code coverage must be >= 90%**

---

## 📄 License

MIT License - GenAI Cohort 5 Capstone Project

---

## 🙏 Acknowledgments

- GenAI Cohort 5 curriculum
- Test-Driven Development principles from Kent Beck
- RAG and LangChain community
- pytest and testing best practices

---

## 🐛 Known Issues

### Issue log (operational)

| Date | What went wrong | How to avoid next time |
|------|-----------------|-------------------------|
| 2026-03-25 | Agentic RAG replies did not show **which** docs/tickets were used. | **`Citations (retrieval):`** block in compose (`rag_kb_sources` / `rag_db_sources`); LLM finalize prompt requires a **Sources** line using the same labels. |
| 2026-03-25 | Agentic MCP had no **RAG**; other tracks had KB/DB retrieval. | Pipeline now runs **KB + DB retrieval** after triage (`agentic_rag_retrieval.py`), passes excerpts into `agent_compose_response`, optional **`agentic_reply_finalize`** LLM merge; `mcp_trace` includes `agent_retrieve_kb_db` (`python_rag`). |
| 2026-03-25 | Agentic MCP **compose** step only said “IT will email you” with no guidance. | Added `backend/chat_demo/compose_support_reply.py` (category + keyword bullets) and mirrored logic in `mcp_server` `agent_compose_response` for real stdio. |
| 2026-03-25 | `mcp-dungeon` victory overlay **Play Again** called full `resetGame()` → start screen + cleared MCP tool log before demos could show the trace. | Primary action is **Continue — view map & MCP trace** (dismiss overlay only); **New game** / header **Reset** perform full reset. |
| 2026-03-25 | Agentic MCP defaulted to **in-process simulation** unless `USE_REAL_MCP=1`. | **Default is now real stdio MCP** (`mcp_server` + `npx`); `USE_SIMULATED_MCP=1` or `USE_REAL_MCP=0` opts into Python stubs; pytest forces `USE_SIMULATED_MCP=1`. |
| 2026-03-24 | `/chat` **Agentic MCP** track still called `ActionAgent.execute_action` (one LLM tool pick + one MCP call); cohort wanted three ordered agents: triage → ticket → respond, each via MCP. | Implemented `backend/chat_demo/mcp_multi_agent_pipeline.py` (`agent_triage`, `agent_log_ticket`, `agent_compose_response`) + SQLite `create_ticket` in the ticket step; extended MCP TS server and `ActionAgent._simulate_mcp_tool`; updated router + unit tests (`test_mcp_multi_agent_pipeline.py`). |
| 2026-03-24 | `fastapi.testclient.TestClient` failed with httpx 0.28 (`unexpected keyword argument 'app'` / ASGITransport sync context). | For teaching API tests, call the FastAPI handler directly with injected `db` + mock LLM instead of relying on Starlette TestClient + httpx edge cases. |
| 2026-03-24 | `main.py` used `from database import` while pytest imports `backend.main`, causing `ModuleNotFoundError: database`. | Use `from backend.database import` (and `from backend.rag`) so `uvicorn backend.main:app` and pytest share the same import path from repo root. |
| 2026-03-25 | Teaching UI used a separate dark theme instead of the capstone landing/chat look. | Reuse `LandingPage.css` patterns (`hero`, `agents-section`, `agent-card`, `cta-button`) and add only small overrides in `TeachingPipeline.css`. |
| 2026-03-25 | DELETE success could not return `flow_steps` with HTTP 204 (no body). | Teaching DELETE returns **200 + JSON** with `flow_steps` and a note that RFC often uses 204 without a body. |
| 2026-03-24 | API basics lab looked “washed out”: descriptions, deterministic path, and buttons used slate/grey text. | In `TeachingPipeline.css`, set readable body copy to `#111827` (hero, cards, flow summary/detail, arch controls, method badges); keep gradient primary buttons with white labels. |
| 2026-03-25 | Main-chat demo plan included a fourth track (“RAG structured” over DB). | Superseded: **`rag_db`** is implemented (`backend/rag/db_retriever.py`, Qdrant `it_support_db`). Oxford may still **skip** that button live for a shorter story (`mcp/OXFORD_MCP_SESSION_PLAN.md`). |
| 2026-03-25 | (log) | Main `/chat` demo shipped: `backend/chat_demo/` (`tracks`, `plain_llm`, `router`), `ChatRequest.demo_mode` / `demo_track`, `ChatResponse.presenter` / `mcp_trace`, `Chatbot.tsx` demo strip. |
| 2026-03-25 | `TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'` when starting uvicorn; pip also reported Starlette 1.x vs FastAPI 0.109. | **Pin `starlette>=0.35.0,<0.36.0`** next to `fastapi==0.109.0` in `requirements.txt`. After installing `mcp` or other packages, run `pip install -r backend/requirements.txt` to reconcile. The `_captured_signals` / partial import trace is a **secondary** uvicorn reload crash while imports fail. |
| 2026-03-25 | Root `README.md` and `mcp/OXFORD_MCP_SESSION_PLAN.md` still referenced `mcp/sample documents/` after that folder was removed. | List actual `mcp/` files (PDF/PPTX/DOCX/HTML) in docs; grep for `sample documents` when pruning folders. |
| 2026-03-25 | `ai_agents/langgraph_training_guide.md` used a fixed cohort3 path and `ai_agents_demo` (folder no longer in repo). | Use a generic lab directory (e.g. `~/langgraph_lab`) in setup steps so the guide works for any machine. |
| 2026-03-25 | `mcp/mcp-dungeon` needed `.env` loading and configurable `ANTHROPIC_MODEL` / optional OpenAI transcript review. | Use `dotenv` + `.env.example`; keep real keys only in `.env` (gitignored). |
| 2026-03-25 | `load_dotenv()` without a path depended on shell cwd, so `backend/.env` was ignored when running `uvicorn` from `capstone_project`. | Centralize loading in `backend/env_bootstrap.py`; import it from `main.py` and `conftest.py`; set `pythonpath = .` in `pytest.ini`. |
| 2026-03-25 | After sending a common question, the chatbot hid the welcome + demo tracks with no way to return. | Add **Back to menu** — clears thread and session so the full welcome screen returns; keep 📋 for inline common questions only. |
| 2026-03-25 | Free-text with no KB hit only returned static `generate_simple_response` — felt non-agentic. | **Ticket escalation** (`ticket_escalation.py`): if KB empty and message looks urgent/actionable → create real SQLite ticket + priority + dummy email line; `demo_track` `agentic_ticket` + `ticket_id` in API. |
| 2026-03-25 | Welcome UI showed demo tracks and common questions at once; users wanted **track → questions → answer**. | `Chatbot.tsx`: `DEMO_SECTIONS` with per-track questions; step 1 = tracks only, step 2 = questions; **Back to tracks** between steps; **← Back to menu** clears chat. |
| 2026-03-25 | **Direct LLM** and RAG paths could answer general knowledge (e.g. geography), undermining the IT-support story. | Add `backend/chat_demo/guardrails.py` (`is_clearly_non_it`, refusal copy); **system prompt** + optional regex fast-path in `plain_llm.py`; router early-return + KB/DB prompt lines for IT-only scope. Extend tests before shipping behavior changes. |
| 2026-03-25 | `generate_simple_response` only matched VPN when **"422"** appeared, so “steps to set up VPN” hit the **generic greeting** despite listing VPN in capabilities. | Add a general **`elif "vpn" in message_lower`** branch (after the 422-specific block) with AnyConnect/setup steps; unit tests in `tests/unit/test_generate_simple_response.py`. |
| 2026-03-25 | User chose **Direct LLM** but follow-up messages skipped **`demo_track`** (`Chatbot.tsx` only set it when `messages.length === 0`). Backend then used **legacy** routing (RAG → empty KB → `generate_simple_response`) — not “KB mode,” just missing track. | Persist **`activeDemoTrack`** when a track is chosen / preset is sent; send `trackFromWelcome ?? activeDemoTrack` on every `/chat` request (excluding `menu`). |
| 2026-03-25 | KB RAG looked “broken”: `QDRANT_PATH=./qdrant_storage` resolved to **`capstone_project/qdrant_storage`** (wrong cwd), holding a **3-dim** test collection vs **OpenAI 1536-dim** embeddings — `get_rag_context` raised dimension mismatch. **`backend/qdrant_storage`** had the real index (~14 points). | **`backend/rag/config_paths.py`**: resolve relative `QDRANT_PATH` under **`backend/`**; use **`FakeEmbeddings`** in tests (LangChain rejects `MagicMock`); gitignore `qdrant_storage/` dirs. Re-ingest with `python -m rag.ingest --reset` if collections are stale. |
| 2026-03-25 | `python -m backend.rag.ingest` failed: **`OPENAI_API_KEY` unset** because the CLI never loaded **`backend/.env`** (unlike `main.py`). | Import **`backend.env_bootstrap`** at the top of `ingest.py` / `retriever.py` so ingestion and retrieval CLI pick up the same env as uvicorn. |
| 2026-03-25 | **`RuntimeWarning: backend.rag.ingest found in sys.modules`** when running `python -m backend.rag.ingest`; **`QdrantClient.__del__`** sometimes logged `ImportError` on exit. | **`backend/rag/__init__.py`**: lazy exports via **`__getattr__`** (don’t import `ingest` at package import). **`ingest` CLI**: call **`vectorstore.client.close()`** after ingest. |
| 2026-03-25 | DB RAG (`get_db_rag_context`) needed the same **`.env` loading** as KB ingest when used outside `main.py`; router fallback on retrieval errors was untested. | Import **`backend.env_bootstrap`** in **`db_retriever.py`**; add **`test_rag_db_when_get_db_rag_raises_falls_back_to_simple_response`** + source-label test in **`test_db_rag_retrieval.py`**. |
| 2026-03-25 | Demo strip said Agentic MCP was **“simulated or real”** while the cohort story emphasizes **real MCP**. | **`Chatbot.tsx`**: Agentic MCP description → *“via real MCP (stdio server)”*; still set **`USE_REAL_MCP=1`** + `mcp_server` `npm install` for actual stdio. |
| 2026-03-25 | Chat input felt narrow; presenter JSON didn’t explain **why** a tool was picked (agentic story). | **`ActionAgent`**: `selection_method` (`llm` vs `rule_based`) + `params_used` on success; **`router`**: `mcp_trace.tool_selection` + `how_agentic_works`; **`Chatbot.tsx`**: human-readable “How the agent picked the tool”; **`Chatbot.css`**: wider panel (`min(480px,…)`), `min-width:0` on input row. Tests: **`test_action_agent_tool_selection.py`**. |
| 2026-03-25 | Meta questions (“list all MCP tools”) showed **(UNKNOWN)** in the presenter because **`tool_used`** was null when LLM returned `tool: none` — no MCP call. | **`no_tool_match`** response + **`mcp_trace`** hints + amber UI; **`where_is_ai`** string; README table for Oxford Q&amp;A; **`test_agentic_mcp_no_tool_match_includes_hints_in_trace`**. |

---

## 📞 Support

For setup or behavior questions:
1. Review `HOW_IT_WORKS.md`
2. Review `IT_SUPPORT_TDD_SPEC.md`
3. Read relevant tests under `tests/` for expected behavior

---

**Last Updated**: 2026-03-28
**Project Status**: Active implementation with passing tests
**Next Milestone**: Documentation and deployment hardening
