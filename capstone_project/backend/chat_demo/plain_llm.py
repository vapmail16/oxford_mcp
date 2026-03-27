"""Single LLM call with no retrieval — for Oxford \"plain LLM\" demo track."""

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
    if is_clearly_non_it(user_message):
        return non_it_refusal_message(), {
            **PLAIN_LLM_PRESENTER,
            "note": (
                f"{PLAIN_LLM_PRESENTER['note']} "
                "Guardrail: obvious non-IT; LLM not called."
            ),
        }

    out = llm.invoke(
        [
            SystemMessage(content=SYSTEM_IT_SUPPORT_ONLY),
            HumanMessage(content=user_message),
        ]
    )
    text = getattr(out, "content", str(out))
    return text, PLAIN_LLM_PRESENTER
