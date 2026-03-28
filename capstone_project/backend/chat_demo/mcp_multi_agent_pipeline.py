"""
AGENTIC MCP PIPELINE
====================
What this module demonstrates:
  - Multi-step orchestration: triage -> retrieve -> ticket -> compose.
  - Hybrid execution: MCP tools over transport + Python-side RAG retrieval.
  - Optional final LLM synthesis when retrieval provides useful context.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.chat_demo.agentic_rag_retrieval import fetch_agentic_rag_context
from backend.chat_demo.agentic_reply_finalize import finalize_agentic_reply_with_llm
from backend.database.crud import create_ticket

TRIAGE_TOOL = "agent_triage"
TICKET_TOOL = "agent_log_ticket"
RESPOND_TOOL = "agent_compose_response"
RAG_TOOL = "agent_retrieve_kb_db"


def _trace_transport(action_agent: Any) -> str:
    """Expose whether MCP calls use stdio server or simulation mode."""
    return "stdio_mcp" if getattr(action_agent, "use_real_mcp", False) else "simulated"


def _short(obj: Any, limit: int = 400) -> str:
    """Compact trace serializer used in UI/debug payloads."""
    s = str(obj)
    return s if len(s) <= limit else s[: limit - 3] + "..."


def _normalize_category(raw: Any) -> str:
    """Coerce category labels to the known enum."""
    allowed = (
        "PASSWORD",
        "NETWORK",
        "SOFTWARE",
        "HARDWARE",
        "ACCESS",
        "UNKNOWN",
    )
    if raw is None:
        return "UNKNOWN"
    u = str(raw).upper().strip()
    return u if u in allowed else "UNKNOWN"


def _normalize_priority(raw: Any) -> str:
    """Coerce priority labels to the known enum."""
    allowed = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    if raw is None:
        return "MEDIUM"
    u = str(raw).upper().strip()
    return u if u in allowed else "MEDIUM"


def _merge_sources(rag: Dict[str, Any]) -> List[str]:
    """Build a de-duplicated source list for API responses."""
    out: List[str] = ["agentic_mcp"]
    for key in ("kb_sources", "db_sources"):
        for s in rag.get(key) or []:
            if s and s not in out:
                out.append(s)
    return out


def run_mcp_three_agent_pipeline(
    *,
    action_agent: Any,
    message: str,
    user_email: str,
    db_session: Any = None,
    session_id: Optional[str] = None,
    get_rag_context: Optional[Callable[..., Tuple[str, List[str]]]] = None,
    get_db_rag_context_fn: Optional[Callable[..., Tuple[str, List[str]]]] = None,
    llm: Any = None,
    rag_k: int = 5,
) -> Dict[str, Any]:
    """
    Run triage → RAG (optional) → ticket → compose (MCP) → optional LLM synthesis.

    Returns keys: response, ticket_id (optional), mcp_trace, sources (list).
    """
    # Step 1: initialize trace/transport metadata.
    transport = _trace_transport(action_agent)
    steps: list[Dict[str, Any]] = []

    # Step 2: triage via MCP.
    triage = action_agent._call_mcp_tool(
        TRIAGE_TOOL,
        {"user_message": message, "user_email": user_email},
    )
    steps.append(
        {
            "agent": "triage",
            "tool": TRIAGE_TOOL,
            "result_summary": _short(triage),
            "transport": transport,
        }
    )

    # Step 3: retrieve KB + DB context in Python (same retrievers as non-agentic tracks).
    rag: Dict[str, Any]
    if get_rag_context is not None:
        rag = fetch_agentic_rag_context(
            message=message,
            db_session=db_session,
            get_rag_context=get_rag_context,
            get_db_rag_context_fn=get_db_rag_context_fn,
            k=rag_k,
        )
        steps.append(
            {
                "agent": "rag",
                "tool": RAG_TOOL,
                "result_summary": _short(
                    {
                        "kb_len": len(rag.get("kb_text") or ""),
                        "db_len": len(rag.get("db_text") or ""),
                        "kb_sources": rag.get("kb_sources"),
                        "db_sources": rag.get("db_sources"),
                        "errors": rag.get("errors"),
                    }
                ),
                "transport": "python_rag",
            }
        )
    else:
        rag = {
            "kb_text": "",
            "kb_sources": [],
            "db_text": "",
            "db_sources": [],
            "combined_context": "",
            "errors": [],
        }

    # Step 4: normalize triage output before ticket/logging.
    category = _normalize_category(
        triage.get("category") if isinstance(triage, dict) else None
    )
    priority = _normalize_priority(
        triage.get("priority") if isinstance(triage, dict) else None
    )
    intent = (
        (triage.get("intent") if isinstance(triage, dict) else None) or "SUPPORT_REQUEST"
    )

    # Step 5: call MCP ticket tool (metadata/title suggestion), then persist SQLite ticket.
    ticket_mcp = action_agent._call_mcp_tool(
        TICKET_TOOL,
        {
            "user_message": message,
            "user_email": user_email,
            "intent": intent,
            "category": category,
            "priority": priority,
        },
    )
    steps.append(
        {
            "agent": "ticket",
            "tool": TICKET_TOOL,
            "result_summary": _short(ticket_mcp),
            "transport": transport,
        }
    )

    ticket_id: Optional[int] = None
    if db_session is not None:
        try:
            title_src = (
                ticket_mcp.get("title_suggestion")
                if isinstance(ticket_mcp, dict)
                else None
            ) or message
            title = (str(title_src).strip() or "Support request")[:200]
            row = create_ticket(
                db_session,
                title=title,
                description=message,
                priority=priority,
                category=category,
                user_email=user_email,
                session_id=session_id,
            )
            ticket_id = row.id
            steps[-1]["ticket_id"] = ticket_id
        except Exception as err:  # noqa: BLE001
            steps[-1]["db_persist_error"] = str(err)

    # Step 6: call MCP compose tool with triage + retrieval + ticket context.
    respond = action_agent._call_mcp_tool(
        RESPOND_TOOL,
        {
            "user_message": message,
            "user_email": user_email,
            "triage": triage if isinstance(triage, dict) else {},
            "ticket_mcp": ticket_mcp if isinstance(ticket_mcp, dict) else {},
            "ticket_id": ticket_id,
            "rag_kb_text": rag.get("kb_text") or "",
            "rag_db_text": rag.get("db_text") or "",
            "rag_kb_sources": rag.get("kb_sources") or [],
            "rag_db_sources": rag.get("db_sources") or [],
        },
    )
    reply = ""
    if isinstance(respond, dict):
        reply = str(respond.get("reply") or respond.get("message") or "").strip()
    if not reply:
        reply = str(respond)

    steps.append(
        {
            "agent": "respond",
            "tool": RESPOND_TOOL,
            "result_summary": _short(respond),
            "transport": transport,
        }
    )

    # Step 7 (optional): LLM synthesis pass for a single cohesive final message.
    if llm is not None and (
        (rag.get("kb_text") or "").strip() or (rag.get("db_text") or "").strip()
    ):
        reply = finalize_agentic_reply_with_llm(
            llm,
            user_message=message,
            triage=triage if isinstance(triage, dict) else {},
            ticket_id=ticket_id,
            rag=rag,
            base_text=reply,
        )

    sources = _merge_sources(rag)

    # Step 8: return API-ready payload plus trace for presenter UI.
    return {
        "response": reply,
        "ticket_id": ticket_id,
        "sources": sources,
        "mcp_trace": {
            "pipeline": "triage→rag→ticket→respond",
            "steps": steps,
            "transport": transport,
        },
    }
