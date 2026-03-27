"""
Teaching pipeline: backend → DB (user) → LLM → DB (assistant).
Isolated from production /chat and RAG — for Oxford / cohort demos.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from backend.database.crud import create_message

STEP_KEYS = (
    "backend_receive",
    "db_user_message",
    "llm_generate",
    "db_assistant_message",
)

TRACE_PATH = "/teaching/pipeline/trace"


def _append_step(
    steps: List[Dict[str, Any]],
    *,
    key: str,
    label: str,
    layer: str,
    t0: float,
    status: str,
    detail: Dict[str, Any],
) -> None:
    duration_ms = int((time.perf_counter() - t0) * 1000)
    steps.append(
        {
            "key": key,
            "layer": layer,
            "label": label,
            "status": status,
            "duration_ms": duration_ms,
            "detail": detail,
        }
    )


def _llm_text(result: Any) -> str:
    if hasattr(result, "content"):
        return str(result.content)
    return str(result)


def run_teaching_pipeline(
    *,
    message: str,
    user_email: str,
    db: Session,
    llm: Any,
) -> Dict[str, Any]:
    """
    Execute the teaching trace: accept request, persist user msg, call LLM, persist assistant msg.
    """
    if not message or not str(message).strip():
        raise ValueError("message is required and cannot be empty")

    message = str(message).strip()
    run_id = str(uuid.uuid4())
    session_id = f"teaching-{run_id}"
    steps: List[Dict[str, Any]] = []

    # Step 1 — Backend receives request (teaching route; no RAG)
    t0 = time.perf_counter()
    _append_step(
        steps,
        key="backend_receive",
        label="1. Backend receives request",
        layer="route",
        t0=t0,
        status="success",
        detail={
            "method": "POST",
            "path": TRACE_PATH,
            "user_email": user_email,
            "body_preview": message[:500],
            "note": "Teaching route only — not /chat and not RAG.",
        },
    )

    # Step 2 — Persist user message
    t0 = time.perf_counter()
    user_row = create_message(
        db=db,
        session_id=session_id,
        role="user",
        content=message,
        metadata={"teaching": True, "run_id": run_id},
    )
    _append_step(
        steps,
        key="db_user_message",
        label="2. Database: save user message",
        layer="database",
        t0=t0,
        status="success",
        detail={
            "operation": "INSERT",
            "table": "messages",
            "message_id": user_row.id,
            "session_id": session_id,
        },
    )

    # Step 3 — LLM (no retrieval)
    t0 = time.perf_counter()
    prompt = (
        "You are a concise IT support teaching assistant. "
        "Reply in at most 2 sentences. No RAG context is used in this demo.\n\n"
        f"User: {message}"
    )
    invoke_result = llm.invoke(prompt)
    assistant_text = _llm_text(invoke_result)
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    _append_step(
        steps,
        key="llm_generate",
        label="3. LLM generates reply",
        layer="llm",
        t0=t0,
        status="success",
        detail={
            "model": str(model_name),
            "prompt_preview": prompt[:400] + ("…" if len(prompt) > 400 else ""),
            "response_preview": assistant_text[:500] + ("…" if len(assistant_text) > 500 else ""),
        },
    )

    # Step 4 — Persist assistant message
    t0 = time.perf_counter()
    asst_row = create_message(
        db=db,
        session_id=session_id,
        role="assistant",
        content=assistant_text,
        metadata={"teaching": True, "run_id": run_id},
    )
    _append_step(
        steps,
        key="db_assistant_message",
        label="4. Database: save assistant message",
        layer="database",
        t0=t0,
        status="success",
        detail={
            "operation": "INSERT",
            "table": "messages",
            "message_id": asst_row.id,
            "session_id": session_id,
        },
    )

    return {
        "run_id": run_id,
        "session_id": session_id,
        "assistant_response": assistant_text,
        "steps": steps,
    }
