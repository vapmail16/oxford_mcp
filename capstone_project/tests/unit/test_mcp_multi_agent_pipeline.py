"""TDD: triage → RAG → ticket → respond pipeline; MCP tools + Python RAG + optional LLM."""

import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.unit


def test_pipeline_runs_mcp_tools_rag_step_and_creates_ticket(db_session):
    from backend.agents.action_agent import ActionAgent
    from backend.chat_demo.mcp_multi_agent_pipeline import (
        RAG_TOOL,
        RESPOND_TOOL,
        TICKET_TOOL,
        TRIAGE_TOOL,
        run_mcp_three_agent_pipeline,
    )

    agent = ActionAgent(use_real_mcp=False)
    calls: list[tuple[str, dict]] = []

    def _wrap(name: str, params: dict):
        calls.append((name, params))
        return agent._simulate_mcp_tool(name, params)

    agent._call_mcp_tool = _wrap  # type: ignore[assignment]

    def get_rag(m: str, k: int = 5):
        return ("KB snippet about VPN", ["vpn.md"])

    def get_db(db, m: str, k: int = 5):
        return ("", [])

    out = run_mcp_three_agent_pipeline(
        action_agent=agent,
        message="I cannot connect to the VPN from home",
        user_email="u@oxforduniversity.ac.uk",
        db_session=db_session,
        session_id="sess-pipe-1",
        get_rag_context=get_rag,
        get_db_rag_context_fn=get_db,
        llm=None,
    )

    assert [c[0] for c in calls] == [TRIAGE_TOOL, TICKET_TOOL, RESPOND_TOOL]
    assert "rag_kb_text" in calls[2][1] or calls[2][1].get("rag_kb_text")
    assert out["ticket_id"] is not None
    assert "VPN" in calls[0][1]["user_message"]
    trace = out["mcp_trace"]
    assert trace["pipeline"] == "triage→rag→ticket→respond"
    assert len(trace["steps"]) == 4
    assert trace["steps"][0]["tool"] == TRIAGE_TOOL
    assert trace["steps"][1]["tool"] == RAG_TOOL
    assert trace["steps"][1]["transport"] == "python_rag"
    assert trace["steps"][2]["tool"] == TICKET_TOOL
    assert trace["steps"][3]["tool"] == RESPOND_TOOL
    assert "**Triage:**" in out["response"]
    assert "agentic_mcp" in (out.get("sources") or [])


def test_pipeline_triage_categories_password(db_session):
    from backend.agents.action_agent import ActionAgent
    from backend.chat_demo.mcp_multi_agent_pipeline import run_mcp_three_agent_pipeline

    agent = ActionAgent(use_real_mcp=False)

    def get_rag(_m: str, k: int = 5):
        return ("", [])

    out = run_mcp_three_agent_pipeline(
        action_agent=agent,
        message="I need to reset my password urgently",
        user_email="a@b.com",
        db_session=db_session,
        session_id="sess-p2",
        get_rag_context=get_rag,
        get_db_rag_context_fn=None,
        llm=None,
    )
    assert out["ticket_id"] is not None
    triage_step = out["mcp_trace"]["steps"][0]["result_summary"]
    assert "PASSWORD" in triage_step or "password" in triage_step.lower()


def test_pipeline_llm_finalize_when_kb_context_exists(db_session):
    from backend.agents.action_agent import ActionAgent
    from backend.chat_demo.mcp_multi_agent_pipeline import run_mcp_three_agent_pipeline

    class _Msg:
        content = "FINAL_FROM_LLM"

    llm = MagicMock()
    llm.invoke.return_value = _Msg()
    agent = ActionAgent(use_real_mcp=False)

    def get_rag(_m: str, k: int = 5):
        return ("Some KB text for merge", ["x.md"])

    def get_db(_db, _m: str, k: int = 5):
        return ("", [])

    out = run_mcp_three_agent_pipeline(
        action_agent=agent,
        message="VPN help",
        user_email="u@oxforduniversity.ac.uk",
        db_session=db_session,
        session_id="sess-llm",
        get_rag_context=get_rag,
        get_db_rag_context_fn=get_db,
        llm=llm,
    )
    assert "FINAL_FROM_LLM" in out["response"]
    llm.invoke.assert_called_once()
