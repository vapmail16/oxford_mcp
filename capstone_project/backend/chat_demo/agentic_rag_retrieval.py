"""
KB + DB retrieval for the agentic MCP pipeline only.

Uses the same call shape as `rag_kb` / `rag_db` tracks: `get_rag_context(message, k=...)`
and `get_db_rag_context_fn(db_session, message, k=...)`.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

FetchResult = Dict[str, Any]


def fetch_agentic_rag_context(
    *,
    message: str,
    db_session: Any,
    get_rag_context: Callable[..., Tuple[str, List[str]]],
    get_db_rag_context_fn: Optional[Callable[..., Tuple[str, List[str]]]],
    k: int = 5,
) -> FetchResult:
    """
    Retrieve markdown KB (Qdrant) and structured DB RAG (tickets/messages) in one step.

    Failures in one source are isolated so the other can still return context.
    """
    errors: List[str] = []
    kb_text, kb_sources = "", []
    db_text, db_sources = "", []

    try:
        kb_text, kb_sources = get_rag_context(message, k=k)
    except Exception as err:  # noqa: BLE001
        errors.append(f"kb:{err}")
        kb_text, kb_sources = "", ["fallback"]

    if db_session is not None and get_db_rag_context_fn is not None:
        try:
            db_text, db_sources = get_db_rag_context_fn(db_session, message, k=k)
        except Exception as err:  # noqa: BLE001
            errors.append(f"db:{err}")
            db_text, db_sources = "", ["fallback"]

    parts: List[str] = []
    for chunk in ((kb_text or "").strip(), (db_text or "").strip()):
        if chunk:
            parts.append(chunk)
    combined = "\n\n---\n\n".join(parts) if parts else ""

    return {
        "kb_text": kb_text or "",
        "kb_sources": kb_sources or [],
        "db_text": db_text or "",
        "db_sources": db_sources or [],
        "combined_context": combined,
        "errors": errors,
    }
