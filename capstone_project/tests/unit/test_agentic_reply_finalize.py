"""TDD: optional LLM merge for agentic + RAG."""

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def test_finalize_skips_when_no_rag_text():
    from backend.chat_demo.agentic_reply_finalize import finalize_agentic_reply_with_llm

    llm = MagicMock()
    out = finalize_agentic_reply_with_llm(
        llm,
        user_message="hi",
        triage={"category": "UNKNOWN"},
        ticket_id=None,
        rag={"kb_text": "", "db_text": ""},
        base_text="BASE",
    )
    assert out == "BASE"
    llm.invoke.assert_not_called()


def test_finalize_calls_llm_when_kb_present():
    from backend.chat_demo.agentic_reply_finalize import finalize_agentic_reply_with_llm

    class _Msg:
        content = "MERGED"

    llm = MagicMock()
    llm.invoke.return_value = _Msg()
    out = finalize_agentic_reply_with_llm(
        llm,
        user_message="VPN issue",
        triage={"category": "NETWORK"},
        ticket_id=5,
        rag={
            "kb_text": "AnyConnect steps...",
            "db_text": "",
            "kb_sources": ["vpn.md"],
            "db_sources": [],
        },
        base_text="Draft",
    )
    assert out == "MERGED"
    llm.invoke.assert_called_once()
    prompt = llm.invoke.call_args[0][0]
    assert "vpn.md" in prompt
    assert "Sources:" in prompt or "sources" in prompt.lower()


def test_finalize_falls_back_on_llm_error():
    from backend.chat_demo.agentic_reply_finalize import finalize_agentic_reply_with_llm

    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("api")

    out = finalize_agentic_reply_with_llm(
        llm,
        user_message="x",
        triage={},
        ticket_id=None,
        rag={"kb_text": "context", "db_text": ""},
        base_text="SAFE",
    )
    assert out == "SAFE"
