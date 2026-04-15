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
    # We capture transport mode once, then stamp every step with it.
    # That makes debugging easier because you can quickly tell whether
    # a response came from the real MCP server or the local simulation path.
    return "stdio_mcp" if getattr(action_agent, "use_real_mcp", False) else "simulated"


def _short(obj: Any, limit: int = 400) -> str:
    """Compact trace serializer used in UI/debug payloads."""
    # MCP tool outputs can be large. For traces, we only need a preview.
    # This helper keeps logs readable while still exposing useful context.
    s = str(obj)
    return s if len(s) <= limit else s[: limit - 3] + "..."


def _normalize_category(raw: Any) -> str:
    """Coerce category labels to the known enum."""
    # "allowed" is the contract this module accepts for category.
    # Normalizing up front prevents invalid values from leaking into ticket writes.
    allowed = (
        "PASSWORD",
        "NETWORK",
        "SOFTWARE",
        "HARDWARE",
        "ACCESS",
        "UNKNOWN",
    )
    if raw is None:
        # If triage omits category, keep the pipeline moving with a safe fallback.
        return "UNKNOWN"
    u = str(raw).upper().strip()
    # Coercion is intentionally defensive: user experience should not fail
    # just because one agent produced an unexpected label.
    return u if u in allowed else "UNKNOWN"


def _normalize_priority(raw: Any) -> str:
    """Coerce priority labels to the known enum."""
    # We use the same values expected by ticket persistence/business logic.
    # This "adapter" pattern allows triage outputs to vary safely.
    allowed = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    if raw is None:
        # MEDIUM is a balanced default when urgency is unknown.
        return "MEDIUM"
    u = str(raw).upper().strip()
    # Invalid values are normalized instead of raising, so support flow continues.
    return u if u in allowed else "MEDIUM"


def _merge_sources(rag: Dict[str, Any]) -> List[str]:
    """Build a de-duplicated source list for API responses."""
    # Consumers want to know "where did this answer come from?"
    # We always include the pipeline marker, then append retrieval sources.
    out: List[str] = ["agentic_mcp"]
    for key in ("kb_sources", "db_sources"):
        # Keep insertion order so source display is deterministic.
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
    # -------------------------------------------------------------------------
    # Step 1) Initialize execution metadata
    # -------------------------------------------------------------------------
    # "transport" tells us if MCP calls are real (stdio) or simulated.
    # "steps" accumulates a compact, UI-friendly audit trail of the pipeline.
    transport = _trace_transport(action_agent)
    steps: list[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Step 2) TRIAGE agent
    # -------------------------------------------------------------------------
    # Goal: classify the message into intent/category/priority.
    # Why first: downstream steps (ticket + response tone) depend on triage.
    triage = action_agent._call_mcp_tool(
        TRIAGE_TOOL,
        {"user_message": message, "user_email": user_email},
    )
    # Record a summarized trace entry so the frontend can visualize the step.
    steps.append(
        {
            "agent": "triage",
            "tool": TRIAGE_TOOL,
            "result_summary": _short(triage),
            "transport": transport,
        }
    )

    # -------------------------------------------------------------------------
    # Step 3) Retrieve context (RAG)
    # -------------------------------------------------------------------------
    # Goal: collect helpful evidence from both KB and DB.
    # Design choice: retrieval runs in Python so this pipeline can reuse existing
    # retrievers used by other chat modes.
    rag: Dict[str, Any]
    if get_rag_context is not None:
        rag = fetch_agentic_rag_context(
            message=message,
            db_session=db_session,
            get_rag_context=get_rag_context,
            get_db_rag_context_fn=get_db_rag_context_fn,
            k=rag_k,
        )
        # We only log compact metrics here (lengths/sources/errors) to avoid
        # putting full context text into traces.
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
        # No retriever configured: use an empty-but-typed structure so later code
        # can always read the same keys without additional branching.
        rag = {
            "kb_text": "",
            "kb_sources": [],
            "db_text": "",
            "db_sources": [],
            "combined_context": "",
            "errors": [],
        }

    # -------------------------------------------------------------------------
    # Step 4) Normalize triage outputs
    # -------------------------------------------------------------------------
    # Goal: convert potentially messy model output into stable enum-like values.
    # This prevents schema/persistence errors in the ticket phase.
    category = _normalize_category(
        triage.get("category") if isinstance(triage, dict) else None
    )
    priority = _normalize_priority(
        triage.get("priority") if isinstance(triage, dict) else None
    )
    intent = (
        (triage.get("intent") if isinstance(triage, dict) else None) or "SUPPORT_REQUEST"
    )

    # -------------------------------------------------------------------------
    # Step 5) Ticket agent + DB persistence
    # -------------------------------------------------------------------------
    # Two sub-steps happen here:
    #   A) Ask MCP ticket tool for structured metadata (for example title ideas).
    #   B) Persist the actual ticket row when a DB session is available.
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
            # Prefer agent-proposed title, but always have a robust fallback.
            title_src = (
                ticket_mcp.get("title_suggestion")
                if isinstance(ticket_mcp, dict)
                else None
            ) or message
            # Clamp length to avoid oversized DB values / UI overflow.
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
            # Attach persisted ID to trace so UI can link to the created ticket.
            steps[-1]["ticket_id"] = ticket_id
        except Exception as err:  # noqa: BLE001
            # Non-fatal by design: user should still receive a response even
            # if persistence fails (we expose the error in trace for operators).
            steps[-1]["db_persist_error"] = str(err)

    # -------------------------------------------------------------------------
    # Step 6) Response composition agent
    # -------------------------------------------------------------------------
    # Goal: generate a user-facing answer using every available signal:
    # triage decision, ticket metadata/id, and retrieved context.
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
        # Support both known response fields from MCP implementations.
        reply = str(respond.get("reply") or respond.get("message") or "").strip()
    if not reply:
        # Last-resort fallback keeps the API contract intact.
        reply = str(respond)

    steps.append(
        {
            "agent": "respond",
            "tool": RESPOND_TOOL,
            "result_summary": _short(respond),
            "transport": transport,
        }
    )

    # -------------------------------------------------------------------------
    # Step 7) Optional final LLM synthesis
    # -------------------------------------------------------------------------
    # If we have extra context and an LLM, do one final polish pass so the
    # answer reads as one coherent message rather than stitched fragments.
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

    # -------------------------------------------------------------------------
    # Step 8) Return API payload
    # -------------------------------------------------------------------------
    # Contract:
    # - response: text shown to end user
    # - ticket_id: created ticket (if persistence succeeded)
    # - sources: provenance labels for transparency
    # - mcp_trace: detailed execution trace for debugging/visualization
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
