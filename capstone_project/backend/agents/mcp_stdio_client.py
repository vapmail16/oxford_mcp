"""
Call the TypeScript MCP server over stdio using the official Python MCP SDK.

Requires: `npm install` in `mcp_server/`, `npx` on PATH. Real stdio is the default; use
`USE_SIMULATED_MCP=1` for in-process Python stubs (e.g. unit tests).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

logger = logging.getLogger(__name__)

_CAPSTONE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_MCP_SERVER_DIR = os.path.join(_CAPSTONE_ROOT, "mcp_server")


async def _call_tool_async(tool_name: str, arguments: Dict[str, Any]) -> Any:
    from mcp import ClientSession
    from mcp import types as mcp_types
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command="npx",
        args=["tsx", "src/index.ts"],
        cwd=_MCP_SERVER_DIR,
        env={**os.environ},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments or {})
            chunks = []
            for block in result.content:
                if isinstance(block, mcp_types.TextContent):
                    chunks.append(block.text)
                elif getattr(block, "type", None) == "text" and getattr(block, "text", None):
                    chunks.append(block.text)
                elif isinstance(block, dict) and block.get("type") == "text":
                    chunks.append(block.get("text", ""))
            raw = "\n".join(chunks).strip()
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw, "isError": getattr(result, "isError", False)}


def call_mcp_tool_sync(tool_name: str, arguments: Dict[str, Any], timeout: float = 45.0) -> Any:
    """Run async MCP client in a worker thread (safe from inside FastAPI async views)."""

    def _run() -> Any:
        return asyncio.run(_call_tool_async(tool_name, arguments))

    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(_run)
        return fut.result(timeout=timeout)
