# IT Support Agent — How It Works (Plain English)

This document explains how the application runs, what each part does, and where to find things. No code — just plain language.

---

## The Big Picture

When you type a message in the chatbot, it goes to a backend server. The server looks up relevant help articles, sends your question and that context to an AI model, and returns an answer. Optionally, it can also create support tickets.

---

## How the Application Runs

**Two main pieces:**

1. **Backend** — A Python server (FastAPI) that handles chat, tickets, and AI logic. Runs on port 8000.
2. **Frontend** — A web page with a landing page and a floating chat button. Runs on port 5173.

**To run everything:**
- Start the backend: `cd backend` then `python main.py`
- Start the frontend: `cd frontend` then `npm run dev`
- Open the browser at the URL shown (usually localhost:5173)

---

## How the Chatbot Is Implemented

**What happens when you send a message:**

1. You type in the chat window and click Send.
2. The frontend sends your message to the backend’s `/chat` endpoint.
3. The backend:
   - Saves your message in a database
   - Looks up relevant help articles (RAG)
   - Sends your question plus those articles to an AI model (LLM)
   - Gets a reply and saves it
4. The reply is sent back to the frontend and shown in the chat.

**Where the chatbot lives:**
- **Frontend:** `frontend/src/components/Chatbot.tsx` — the chat window, buttons, and message display
- **Backend:** `backend/main.py` — the `/chat` endpoint that processes messages

---

## How RAG Is Implemented

**RAG = Retrieval-Augmented Generation.** In simple terms: “Find helpful docs, then ask the AI to answer using them.”

**Step by step:**

1. **Knowledge base** — Markdown files in `backend/rag/docs/` (VPN, password reset, WiFi, etc.).
2. **Ingestion** — A script reads those files, splits them into chunks, turns them into numbers (embeddings), and stores them in a vector database (Qdrant).
3. **Retrieval** — When you ask a question, the system finds the most similar chunks in the knowledge base.
4. **Generation** — Those chunks are added to the prompt sent to the AI, so the answer is based on your docs.

**Where RAG lives:**
- **Source documents:** `backend/rag/docs/` — the markdown help files
- **Ingestion script:** `backend/rag/ingest.py` — loads, chunks, embeds, and stores documents
- **Retrieval logic:** `backend/rag/retriever.py` — fetches relevant chunks for a query
- **Vector store:** `backend/qdrant_storage/` — where embeddings are stored (created when you run ingestion)

**To refresh the knowledge base:**  
Run `python -m rag.ingest --reset` from the `backend` folder.

---

## How Agents Are Implemented

**Agents** are separate modules that each do one job: triage, answering questions, creating tickets, formatting replies, etc.

**The flow (when agents are used):**

1. **Triage Agent** — Decides what kind of request it is (question, ticket request, greeting, etc.).
2. **RAG Agent** — Answers questions using the knowledge base.
3. **Ticket Agent** — Creates support tickets when needed.
4. **Response Agent** — Formats the final answer for the user.
5. **Action Agent** — Placeholder for future actions (e.g. MCP tools).

**Orchestrator** — A coordinator that runs these agents in the right order based on the triage result.

**Important:** The agents and orchestrator are implemented, but the main chat API does **not** use them yet. The chat endpoint uses a simpler path: RAG + LLM directly. The agents are ready to be wired in if you want the full multi-agent flow.

**Where agents live:**
- **Triage:** `backend/agents/triage.py`
- **RAG Agent:** `backend/agents/rag_agent.py`
- **Ticket Agent:** `backend/agents/ticket_agent.py`
- **Response Agent:** `backend/agents/response_agent.py`
- **Action Agent:** `backend/agents/action_agent.py`
- **Orchestrator:** `backend/agents/orchestrator.py`

---

## File Map (Quick Reference)

| What | Where |
|------|-------|
| **Backend server** | `backend/main.py` |
| **Chat endpoint** | `backend/main.py` (chat function) |
| **Ticket endpoints** | `backend/main.py` |
| **Database models** | `backend/database/models.py` |
| **Database operations** | `backend/database/crud.py` |
| **Knowledge base docs** | `backend/rag/docs/` |
| **RAG ingestion** | `backend/rag/ingest.py` |
| **RAG retrieval** | `backend/rag/retriever.py` |
| **Vector store (Qdrant)** | `backend/qdrant_storage/` |
| **All agents** | `backend/agents/` |
| **Orchestrator** | `backend/agents/orchestrator.py` |
| **Frontend app** | `frontend/src/App.tsx` |
| **Landing page** | `frontend/src/pages/LandingPage.tsx` |
| **Chatbot UI** | `frontend/src/components/Chatbot.tsx` |
| **API client** | `frontend/src/api.ts` |
| **Environment config** | `backend/.env` |

---

## Summary

- **Chatbot:** Frontend sends messages to the backend; backend uses RAG + LLM to reply.
- **RAG:** Help docs are stored as embeddings in Qdrant; similar chunks are retrieved and passed to the LLM.
- **Agents:** Implemented and tested, but not yet used by the main chat API.
- **To run:** Start backend and frontend, then open the frontend URL in your browser.
