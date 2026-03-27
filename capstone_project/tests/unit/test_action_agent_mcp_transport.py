"""ActionAgent reports mcp_transport for chat demo trace."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def test_execute_action_includes_simulated_transport():
    from backend.agents.action_agent import ActionAgent

    agent = ActionAgent(use_real_mcp=False)
    with patch.object(agent, "_select_tool", return_value={"tool": "none", "params": {}, "confidence": 0}):
        out = agent.execute_action("hello", "u@x.com")
    assert out.get("mcp_transport") is None

    with patch.object(
        agent,
        "_select_tool",
        return_value={
            "tool": "check_vpn_status",
            "params": {"user_email": "u@x.com"},
            "confidence": 0.9,
            "selection_method": "llm",
        },
    ):
        out = agent.execute_action("check my vpn", "u@x.com")
    assert out.get("success") is True
    assert out.get("mcp_transport") == "simulated"
    assert out.get("selection_method") == "llm"
    assert out.get("params_used") == {"user_email": "u@x.com"}
