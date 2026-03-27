"""Route /chat-style messages to menu, plain LLM, KB RAG, agentic MCP, or legacy RAG."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.chat_demo.guardrails import is_clearly_non_it, non_it_refusal_message
from backend.chat_demo.mcp_multi_agent_pipeline import run_mcp_three_agent_pipeline
from backend.chat_demo.plain_llm import run_plain_llm
from backend.chat_demo.ticket_escalation import try_create_ticket_from_escalation
from backend.chat_demo.tracks import resolve_effective_track

RAG_KB_PRESENTER: Dict[str, str] = {
    "file": "backend/rag/retriever.py",
    "symbol": "get_rag_context",
    "note": "Qdrant KB retrieval + grounded prompt in router._kb_rag_reply.",
}

AGENTIC_MCP_PRESENTER: Dict[str, str] = {
    "file": "backend/chat_demo/mcp_multi_agent_pipeline.py",
    "symbol": "run_mcp_three_agent_pipeline",
    "note": "MCP: agent_triage → agent_log_ticket → agent_compose_response; RAG (KB+DB) runs in Python; optional LLM merge when retrieval returns text.",
}

RAG_DB_PRESENTER: Dict[str, str] = {
    "file": "backend/rag/db_retriever.py",
    "symbol": "get_db_rag_context",
    "note": "Tickets + messages embedded into Qdrant collection it_support_db.",
}

TICKET_ESCALATION_PRESENTER: Dict[str, str] = {
    "file": "backend/chat_demo/ticket_escalation.py",
    "symbol": "try_create_ticket_from_escalation",
    "note": "No KB hit → heuristic priority + SQLite ticket + dummy email line.",
}


def _demo_menu_markdown() -> str:
    return """### Demo tracks

Pick a track using the **buttons** in the chat (they set `demo_track` on the request), or send a message starting with `__DEMO__:<track>`.

1. **Direct LLM** — `demo_track`: `plain_llm` — language model only, no knowledge base retrieval. *Open `backend/chat_demo/plain_llm.py` when presenting.*

2. **Knowledge base RAG** — `demo_track`: `rag_kb` — retrieve from the IT KB (Qdrant) then answer.

3. **DB RAG (structured)** — `demo_track`: `rag_db` (alias `rag_structured`) — retrieve from embedded **tickets and chat messages** in SQLite (collection `it_support_db`).

4. **Agentic MCP** — `demo_track`: `agentic_mcp` — **triage → KB+DB RAG (Python) → ticket → respond (MCP)**, optional **LLM** merge when RAG returns context. *Open `backend/chat_demo/mcp_multi_agent_pipeline.py` when presenting.*

Say **Hi** again any time with demo mode on to see this menu."""


def _db_rag_reply(llm: Any, message: str, context: str) -> str:
    if is_clearly_non_it(message):
        return non_it_refusal_message()
    prompt = f"""You are an IT support agent at Acme Corp. Use the following context from **internal tickets and chat logs** (database RAG). Be concise and professional.

Context:
{context}

User Question: {message}

If the question is unrelated to IT or workplace technology, politely refuse and suggest IT topics. Do not answer general knowledge or trivia.

If the context does not contain the answer, say so. Cite ticket or message ids when present in the context.

Answer:"""
    return llm.invoke(prompt).content


def _kb_rag_reply(
    llm: Any,
    message: str,
    context: str,
    sources: List[str],
) -> str:
    if is_clearly_non_it(message):
        return non_it_refusal_message()
    prompt = f"""You are an IT support agent at Acme Corp. Use the following context from our knowledge base to answer the user's question. Be helpful, concise, and professional.

Context from Knowledge Base:
{context}

User Question: {message}

Instructions:
- If the question is unrelated to IT or workplace technology, politely refuse and suggest IT topics. Do not answer general knowledge or trivia.
- Provide a clear, step-by-step answer based on the context
- If the context doesn't contain relevant information, say so politely
- Include specific details like URLs, commands, or error codes when available
- Be friendly and professional

Answer:"""
    return llm.invoke(prompt).content


def compute_chat_reply(
    *,
    message: str,
    user_email: str,
    demo_mode: bool,
    demo_track: Optional[str],
    llm: Any,
    get_rag_context: Callable[..., Tuple[str, List[str]]],
    generate_simple_response_fn: Callable[[str], str],
    action_agent: Any,
    db_session: Any = None,
    get_db_rag_context_fn: Optional[Callable[..., Tuple[str, List[str]]]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pure routing + generation. Caller persists messages and builds ChatResponse.

    Returns dict with keys: response, sources, demo_track, presenter, mcp_trace, ticket_id (optional).
    """
    effective = resolve_effective_track(
        message=message,
        demo_track_field=demo_track,
        demo_mode=demo_mode,
    )

    if effective == "menu":
        return {
            "response": _demo_menu_markdown(),
            "sources": None,
            "demo_track": "menu",
            "presenter": None,
            "mcp_trace": None,
        }

    if effective == "plain_llm":
        text, presenter = run_plain_llm(llm, message)
        return {
            "response": text,
            "sources": ["plain_llm"],
            "demo_track": "plain_llm",
            "presenter": presenter,
            "mcp_trace": None,
        }

    if effective == "rag_kb":
        if is_clearly_non_it(message):
            return {
                "response": non_it_refusal_message(),
                "sources": ["guardrail"],
                "demo_track": "rag_kb",
                "presenter": RAG_KB_PRESENTER,
                "mcp_trace": None,
            }
        try:
            context, sources = get_rag_context(message, k=5)
        except Exception:
            context, sources = "", ["fallback"]
        if not context:
            return {
                "response": generate_simple_response_fn(message),
                "sources": sources or ["no_sources"],
                "demo_track": "rag_kb",
                "presenter": RAG_KB_PRESENTER,
                "mcp_trace": None,
            }
        text = _kb_rag_reply(llm, message, context, sources)
        return {
            "response": text,
            "sources": sources,
            "demo_track": "rag_kb",
            "presenter": RAG_KB_PRESENTER,
            "mcp_trace": None,
        }

    if effective == "rag_db":
        if is_clearly_non_it(message):
            return {
                "response": non_it_refusal_message(),
                "sources": ["guardrail"],
                "demo_track": "rag_db",
                "presenter": RAG_DB_PRESENTER,
                "mcp_trace": None,
            }
        if db_session is None or get_db_rag_context_fn is None:
            return {
                "response": "Database RAG is not available (no DB session).",
                "sources": ["error"],
                "demo_track": "rag_db",
                "presenter": RAG_DB_PRESENTER,
                "mcp_trace": None,
            }
        try:
            context, sources = get_db_rag_context_fn(db_session, message, k=5)
        except Exception:
            context, sources = "", ["fallback"]
        if not context:
            return {
                "response": generate_simple_response_fn(message),
                "sources": sources or ["no_sources"],
                "demo_track": "rag_db",
                "presenter": RAG_DB_PRESENTER,
                "mcp_trace": None,
            }
        text = _db_rag_reply(llm, message, context)
        return {
            "response": text,
            "sources": sources,
            "demo_track": "rag_db",
            "presenter": RAG_DB_PRESENTER,
            "mcp_trace": None,
        }

    if effective == "agentic_mcp":
        if is_clearly_non_it(message):
            return {
                "response": non_it_refusal_message(),
                "sources": ["guardrail"],
                "demo_track": "agentic_mcp",
                "presenter": AGENTIC_MCP_PRESENTER,
                "mcp_trace": None,
            }
        pipeline = run_mcp_three_agent_pipeline(
            action_agent=action_agent,
            message=message,
            user_email=user_email,
            db_session=db_session,
            session_id=session_id,
            get_rag_context=get_rag_context,
            get_db_rag_context_fn=get_db_rag_context_fn,
            llm=llm,
        )
        text = pipeline.get("response") or ""
        trace = pipeline.get("mcp_trace") or {}
        mcp_trace: Dict[str, Any] = {
            **trace,
            "how_agentic_works": (
                "Step 1: MCP **agent_triage**. Step 2: **agent_retrieve_kb_db** (Python) runs the same KB + DB retrieval as "
                "`rag_kb` / `rag_db`. Step 3: **agent_log_ticket** + SQLite ticket. Step 4: MCP **agent_compose_response** "
                "with RAG excerpts in the prompt. If retrieval returned text, an **LLM** pass merges everything into one reply."
            ),
            "where_is_ai": (
                "MCP tools run over stdio (or simulated). RAG embeddings live in Python, so retrieval is not a Node MCP call. "
                "Set USE_SIMULATED_MCP=1 for in-process MCP stubs without Node."
            ),
        }
        out: Dict[str, Any] = {
            "response": text,
            "sources": pipeline.get("sources") or ["agentic_mcp"],
            "demo_track": "agentic_mcp",
            "presenter": AGENTIC_MCP_PRESENTER,
            "mcp_trace": mcp_trace,
        }
        tid = pipeline.get("ticket_id")
        if tid is not None:
            out["ticket_id"] = tid
        return out

    # Legacy: same as previous /chat behaviour
    if is_clearly_non_it(message):
        return {
            "response": non_it_refusal_message(),
            "sources": ["guardrail"],
            "demo_track": None,
            "presenter": None,
            "mcp_trace": None,
            "ticket_id": None,
        }

    try:
        context, sources = get_rag_context(message, k=5)
    except Exception:
        context, sources = "", ["fallback"]

    if context:
        text = _kb_rag_reply(llm, message, context, sources)
        return {
            "response": text,
            "sources": sources if sources else ["no_sources"],
            "demo_track": None,
            "presenter": None,
            "mcp_trace": None,
            "ticket_id": None,
        }

    # No KB context: optional real ticket + priority (agentic side effect, not just LLM text)
    if db_session is not None and session_id is not None:
        try:
            esc = try_create_ticket_from_escalation(
                db_session,
                message=message,
                user_email=user_email,
                session_id=session_id,
            )
            if esc is not None:
                tid, pri, cat, reply = esc
                return {
                    "response": reply,
                    "sources": ["ticket_escalation"],
                    "demo_track": "agentic_ticket",
                    "presenter": {
                        **TICKET_ESCALATION_PRESENTER,
                        "note": f"{TICKET_ESCALATION_PRESENTER['note']} ticket_id={tid} priority={pri} category={cat}",
                    },
                    "mcp_trace": None,
                    "ticket_id": tid,
                }
        except Exception:
            pass

    return {
        "response": generate_simple_response_fn(message),
        "sources": sources if sources else ["no_sources"],
        "demo_track": None,
        "presenter": None,
        "mcp_trace": None,
        "ticket_id": None,
    }
