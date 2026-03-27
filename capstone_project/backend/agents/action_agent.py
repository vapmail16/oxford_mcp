"""
Action Agent - MCP Tool Execution
Executes IT support actions via MCP server
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class ActionAgent:
    """
    Action Agent executes IT support actions via MCP tools.

    Responsibilities:
    - Parse action requests from user
    - Select appropriate MCP tool
    - Execute tool with correct parameters
    - Parse and format tool results
    - Handle errors gracefully
    """

    def __init__(
        self,
        model: str = None,
        mcp_server_path: str = None,
        use_real_mcp: Optional[bool] = None,
    ):
        """Initialize action agent with LLM and MCP client"""
        self.llm = ChatOpenAI(
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0
        )

        if use_real_mcp is None:
            # Default: real MCP over stdio (TypeScript server under mcp_server/). Opt into
            # in-process simulation with USE_SIMULATED_MCP=1 (e.g. pytest) or USE_REAL_MCP=0.
            sim = os.getenv("USE_SIMULATED_MCP", "").lower() in ("1", "true", "yes")
            legacy_off = os.getenv("USE_REAL_MCP", "").lower() in ("0", "false", "no")
            self.use_real_mcp = not sim and not legacy_off
        else:
            self.use_real_mcp = use_real_mcp

        # MCP server path (reference for docs / future config)
        self.mcp_server_path = mcp_server_path or os.path.join(
            os.path.dirname(__file__),
            '../../mcp_server/src/index.ts'
        )

        # Available MCP tools
        self.available_tools = {
            'check_vpn_status': {
                'description': 'Check VPN connection status for a user',
                'params': ['user_email']
            },
            'reset_password': {
                'description': 'Reset user password and send reset link',
                'params': ['user_email', 'send_email']
            },
            'check_service_health': {
                'description': 'Check health of IT services',
                'params': ['service_name']
            },
            'run_network_diagnostic': {
                'description': 'Run network diagnostic tests',
                'params': ['user_email', 'test_type']
            },
            'check_printer_queue': {
                'description': 'Check printer queue and clear if needed',
                'params': ['printer_name', 'clear_queue']
            },
            'agent_triage': {
                'description': 'Classify user message into intent, category, and priority (chat pipeline step 1)',
                'params': ['user_message', 'user_email'],
            },
            'agent_log_ticket': {
                'description': 'Produce ticket title/metadata from triage (chat pipeline step 2; DB row created in Python)',
                'params': [
                    'user_message',
                    'user_email',
                    'intent',
                    'category',
                    'priority',
                ],
            },
            'agent_compose_response': {
                'description': 'Compose final user-facing reply from triage + ticket context (chat pipeline step 3)',
                'params': [
                    'user_message',
                    'user_email',
                    'triage',
                    'ticket_mcp',
                    'ticket_id',
                ],
            },
        }

        # Tool selection prompt
        self.tool_selection_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are parsing user requests for IT support actions.

Analyze the user's request and determine which tool to use.

Available tools:
{tools}

Respond with JSON:
{{
  "tool": "tool_name",
  "params": {{"param1": "value1"}},
  "confidence": 0.0-1.0
}}

If no tool matches, respond with {{"tool": "none", "confidence": 0.0}}"""),
            ("human", "User request: {request}\nUser email: {user_email}")
        ])

    def execute_action(
        self,
        request: str,
        user_email: str,
        classification: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an action based on user request.

        Args:
            request: User's action request
            user_email: User's email address
            classification: Optional triage classification

        Returns:
            Dict with action result
        """
        try:
            # Step 1: Determine which tool to use
            tool_selection = self._select_tool(request, user_email)

            if tool_selection['tool'] == 'none':
                return {
                    'success': False,
                    'message': (
                        'No suitable **action** tool matched. This demo picks **one** registered '
                        'MCP tool per turn (VPN check, password reset, …) — it does not answer '
                        'meta questions like “list every tool”.'
                    ),
                    'suggestion': 'Please rephrase your request or create a support ticket',
                    'mcp_transport': None,
                    'no_tool_match': True,
                    'selection_method': tool_selection.get('selection_method'),
                    'confidence': tool_selection.get('confidence'),
                    'demo_tip': (
                        'The model returned tool "none" because the request is not mapped to a '
                        'concrete IT action in available_tools.'
                    ),
                    'example_working_prompts': [
                        'Check my VPN status',
                        'Start a password reset for my account',
                    ],
                }

            # Step 2: Execute the tool
            tool_result = self._call_mcp_tool(
                tool_selection['tool'],
                tool_selection['params']
            )

            # Step 3: Format result for user
            formatted_result = self._format_result(
                tool_selection['tool'],
                tool_result
            )

            return {
                'success': True,
                'tool_used': tool_selection['tool'],
                'result': tool_result,
                'message': formatted_result,
                'confidence': tool_selection.get('confidence'),
                'selection_method': tool_selection.get('selection_method'),
                'params_used': tool_selection.get('params'),
                'mcp_transport': 'stdio_mcp' if self.use_real_mcp else 'simulated',
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to execute action: {str(e)}',
                'mcp_transport': 'error',
            }

    def _select_tool(self, request: str, user_email: str) -> Dict[str, Any]:
        """Select the appropriate MCP tool for the request"""
        try:
            # Format tools description
            tools_desc = '\n'.join([
                f"- {name}: {info['description']}"
                for name, info in self.available_tools.items()
            ])

            # Get LLM recommendation
            chain = self.tool_selection_prompt | self.llm
            response = chain.invoke({
                "request": request,
                "user_email": user_email,
                "tools": tools_desc
            })

            result = json.loads(response.content)
            if isinstance(result, dict):
                result.setdefault("selection_method", "llm")
            return result

        except Exception:
            # Fallback to rule-based selection
            result = self._rule_based_tool_selection(request, user_email)
            result["selection_method"] = "rule_based"
            return result

    def _rule_based_tool_selection(self, request: str, user_email: str) -> Dict[str, Any]:
        """Fallback rule-based tool selection"""
        request_lower = request.lower()

        # VPN check
        if 'vpn' in request_lower and 'check' in request_lower:
            return {
                'tool': 'check_vpn_status',
                'params': {'user_email': user_email},
                'confidence': 0.8
            }

        # Password reset
        if 'password' in request_lower and 'reset' in request_lower:
            return {
                'tool': 'reset_password',
                'params': {'user_email': user_email, 'send_email': True},
                'confidence': 0.8
            }

        # Service health
        if 'service' in request_lower or 'status' in request_lower:
            return {
                'tool': 'check_service_health',
                'params': {'service_name': 'all'},
                'confidence': 0.6
            }

        # Network diagnostic
        if 'network' in request_lower or 'connection' in request_lower:
            return {
                'tool': 'run_network_diagnostic',
                'params': {'user_email': user_email, 'test_type': 'full'},
                'confidence': 0.7
            }

        # Printer
        if 'printer' in request_lower or 'print' in request_lower:
            printer_name = 'main_office_printer'  # Default
            return {
                'tool': 'check_printer_queue',
                'params': {'printer_name': printer_name, 'clear_queue': False},
                'confidence': 0.7
            }

        return {
            'tool': 'none',
            'params': {},
            'confidence': 0.0
        }

    def _call_mcp_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Call MCP tool via stdio (default) or in-process simulation (tests / USE_SIMULATED_MCP)."""
        if self.use_real_mcp:
            try:
                from backend.agents.mcp_stdio_client import call_mcp_tool_sync
            except ImportError as err:
                raise RuntimeError(
                    "USE_REAL_MCP is enabled but the `mcp` package is not installed. "
                    "Add `mcp` to requirements and pip install."
                ) from err
            return call_mcp_tool_sync(tool_name, params)
        return self._simulate_mcp_tool(tool_name, params)

    def _simulate_mcp_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """In-process stand-in for the TS MCP server (pytest / USE_SIMULATED_MCP=1 only)."""
        if tool_name == 'check_vpn_status':
            return {
                'status': 'connected',
                'user_email': params.get('user_email'),
                'latency_ms': 45,
                'server': 'vpn-us-east-1',
                'last_connected': '2026-03-11T22:30:00Z'
            }

        elif tool_name == 'reset_password':
            return {
                'success': True,
                'user_email': params.get('user_email'),
                'email_sent': params.get('send_email', True),
                'reset_link': 'https://portal.acme.com/reset?token=abc123',
                'expires_in': '24 hours'
            }

        elif tool_name == 'check_service_health':
            service = params.get('service_name', 'all')
            if service == 'all':
                return {
                    'overall_status': 'operational',
                    'services': {
                        'email': {'status': 'operational', 'uptime': '99.9%'},
                        'vpn': {'status': 'operational', 'uptime': '99.5%'},
                        'wifi': {'status': 'operational', 'uptime': '99.8%'}
                    }
                }
            else:
                return {
                    'service_name': service,
                    'status': 'operational',
                    'uptime': '99.9%',
                    'response_time_ms': 45
                }

        elif tool_name == 'run_network_diagnostic':
            return {
                'user_email': params.get('user_email'),
                'test_type': params.get('test_type', 'ping'),
                'overall_status': 'healthy',
                'tests': {
                    'ping': {
                        'packets_sent': 4,
                        'packets_received': 4,
                        'avg_latency_ms': 15,
                        'status': 'success'
                    }
                }
            }

        elif tool_name == 'check_printer_queue':
            return {
                'printer_name': params.get('printer_name'),
                'status': 'idle',
                'queue_length': 0,
                'message': 'Printer is ready'
            }

        elif tool_name == 'agent_triage':
            msg = (params.get('user_message') or '').lower()
            if 'password' in msg:
                category = 'PASSWORD'
            elif any(
                w in msg for w in ('vpn', 'wifi', 'network', 'dns', 'connection')
            ):
                category = 'NETWORK'
            elif any(w in msg for w in ('software', 'excel', 'outlook', 'install')):
                category = 'SOFTWARE'
            elif any(w in msg for w in ('laptop', 'screen', 'printer', 'hardware')):
                category = 'HARDWARE'
            elif 'access' in msg or 'permission' in msg:
                category = 'ACCESS'
            else:
                category = 'UNKNOWN'
            priority = 'HIGH' if any(
                w in msg for w in ('urgent', 'critical', 'down', 'outage')
            ) else 'MEDIUM'
            return {
                'intent': 'SUPPORT_REQUEST',
                'category': category,
                'priority': priority,
                'confidence': 0.86,
                'rationale': 'Simulated triage via keyword rules (MCP)',
            }

        elif tool_name == 'agent_log_ticket':
            snippet = (params.get('user_message') or '')[:72].strip()
            title = (params.get('title_suggestion') or '').strip() or (
                f"Support: {snippet}" if snippet else 'IT support request'
            )
            return {
                'title_suggestion': title[:200],
                'mcp_stage': 'ready_for_db',
                'category': params.get('category'),
                'priority': params.get('priority'),
            }

        elif tool_name == 'agent_compose_response':
            from backend.chat_demo.compose_support_reply import (
                build_support_reply,
                coerce_rag_source_arg,
            )

            triage = params.get('triage') or {}
            reply = build_support_reply(
                user_message=str(params.get('user_message') or ''),
                triage=triage if isinstance(triage, dict) else {},
                ticket_id=params.get('ticket_id'),
                source_note='simulated MCP',
                rag_kb_text=str(params.get('rag_kb_text') or ''),
                rag_db_text=str(params.get('rag_db_text') or ''),
                rag_kb_sources=coerce_rag_source_arg(params.get('rag_kb_sources')),
                rag_db_sources=coerce_rag_source_arg(params.get('rag_db_sources')),
            )
            return {'reply': reply, 'tone': 'professional'}

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _format_result(self, tool_name: str, result: Any) -> str:
        """Format tool result for user-friendly display"""
        if tool_name == 'check_vpn_status':
            status = result.get('status', 'unknown')
            if status == 'connected':
                return f"✅ VPN Status: Connected to {result.get('server')}\nLatency: {result.get('latency_ms')}ms"
            else:
                return f"❌ VPN Status: Disconnected\nLast connected: {result.get('last_connected')}"

        elif tool_name == 'reset_password':
            if result.get('success'):
                return f"✅ Password reset initiated for {result.get('user_email')}\nReset link sent via email. Link expires in {result.get('expires_in')}."
            else:
                return "❌ Password reset failed. Please try again or contact support."

        elif tool_name == 'check_service_health':
            if 'overall_status' in result:
                status = result['overall_status']
                return f"🔍 Service Health: {status.upper()}\n" + \
                       '\n'.join([f"- {name}: {info['status']}" for name, info in result.get('services', {}).items()])
            else:
                service = result.get('service_name')
                status = result.get('status')
                uptime = result.get('uptime')
                return f"🔍 {service.upper()}: {status} (Uptime: {uptime})"

        elif tool_name == 'run_network_diagnostic':
            overall = result.get('overall_status', 'unknown')
            return f"🌐 Network Diagnostic: {overall.upper()}\n" + \
                   f"Ping test: {result.get('tests', {}).get('ping', {}).get('status', 'N/A')}\n" + \
                   f"Recommendation: {result.get('recommendation', 'No issues detected')}"

        elif tool_name == 'check_printer_queue':
            return f"🖨️ {result.get('printer_name')}: {result.get('message')}\n" + \
                   f"Queue length: {result.get('queue_length')}"

        else:
            return str(result)


if __name__ == "__main__":
    """Test action agent"""
    agent = ActionAgent()

    print("=" * 60)
    print("Action Agent Test")
    print("=" * 60)

    # Test 1: VPN check
    result1 = agent.execute_action(
        request="Check my VPN status",
        user_email="test@acme.com"
    )
    print("\n✓ Test 1: VPN Check")
    print(f"Success: {result1['success']}")
    print(f"Tool: {result1.get('tool_used')}")
    print(f"Message:\n{result1.get('message')}")

    # Test 2: Password reset
    result2 = agent.execute_action(
        request="Reset my password",
        user_email="test@acme.com"
    )
    print("\n✓ Test 2: Password Reset")
    print(f"Success: {result2['success']}")
    print(f"Message:\n{result2.get('message')}")

    # Test 3: Service health
    result3 = agent.execute_action(
        request="Check service status",
        user_email="test@acme.com"
    )
    print("\n✓ Test 3: Service Health")
    print(f"Success: {result3['success']}")
    print(f"Message:\n{result3.get('message')}")

    print("\n" + "=" * 60)
    print("Action Agent working successfully!")
    print("=" * 60)
