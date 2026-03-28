"""
AGENTIC RAG RETRIEVAL
=====================
What this module demonstrates:
  - Reuse of the same KB and DB retrievers used by normal RAG tracks.
  - One helper that fetches both sources in a fault-tolerant way.
  - A single structured payload returned to the MCP pipeline.
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
    # Working buffers: collect successful retrieval text plus any source-specific errors.
    errors: List[str] = []
    kb_text, kb_sources = "", []
    db_text, db_sources = "", []

    # Step 1: KB retrieval (Qdrant / markdown corpus).
    try:
        kb_text, kb_sources = get_rag_context(message, k=k)
    except Exception as err:  # noqa: BLE001
        errors.append(f"kb:{err}")
        kb_text, kb_sources = "", ["fallback"]

    # Step 2: DB retrieval (tickets/messages), only when DB hooks are available.
    if db_session is not None and get_db_rag_context_fn is not None:
        try:
            db_text, db_sources = get_db_rag_context_fn(db_session, message, k=k)
        except Exception as err:  # noqa: BLE001
            errors.append(f"db:{err}")
            db_text, db_sources = "", ["fallback"]

    # Step 3: merge non-empty contexts with a visual separator for downstream prompts.
    parts: List[str] = []
    for chunk in ((kb_text or "").strip(), (db_text or "").strip()):
        if chunk:
            parts.append(chunk)
    combined = "\n\n---\n\n".join(parts) if parts else ""

    # Step 4: return normalized structure used by pipeline and trace UI.
    return {
        "kb_text": kb_text or "",
        "kb_sources": kb_sources or [],
        "db_text": db_text or "",
        "db_sources": db_sources or [],
        "combined_context": combined,
        "errors": errors,
    }
