# IT Support Agent — Capstone Implementation Plan
## GenAI Cohort 5 | Built week-by-week across the course

---

## WHAT YOU'RE BUILDING

An intelligent IT Support Agent that employees can chat with to diagnose issues, search the knowledge base, create tickets, and execute simple fixes — all powered by RAG, LangGraph agents, and MCP tools.

**The finished product:**
- React chat UI with streaming responses
- RAG over real IT docs (troubleshooting guides, SOPs, error logs)
- LangGraph agent with 3 specialised sub-agents
- MCP server exposing ticketing + system tools
- SQLite persistence (conversation + ticket history)
- Deployed via Docker to Railway

---

## ARCHITECTURE (the diagram to show on Day 1)

```
┌─────────────────────────────────────────────────────┐
│                  React Frontend                      │
│         (Chat UI + Ticket Dashboard)                 │
└────────────────────┬────────────────────────────────┘
                     │ HTTP / SSE streaming
┌────────────────────▼────────────────────────────────┐
│              Express / FastAPI Backend               │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │           LangGraph Orchestrator             │   │
│  │                                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │   │
│  │  │ Triage   │ │   RAG    │ │  Ticket     │  │   │
│  │  │  Agent   │→│  Agent   │ │  Agent      │  │   │
│  │  └──────────┘ └──────────┘ └─────────────┘  │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  Chroma Vector   │  │    MCP Tool Server       │ │
│  │  Store (RAG)     │  │  (tickets, sys-check,    │ │
│  │                  │  │   password-reset, logs)  │ │
│  └──────────────────┘  └──────────────────────────┘ │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │        SQLite  (tickets + chat history)      │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## PROJECT STRUCTURE (scaffold this in Week 1)

```
it-support-agent/
│
├── frontend/                    # React app (built Week 8)
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   ├── TicketDashboard.jsx
│   │   │   └── StatusBadge.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── backend/                     # Python FastAPI (main app)
│   ├── main.py                  # FastAPI entry point + SSE streaming
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # LangGraph graph definition (Week 6)
│   │   ├── triage_agent.py      # Classifies issue type (Week 6)
│   │   ├── rag_agent.py         # Searches knowledge base (Week 4-5)
│   │   └── ticket_agent.py      # Creates/updates tickets (Week 7)
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── ingest.py            # Chunk + embed + store docs (Week 3)
│   │   ├── retriever.py         # Query Chroma + rerank (Week 4)
│   │   └── docs/                # IT knowledge base documents
│   │       ├── wifi_troubleshooting.md
│   │       ├── vpn_setup_guide.md
│   │       ├── password_reset_sop.md
│   │       ├── laptop_setup_checklist.md
│   │       ├── common_error_codes.md
│   │       └── software_install_policies.md
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py            # SQLite schema (tickets, messages)
│   │   └── crud.py              # DB operations
│   ├── mcp_server/              # MCP tool server (Week 7)
│   │   ├── server.ts            # TypeScript MCP server
│   │   ├── tools/
│   │   │   ├── ticket_tools.ts  # create_ticket, update_ticket, get_ticket
│   │   │   ├── system_tools.ts  # check_system_status, ping_service
│   │   │   └── user_tools.ts    # reset_password, check_user_account
│   │   └── package.json
│   ├── requirements.txt
│   └── .env.example
│
├── docker-compose.yml           # Week 10
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

---

## WEEK-BY-WEEK BUILD PLAN

---

### WEEK 1 — Scaffold + Dev Tools
**Module: SDLC with LLM, Dev Tools**
**What students build:** The folder structure, a working hello-world endpoint, README

**Claude Code prompt to run:**
```
Create an IT Support Agent project with this structure:
- FastAPI backend with a /health endpoint and a /chat endpoint that echoes back the user message
- React + Vite frontend with a basic chat input and message list
- SQLite database with a tickets table (id, title, description, status, created_at) and messages table (id, session_id, role, content, created_at)
- requirements.txt with: fastapi, uvicorn, langchain, langchain-openai, langchain-chroma, langgraph, python-dotenv, sqlalchemy
- .env.example with OPENAI_API_KEY placeholder
- A README explaining what the project will become
Use best practices: separate concerns, environment variables for secrets, CORS configured for localhost:5173
```

**Teaching points:**
- Project scaffolding with AI
- Why we structure it this way (separation of concerns)
- Show the finished app briefly — "this is where we're heading"

---

### WEEK 2 — Prompt Engineering
**Module: Prompt Engineering**
**What students build:** The system prompt for the IT Support agent + basic chat endpoint

**Files to create/update:**
- `backend/main.py` — wire up OpenAI with a system prompt
- `backend/prompts.py` — all system prompts in one place

**The system prompt (teach students to write this):**
```python
SYSTEM_PROMPT = """
You are an IT Support Agent for Acme Corp. Your job is to help employees 
resolve technical issues quickly and professionally.

BEHAVIOUR:
- Always greet the user and ask clarifying questions if the issue is unclear
- Categorise issues as: PASSWORD, NETWORK, SOFTWARE, HARDWARE, or ACCESS
- If you can resolve it with the knowledge base, provide step-by-step instructions
- If you cannot resolve it, create a support ticket
- Always confirm the issue is resolved before closing

TONE: Professional but friendly. Use clear numbered steps. Avoid jargon.

CONSTRAINTS:
- Never provide instructions for personal devices
- Never share other users' ticket information  
- Escalate to human agent if issue involves security breach
"""
```

**Teaching points:**
- System prompt design
- Role, behaviour, constraints, tone structure
- Zero-shot vs few-shot — add 2 example exchanges
- Test: what happens with a bad prompt vs this one

---

### WEEK 3 — Vector Databases
**Module: Vector Databases**
**What students build:** The RAG knowledge base ingestion pipeline

**Claude Code prompt:**
```
In backend/rag/ingest.py, build a document ingestion pipeline:
1. Load all markdown files from backend/rag/docs/
2. Split them using RecursiveCharacterTextSplitter (chunk_size=500, overlap=50)
3. Create embeddings using OpenAIEmbeddings
4. Store in a persistent Chroma vector store at ./chroma_db
5. Print how many chunks were created and stored
6. Add a CLI flag --reset to delete and rebuild the store

Also create the 6 sample IT docs in backend/rag/docs/ with realistic content:
- wifi_troubleshooting.md (10+ common issues + steps)
- vpn_setup_guide.md (Windows + Mac setup)
- password_reset_sop.md (self-service + admin process)
- laptop_setup_checklist.md (new employee setup)
- common_error_codes.md (top 20 Windows/Mac error codes)
- software_install_policies.md (approved software list + process)
```

**Teaching points:**
- Why chunking matters (show chunk size effect on retrieval)
- What embeddings actually are — visualise in 2D
- Persistent vs in-memory store
- Run: `python ingest.py` — watch it chunk and store

---

### WEEK 4 — RAG Systems
**Module: RAG Systems**
**What students build:** The retrieval pipeline wired into the chat endpoint

**Claude Code prompt:**
```
In backend/rag/retriever.py, build a RAG retrieval module:
1. Load the existing Chroma store
2. Create a retriever with k=4 (top 4 chunks)
3. Build a LangChain RAG chain: retriever → prompt → LLM → output
4. The prompt should include the retrieved context and the user question
5. Return both the answer AND the source documents used

In backend/main.py, update the /chat endpoint to:
1. Call the RAG chain instead of plain OpenAI
2. Return the answer + sources in the response JSON
3. Store the conversation in the SQLite messages table

Add a /chat/history/{session_id} endpoint to retrieve past messages.
```

**Teaching points:**
- Show the difference: answer WITHOUT RAG vs WITH RAG on "how do I connect to VPN?"
- Inspect the retrieved chunks — are they relevant?
- What is faithfulness? (the answer should come from the docs)
- Introduce RAGAS — run basic evaluation: faithfulness + answer relevance

---

### WEEK 5 — LangChain
**Module: LangChain**
**What students build:** Refactor the RAG chain using LCEL + add conversation memory

**Claude Code prompt:**
```
Refactor backend/rag/retriever.py to use LangChain Expression Language (LCEL):

1. Build the chain as:
   retriever | format_docs | prompt | llm | StrOutputParser

2. Add ConversationBufferWindowMemory (last 5 turns) so the agent 
   remembers context within a session

3. Add a HyDE (Hypothetical Document Embedding) option:
   - Generate a hypothetical answer first
   - Use that to retrieve more relevant chunks
   - Compare retrieval quality with and without HyDE

4. Add a streaming version of the chain that yields tokens as they arrive
   (we'll wire this to SSE in Week 8)

Show both chains working in a test script: test_rag.py
```

**Teaching points:**
- LCEL pipe syntax — why it's cleaner than the old chain API
- Memory types: buffer, window, summary
- HyDE demo: ask a technical question and show the hypothetical doc it generates
- Streaming: why this matters for UX

---

### WEEK 6 — AI Agents / LangGraph
**Module: AI Agents**
**What students build:** The multi-agent orchestrator (biggest week)

**Claude Code prompt:**
```
Build a LangGraph multi-agent system in backend/agents/:

STATE:
- session_id, messages, issue_category, retrieved_docs, ticket_id, resolved

NODES (one per agent):
1. triage_agent — classifies the issue into: PASSWORD | NETWORK | SOFTWARE | HARDWARE | ACCESS | UNKNOWN
   Uses structured output (Pydantic) to return category + confidence + reasoning

2. rag_agent — searches the knowledge base for the issue
   If confidence > 0.7 from RAG, returns answer + sources
   If confidence < 0.7, sets needs_ticket = True

3. ticket_agent — creates a ticket when RAG can't solve it
   Extracts: title, description, priority (LOW/MEDIUM/HIGH/CRITICAL), category
   Returns ticket_id

4. response_agent — formats the final response to the user
   Combines RAG answer OR ticket confirmation into a friendly message

EDGES:
- START → triage
- triage → rag (always)
- rag → response (if resolved)
- rag → ticket (if needs_ticket)
- ticket → response
- response → END

Also add a human_in_the_loop interrupt before ticket creation:
  "I'm going to create a ticket for this. Shall I proceed? (yes/no)"

Use LangGraph checkpointer (SQLite) for persistence across turns.
```

**Teaching points:**
- Draw the graph on the whiteboard first
- Conditional edges — the agent "decides" where to go
- Structured output — why JSON from LLM matters
- Human-in-the-loop — this is real agentic AI, not just chat
- Show the graph visualisation: `graph.get_graph().draw_mermaid()`

---

### WEEK 7 — MCP Protocol
**Module: MCP**
**What students build:** The MCP tool server + wire it into the agent

**Claude Code prompt:**
```
Build an MCP server in backend/mcp_server/ using TypeScript:

TOOLS to implement:
1. create_ticket(title, description, priority, category, user_email) → ticket_id
   Stores in SQLite tickets table, returns ticket_id

2. get_ticket(ticket_id) → ticket details + status

3. update_ticket_status(ticket_id, status, note) → success/failure
   Valid statuses: OPEN, IN_PROGRESS, RESOLVED, CLOSED

4. check_system_status(service_name) → UP/DOWN/DEGRADED
   Simulate: check a hardcoded services dict {wifi: UP, vpn: UP, email: DEGRADED, jira: UP}

5. reset_password_link(user_email) → sends a mock email, returns confirmation
   Just log it + return "Password reset email sent to {email}"

6. search_known_issues(query) → returns top 3 matching known issues from a JSON file

Wire the MCP server into the LangGraph ticket_agent so it calls 
create_ticket via MCP instead of directly. Show the agent using 
the tool transparently.
```

**Teaching points:**
- MCP vs direct function call — why the abstraction matters
- Tool schemas — the description IS the prompt for the agent
- Show the agent discovering and calling tools automatically
- Optional: connect to Claude Desktop and show the same tools working there

---

### WEEK 8 — Full Stack Frontend
**Module: IT Support Chatbot**
**What students build:** The React frontend with streaming + ticket dashboard

**Claude Code prompt:**
```
Build a React frontend in frontend/src/ for the IT Support Agent:

CHAT PAGE:
- ChatWindow component: message list with user (right) and agent (left) bubbles
- Streaming: use EventSource/SSE to stream tokens as they arrive from /chat/stream
- Show typing indicator while streaming
- Show source documents used (collapsible "Sources" section under each AI message)
- Show ticket ID if one was created (with link to ticket dashboard)
- Session persistence: store session_id in localStorage

TICKET DASHBOARD (/tickets):
- Table of all tickets: ID, title, category, priority, status, created_at
- Status badges: colour-coded (red=OPEN, yellow=IN_PROGRESS, green=RESOLVED)
- Click a ticket to see full detail + conversation history
- Filter by status and category

LAYOUT:
- Sidebar navigation: Chat | Tickets | Knowledge Base (placeholder)
- Header with "IT Support Agent" branding and a status indicator
- Mobile responsive

Tech: React + Vite, Tailwind CSS, fetch/EventSource for API calls.
No external UI libraries except lucide-react for icons.
```

**Teaching points:**
- SSE streaming — why not WebSockets for this use case
- Component structure — single responsibility
- State management with useState/useContext
- The full round-trip: user types → backend → LangGraph → MCP → response streams back

---

### WEEK 9 — Local Models (Ollama)
**Module: GPU Setup + Local Models**
**What students build:** Swap OpenAI for Ollama on local dev

**Claude Code prompt:**
```
Add Ollama support as an alternative to OpenAI in backend/rag/retriever.py 
and backend/agents/orchestrator.py:

1. Add a MODEL_PROVIDER env var: "openai" (default) or "ollama"
2. If ollama: use ChatOllama(model="llama3.2") from langchain_ollama
3. For embeddings: if ollama, use OllamaEmbeddings(model="nomic-embed-text")
4. The rest of the chain should work unchanged (LCEL makes this easy)

Add a model comparison script scripts/compare_models.py:
- Ask the same 3 IT support questions to: GPT-4o, llama3.2 (Ollama), mistral (Ollama)
- Print: model name | response | latency | rough token count
- Let students see quality vs speed vs cost tradeoffs
```

**Teaching points:**
- Install Ollama, pull llama3.2 — run it in class
- LangChain abstraction: same chain, different model
- Quality comparison: how does llama3.2 handle IT support vs GPT-4o?
- Cost argument: local = free for development, no API key needed

---

### WEEK 10 — SDLC + Docker + Deploy
**Module: SDLC with LLM**
**What students build:** Dockerise + deploy + write tests + document

**Claude Code prompt:**
```
Finalise the IT Support Agent for production:

1. DOCKER:
   - Dockerfile.backend: Python 3.11, install requirements, run uvicorn
   - Dockerfile.frontend: Node 20, build Vite app, serve with nginx
   - docker-compose.yml: backend (port 8000) + frontend (port 3000) + shared volume for SQLite
   - .env passed in via docker-compose environment section

2. TESTS (pytest):
   - test_rag.py: test retrieval returns relevant docs for 5 sample queries
   - test_agents.py: test triage agent correctly classifies 10 issue types
   - test_api.py: test /health, /chat, /tickets endpoints return correct schemas

3. EVALUATION (RAGAS):
   - Create eval/test_dataset.json: 10 question/answer pairs from the IT docs
   - Run RAGAS: report faithfulness, answer_relevance, context_recall scores
   - Print a summary table

4. README update:
   - Project overview
   - Architecture diagram (ASCII)
   - Setup instructions (local + Docker)
   - How to add new documents to the knowledge base
   - API endpoint reference
```

**Teaching points:**
- Docker: one command to run the whole app
- Why tests matter for LLM apps (outputs are non-deterministic)
- RAGAS scores: what's a good score? How to improve?
- Deploy to Railway: `railway up` — get a public URL in 5 minutes

---

## SAMPLE IT KNOWLEDGE BASE DOCUMENTS

These are the 6 docs students ingest in Week 3. Here are the titles and what each should contain (write them with Claude):

| File | Contents |
|------|----------|
| `wifi_troubleshooting.md` | Can't connect, slow speed, drops, DNS issues, corporate vs guest network |
| `vpn_setup_guide.md` | Cisco AnyConnect install for Win/Mac, MFA setup, common errors |
| `password_reset_sop.md` | Self-service via portal, admin reset process, password policy rules |
| `laptop_setup_checklist.md` | New employee 25-step setup: accounts, software, security, VPN, email |
| `common_error_codes.md` | 20 errors: BSOD codes, Mac kernel panics, Office errors, VPN error codes |
| `software_install_policies.md` | Approved list, request process, prohibited software, IT approval SLA |

---

## WHAT THE AGENT CAN DO (finished product demo script)

Run these queries to show the finished app working:

1. **RAG resolved:** "I can't connect to the VPN, I'm getting error 422"
   → Agent triages as NETWORK → RAG finds vpn_setup_guide → Returns step-by-step fix with source cited

2. **Human in loop:** "My laptop won't turn on at all"
   → Agent triages as HARDWARE → RAG finds nothing useful → Agent says "I'll create a ticket, shall I proceed?" → User says yes → Ticket created, ID returned

3. **Memory:** "What was the ticket number you just created?"
   → Agent uses conversation memory to recall the ticket ID

4. **MCP tool call:** "Can you check if the VPN service is currently up?"
   → Agent calls check_system_status("vpn") via MCP → Returns UP/DOWN

5. **Multi-turn:** Follow-up questions, "My issue from last week is still not fixed"
   → Agent searches ticket history → Finds old ticket → Escalates

---

## TECH STACK SUMMARY

| Layer | Technology | Introduced |
|-------|-----------|------------|
| Frontend | React + Vite + Tailwind | Week 8 |
| API | FastAPI + SSE streaming | Week 1 |
| Orchestration | LangGraph (multi-agent) | Week 6 |
| RAG | LangChain LCEL + Chroma | Week 4-5 |
| Embeddings | OpenAI / nomic-embed-text | Week 3 |
| LLM | OpenAI GPT-4o / Ollama | Week 2 / Week 9 |
| MCP | TypeScript MCP SDK | Week 7 |
| Database | SQLite + SQLAlchemy | Week 1 |
| Evaluation | RAGAS | Week 4 + 10 |
| Deployment | Docker + Railway | Week 10 |

---

## CURSOR/CLAUDE CODE TIPS FOR BUILDING THIS

- Start each week by opening the relevant files and giving Claude Code the full context: `claude` then say "I'm building an IT Support Agent. Here's the current state: @backend/agents/ @backend/rag/`
- Use Composer to scaffold each new week's files in one go
- Commit after each week so students can `git checkout week-3` to start from a clean base
- Keep a `PROGRESS.md` in the repo tracking what's done, what's next, and any decisions made

---

*GenAI Cohort 5 — Capstone Project Plan | IT Support Agent | 10 weeks*
