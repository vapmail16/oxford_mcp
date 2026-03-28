"""
PLAIN LLM TRACK
===============
What this module demonstrates:
  - A direct system+user prompt call (no RAG, no MCP tools).
  - Lightweight non-IT guardrail before invoking the model.
  - A presenter metadata payload for the UI/demo overlay.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from backend.chat_demo.guardrails import (
    SYSTEM_IT_SUPPORT_ONLY,
    is_clearly_non_it,
    non_it_refusal_message,
)

PLAIN_LLM_PRESENTER: Dict[str, str] = {
    "file": "backend/chat_demo/plain_llm.py",
    "symbol": "run_plain_llm",
    "note": "System + user messages via ChatOpenAI.invoke; IT-scope guardrails; no RAG.",
}


def run_plain_llm(llm: Any, user_message: str) -> Tuple[str, Dict[str, str]]:
    """
    Execute the simplest chat path used in demo mode.

    Flow:
      1) Guardrail check for obviously non-IT prompts.
      2) If allowed, call the model with system + human messages.
      3) Return plain text plus presenter metadata.
    """
    # Step 1: short-circuit obvious non-IT questions before model call.
    if is_clearly_non_it(user_message):
        return non_it_refusal_message(), {
            **PLAIN_LLM_PRESENTER,
            "note": (
                f"{PLAIN_LLM_PRESENTER['note']} "
                "Guardrail: obvious non-IT; LLM not called."
            ),
        }

    # Step 2: invoke the model directly (no retrieval context added).
    out = llm.invoke(
        [
            SystemMessage(content=SYSTEM_IT_SUPPORT_ONLY),
            HumanMessage(content=user_message),
        ]
    )
    # Step 3: normalize output type and return with presenter info.
    text = getattr(out, "content", str(out))
    return text, PLAIN_LLM_PRESENTER
