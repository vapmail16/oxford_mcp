"""TDD: agentic track fetches KB + DB RAG using the same entry points as rag_kb / rag_db."""

from typing import List, Tuple
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def test_fetch_agentic_rag_context_calls_kb_and_db():
    from backend.chat_demo.agentic_rag_retrieval import fetch_agentic_rag_context

    kb_calls: list = []

    def get_rag(q: str, k: int = 5) -> Tuple[str, List[str]]:
        kb_calls.append((q, k))
        return ("VPN doc chunk", ["vpn.md"])

    def get_db(db, q: str, k: int = 5) -> Tuple[str, List[str]]:
        assert q == "VPN error 422"
        return ("ticket 5 about VPN", ["db_ticket:5"])

    db = MagicMock()
    out = fetch_agentic_rag_context(
        message="VPN error 422",
        db_session=db,
        get_rag_context=get_rag,
        get_db_rag_context_fn=get_db,
        k=5,
    )
    assert out["kb_text"] == "VPN doc chunk"
    assert "vpn.md" in out["kb_sources"]
    assert "422" in out["db_text"] or "VPN" in out["db_text"]
    assert len(kb_calls) == 1
    assert "combined_context" in out


def test_fetch_agentic_rag_context_kb_only_when_no_db_fn():
    from backend.chat_demo.agentic_rag_retrieval import fetch_agentic_rag_context

    def get_rag(q: str, k: int = 5) -> Tuple[str, List[str]]:
        return ("x", ["a.md"])

    out = fetch_agentic_rag_context(
        message="hi",
        db_session=MagicMock(),
        get_rag_context=get_rag,
        get_db_rag_context_fn=None,
        k=3,
    )
    assert out["db_text"] == ""
    assert out["kb_text"] == "x"


def test_fetch_agentic_rag_context_survives_kb_exception():
    from backend.chat_demo.agentic_rag_retrieval import fetch_agentic_rag_context

    def boom(_q: str, k: int = 5) -> Tuple[str, List[str]]:
        raise RuntimeError("qdrant down")

    def get_db(db, q: str, k: int = 5) -> Tuple[str, List[str]]:
        return ("db ok", ["t:1"])

    out = fetch_agentic_rag_context(
        message="q",
        db_session=MagicMock(),
        get_rag_context=boom,
        get_db_rag_context_fn=get_db,
        k=5,
    )
    assert out["kb_text"] == ""
    assert "db ok" in out["db_text"]
    assert any("kb" in e.lower() for e in out.get("errors", []))
