"""TDD: compute_chat_reply routes demo tracks vs legacy RAG chat."""

from typing import List, Tuple
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def _legacy_simple(msg: str) -> str:
    return f"legacy:{msg}"


class TestComputeChatReply:
    def test_menu_track_returns_markdown_three_options(self):
        from backend.chat_demo.router import compute_chat_reply

        llm = MagicMock()
        get_rag = MagicMock()
        agent = MagicMock()

        out = compute_chat_reply(
            message="Hi",
            user_email="a@b.com",
            demo_mode=True,
            demo_track="menu",
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=MagicMock(),
            get_db_rag_context_fn=MagicMock(),
        )

        assert out["demo_track"] == "menu"
        assert "Direct LLM" in out["response"]
        assert "Knowledge base RAG" in out["response"] or "RAG" in out["response"]
        assert "DB RAG" in out["response"] or "rag_db" in out["response"]
        assert "Agentic MCP" in out["response"]
        assert out["presenter"] is None
        assert out["mcp_trace"] is None
        llm.invoke.assert_not_called()
        get_rag.assert_not_called()

    def test_plain_llm_does_not_call_get_rag_context(self):
        from backend.chat_demo.router import compute_chat_reply

        class _Msg:
            content = "ok"

        llm = MagicMock()
        llm.invoke.return_value = _Msg()
        get_rag = MagicMock()
        agent = MagicMock()

        out = compute_chat_reply(
            message="Say hi in one word.",
            user_email="a@b.com",
            demo_mode=True,
            demo_track="plain_llm",
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=MagicMock(),
            get_db_rag_context_fn=MagicMock(),
        )

        assert out["demo_track"] == "plain_llm"
        get_rag.assert_not_called()
        assert out["presenter"] is not None
        assert out["presenter"].get("file", "").endswith("plain_llm.py")

    def test_rag_kb_calls_get_rag_context(self):
        from backend.chat_demo.router import compute_chat_reply

        class _Msg:
            content = "answer from kb"

        llm = MagicMock()
        llm.invoke.return_value = _Msg()

        def get_rag(q: str, k: int = 5) -> Tuple[str, List[str]]:
            return ("chunk about VPN", ["vpn.md"])

        agent = MagicMock()

        out = compute_chat_reply(
            message="VPN error",
            user_email="a@b.com",
            demo_mode=True,
            demo_track="rag_kb",
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=MagicMock(),
            get_db_rag_context_fn=MagicMock(),
        )

        assert out["demo_track"] == "rag_kb"
        assert "answer from kb" in out["response"]
        assert "Sources:" in out["response"]
        assert "vpn.md" in out["response"]
        assert "vpn.md" in (out.get("sources") or [])

    def test_agentic_mcp_runs_three_step_mcp_pipeline(self, db_session):
        from backend.agents.action_agent import ActionAgent
        from backend.chat_demo.router import compute_chat_reply

        llm = MagicMock()
        get_rag = MagicMock(return_value=("", []))
        get_db_rag = MagicMock(return_value=("", []))
        agent = ActionAgent(use_real_mcp=False)

        out = compute_chat_reply(
            message="My VPN keeps disconnecting",
            user_email="u@oxforduniversity.ac.uk",
            demo_mode=True,
            demo_track="agentic_mcp",
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=db_session,
            get_db_rag_context_fn=get_db_rag,
            session_id="sess-router-mcp",
        )

        assert out["demo_track"] == "agentic_mcp"
        assert out.get("ticket_id") is not None
        trace = out["mcp_trace"]
        assert trace["pipeline"] == "triage→rag→ticket→respond"
        assert len(trace["steps"]) == 4
        assert trace["steps"][0]["tool"] == "agent_triage"
        assert trace["steps"][1]["tool"] == "agent_retrieve_kb_db"
        assert trace["steps"][2]["tool"] == "agent_log_ticket"
        assert trace["steps"][3]["tool"] == "agent_compose_response"
        assert trace["transport"] == "simulated"
        assert "how_agentic_works" in trace
        assert "**Triage:**" in out["response"] or "Triage" in out["response"]
        get_rag.assert_called_once()
        get_db_rag.assert_called_once()

    def test_agentic_mcp_trace_has_three_steps_not_single_tool_none(self, db_session):
        """Replaces old no_tool_match case: pipeline always performs three MCP calls."""
        from backend.agents.action_agent import ActionAgent
        from backend.chat_demo.router import compute_chat_reply

        llm = MagicMock()
        get_rag = MagicMock(return_value=("", []))
        get_db_rag = MagicMock(return_value=("", []))
        agent = ActionAgent(use_real_mcp=False)

        out = compute_chat_reply(
            message="List every MCP tool in the project",
            user_email="u@oxforduniversity.ac.uk",
            demo_mode=True,
            demo_track="agentic_mcp",
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=db_session,
            get_db_rag_context_fn=get_db_rag,
            session_id="sess-meta",
        )

        assert out["mcp_trace"].get("no_tool_match") is not True
        assert len(out["mcp_trace"]["steps"]) == 4

    def test_legacy_path_when_no_effective_track(self):
        from backend.chat_demo.router import compute_chat_reply

        class _Msg:
            content = "rag answer"

        llm = MagicMock()
        llm.invoke.return_value = _Msg()
        get_rag = MagicMock(
            return_value=("some context", ["doc.md"])
        )
        agent = MagicMock()

        out = compute_chat_reply(
            message="WiFi slow",
            user_email="a@b.com",
            demo_mode=False,
            demo_track=None,
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=MagicMock(),
            get_db_rag_context_fn=MagicMock(),
        )

        assert out["demo_track"] is None
        get_rag.assert_called_once()
        assert "rag answer" in out["response"]
        assert "Sources:" in out["response"]
        assert "doc.md" in out["response"]

    def test_rag_db_calls_get_db_rag_context(self):
        from backend.chat_demo.router import compute_chat_reply

        class _Msg:
            content = "from tickets"

        llm = MagicMock()
        llm.invoke.return_value = _Msg()
        get_rag = MagicMock()
        agent = MagicMock()
        db_sess = MagicMock()

        def get_db_rag(db, q: str, k: int = 5):
            return ("ticket #1 VPN outage", ["db_ticket:1"])

        out = compute_chat_reply(
            message="Any VPN tickets?",
            user_email="a@b.com",
            demo_mode=True,
            demo_track="rag_db",
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=db_sess,
            get_db_rag_context_fn=get_db_rag,
        )

        assert out["demo_track"] == "rag_db"
        assert "from tickets" in out["response"]
        assert "Sources:" in out["response"]
        assert "db_ticket:1" in out["response"]
        get_rag.assert_not_called()
        assert out["presenter"] and "db_retriever" in out["presenter"].get("file", "")

    def test_rag_db_when_get_db_rag_raises_falls_back_to_simple_response(self):
        """Same pattern as rag_kb: failed retrieval → rule-based fallback, no LLM."""
        from backend.chat_demo.router import compute_chat_reply

        llm = MagicMock()
        get_rag = MagicMock()
        agent = MagicMock()

        def get_db_rag_boom(_db, _q: str, k: int = 5):
            raise RuntimeError("qdrant unavailable")

        out = compute_chat_reply(
            message="Summarize VPN tickets",
            user_email="a@b.com",
            demo_mode=True,
            demo_track="rag_db",
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=MagicMock(),
            get_db_rag_context_fn=get_db_rag_boom,
        )

        assert out["demo_track"] == "rag_db"
        assert out["response"] == "legacy:Summarize VPN tickets"
        assert out["sources"] == ["fallback"]
        llm.invoke.assert_not_called()
        get_rag.assert_not_called()

    def test_legacy_falls_back_to_simple_when_no_context(self):
        from backend.chat_demo.router import compute_chat_reply

        llm = MagicMock()
        get_rag = MagicMock(return_value=("", []))
        agent = MagicMock()

        out = compute_chat_reply(
            message="WiFi slow",
            user_email="a@b.com",
            demo_mode=False,
            demo_track=None,
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=MagicMock(),
            get_db_rag_context_fn=MagicMock(),
        )

        assert out["response"] == "legacy:WiFi slow"
        llm.invoke.assert_not_called()

    def test_legacy_ticket_escalation_when_no_kb_and_session(self, monkeypatch):
        """KB empty + session_id → try_create_ticket_from_escalation may create a ticket."""
        from backend.chat_demo import router as router_mod
        from backend.chat_demo.router import compute_chat_reply

        llm = MagicMock()
        get_rag = MagicMock(return_value=("", []))
        agent = MagicMock()

        def fake_esc(_db, *, message, user_email, session_id):
            if "urgent" in message.lower() and "issue" in message.lower():
                return (
                    7,
                    "HIGH",
                    "UNKNOWN",
                    "### Ticket\nCreated ticket 7.",
                )
            return None

        monkeypatch.setattr(router_mod, "try_create_ticket_from_escalation", fake_esc)

        out = compute_chat_reply(
            message="I have an urgent issue with my laptop",
            user_email="u@oxforduniversity.ac.uk",
            demo_mode=False,
            demo_track=None,
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=MagicMock(),
            get_db_rag_context_fn=MagicMock(),
            session_id="sess-1",
        )

        assert out["demo_track"] == "agentic_ticket"
        assert out["ticket_id"] == 7
        assert "Ticket" in out["response"]
        assert out["sources"] == ["ticket_escalation"]

    def test_rag_kb_non_it_skips_rag_and_llm(self):
        from backend.chat_demo.router import compute_chat_reply

        llm = MagicMock()
        get_rag = MagicMock()
        agent = MagicMock()

        out = compute_chat_reply(
            message="what is the capital of france",
            user_email="a@b.com",
            demo_mode=True,
            demo_track="rag_kb",
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=MagicMock(),
            get_db_rag_context_fn=MagicMock(),
        )

        assert out["demo_track"] == "rag_kb"
        assert out["sources"] == ["guardrail"]
        assert "Oxford University IT" in out["response"]
        get_rag.assert_not_called()
        llm.invoke.assert_not_called()

    def test_legacy_non_it_skips_rag(self):
        from backend.chat_demo.router import compute_chat_reply

        llm = MagicMock()
        get_rag = MagicMock()
        agent = MagicMock()

        out = compute_chat_reply(
            message="what is the capital of france",
            user_email="a@b.com",
            demo_mode=False,
            demo_track=None,
            llm=llm,
            get_rag_context=get_rag,
            generate_simple_response_fn=_legacy_simple,
            action_agent=agent,
            db_session=MagicMock(),
            get_db_rag_context_fn=MagicMock(),
        )

        assert out["sources"] == ["guardrail"]
        assert "Oxford University IT" in out["response"]
        get_rag.assert_not_called()
        llm.invoke.assert_not_called()
