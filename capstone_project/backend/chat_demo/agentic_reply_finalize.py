"""
Optional LLM pass to merge agentic MCP compose text with KB + DB RAG (same idea as rag_kb / rag_db).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def finalize_agentic_reply_with_llm(
    llm: Any,
    *,
    user_message: str,
    triage: Dict[str, Any],
    ticket_id: Optional[int],
    rag: Dict[str, Any],
    base_text: str,
) -> str:
    """
    Produce one cohesive answer when retrieval returned context.

    If LLM fails, callers should fall back to ``base_text``.
    """
    kb = (rag.get("kb_text") or "").strip()
    db = (rag.get("db_text") or "").strip()
    if not kb and not db:
        return base_text

    cat = str((triage or {}).get("category") or "UNKNOWN")
    tid = ticket_id
    tid_line = f"Support ticket #{tid} was created for follow-up." if tid is not None else ""

    kb_labels = rag.get("kb_sources") or []
    db_labels = rag.get("db_sources") or []
    kb_cite = ", ".join(str(x) for x in kb_labels[:16]) if kb_labels else "(none)"
    db_cite = ", ".join(str(x) for x in db_labels[:16]) if db_labels else "(none)"

    prompt = f"""You are an IT support assistant at Acme Corp.

User message:
{user_message}

Triage category (from agent workflow): {cat}
{tid_line}

Retrieved knowledge base (markdown docs):
{kb or "(none)"}

KB source labels (use these in citations): {kb_cite}

Retrieved internal tickets/messages (similar past cases):
{db or "(none)"}

DB source labels (use these in citations): {db_cite}

Draft reply from the agent workflow (triage + first-line guidance + ticket line):
{base_text}

Write ONE concise reply to the user that:
- Uses the retrieved KB and internal examples when they help answer the question
- Keeps the ticket reference if present
- Does not invent policy; if context is thin, say what is known and that IT will follow up
- Stays professional and under ~350 words
- End with a short **Sources:** paragraph on its own line: name the KB markdown filenames and internal record ids (e.g. db_ticket:ticket_110) you relied on, matching the labels above. If you only used workflow bullets, say "Sources: triage workflow only."

Answer:"""

    try:
        out = llm.invoke(prompt)
        text = getattr(out, "content", None) or str(out)
        return (text or "").strip() or base_text
    except Exception:
        return base_text
