"""TDD: ActionAgent records whether the LLM or rule-based routing chose the MCP tool."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def test_select_tool_marks_rule_based_when_chain_raises():
    from backend.agents.action_agent import ActionAgent

    agent = ActionAgent(use_real_mcp=False)
    broken_pipe = MagicMock()
    broken_pipe.invoke.side_effect = RuntimeError("LLM unavailable")

    with patch.object(agent, "tool_selection_prompt") as prompt:
        prompt.__or__.return_value = broken_pipe
        out = agent._select_tool("Check my VPN status", "u@oxforduniversity.ac.uk")

    assert out["selection_method"] == "rule_based"
    assert out["tool"] == "check_vpn_status"


def test_select_tool_marks_llm_when_json_ok():
    from backend.agents.action_agent import ActionAgent

    agent = ActionAgent(use_real_mcp=False)
    ok_pipe = MagicMock()
    ok_pipe.invoke.return_value = MagicMock(
        content='{"tool":"check_vpn_status","params":{"user_email":"a@b.com"},"confidence":0.95}'
    )

    with patch.object(agent, "tool_selection_prompt") as prompt:
        prompt.__or__.return_value = ok_pipe
        out = agent._select_tool("vpn check", "a@b.com")

    assert out["selection_method"] == "llm"
    assert out["tool"] == "check_vpn_status"
