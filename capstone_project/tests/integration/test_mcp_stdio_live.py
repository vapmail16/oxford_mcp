"""
Optional live check against the TypeScript MCP server (stdio).

Requires: `cd mcp_server && npm install`, `npx` on PATH, `mcp` Python package.
Run: `RUN_MCP_LIVE=1 pytest tests/integration/test_mcp_stdio_live.py -v`
"""

from __future__ import annotations

import os
import shutil

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.mcp]


@pytest.mark.skipif(os.getenv("RUN_MCP_LIVE") != "1", reason="Set RUN_MCP_LIVE=1 for real stdio MCP")
@pytest.mark.skipif(shutil.which("npx") is None, reason="npx not on PATH")
def test_stdio_mcp_agent_triage_returns_network_for_vpn_message():
    from backend.agents.mcp_stdio_client import call_mcp_tool_sync

    out = call_mcp_tool_sync(
        "agent_triage",
        {"user_message": "VPN keeps dropping", "user_email": "u@oxforduniversity.ac.uk"},
    )
    assert isinstance(out, dict)
    assert out.get("category") == "NETWORK"
