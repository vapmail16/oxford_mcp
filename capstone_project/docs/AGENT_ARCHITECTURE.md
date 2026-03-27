# Multi-Agent System Architecture

**Date**: 2026-03-11
**Status**: 🔄 **DESIGN PHASE**
**Approach**: Test-Driven Development

---

## 🎯 **Agent Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    USER QUERY                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              LANGGRAPH ORCHESTRATOR                         │
│  (State Management, Agent Routing, Error Handling)          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────┴──────────┐
              │   TRIAGE AGENT      │
              │  (Intent Classifier) │
              └──────────┬──────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌────────────┐  ┌────────────┐  ┌────────────┐
│ RAG AGENT  │  │   TICKET   │  │   ACTION   │
│ (Q&A from  │  │   AGENT    │  │   AGENT    │
│  docs)     │  │  (Create/  │  │ (Execute   │
│            │  │   Update)  │  │  tools)    │
└─────┬──────┘  └─────┬──────┘  └─────┬──────┘
      │               │               │
      └───────────────┼───────────────┘
                      │
                      ▼
              ┌────────────┐
              │  RESPONSE  │
              │   AGENT    │
              │ (Format &  │
              │  Verify)   │
              └─────┬──────┘
                    │
                    ▼
              ┌──────────┐
              │ DATABASE │
              │  (Store) │
              └──────────┘
```

---

## 🤖 **Agent Definitions**

### 1. **Triage Agent** (Intent Classifier)

**Purpose**: Route user queries to the appropriate specialist agent

**Responsibilities**:
- Classify user intent (question, ticket, action)
- Extract key information (category, priority, urgency)
- Determine which agent(s) to invoke
- Handle ambiguous queries

**Intents**:
- `QUESTION` → Route to RAG Agent
- `TICKET_CREATE` → Route to Ticket Agent
- `TICKET_UPDATE` → Route to Ticket Agent
- `ACTION_REQUEST` → Route to Action Agent
- `GREETING` → Handle directly
- `UNCLEAR` → Ask for clarification

**Input**: User message + conversation history
**Output**: Intent classification + routing decision

**Example**:
```python
Query: "VPN error 422"
→ Intent: QUESTION
→ Category: VPN
→ Priority: MEDIUM
→ Route: RAG Agent
```

---

### 2. **RAG Agent** (Question Answering)

**Purpose**: Answer questions using knowledge base

**Responsibilities**:
- Retrieve relevant context from Qdrant
- Generate answer using LLM + context
- Provide source attribution
- Detect if answer requires ticket creation

**Tools Available**:
- `retrieve_context(query, k)` - Get relevant docs
- `llm_answer(context, query)` - Generate response
- `assess_complexity()` - Determine if needs ticket

**Input**: Question + category + priority
**Output**: Answer + sources + confidence + needs_ticket

**Example**:
```python
Query: "How to fix VPN error 422?"
→ Retrieves: vpn_setup_guide.md
→ Generates: Step-by-step fix
→ Sources: ["vpn_setup_guide.md"]
→ Confidence: HIGH
→ Needs ticket: False
```

---

### 3. **Ticket Agent** (Ticket Management)

**Purpose**: Create and manage support tickets

**Responsibilities**:
- Create new tickets
- Update existing tickets
- Check ticket status
- Escalate complex issues
- Link related tickets

**Tools Available**:
- `create_ticket(title, desc, priority, category)`
- `update_ticket(id, status, note)`
- `get_ticket(id)`
- `search_tickets(query)`
- `escalate_ticket(id, reason)`

**Input**: Issue description + category + priority
**Output**: Ticket ID + status + next steps

**Example**:
```python
Query: "VPN still broken after following guide"
→ Creates ticket
→ Ticket ID: #1234
→ Priority: HIGH
→ Category: VPN
→ Status: OPEN
→ Assigned: IT Team
```

---

### 4. **Action Agent** (Tool Executor)

**Purpose**: Execute actions via MCP tools

**Responsibilities**:
- Execute system commands (via MCP)
- Check service status
- Reset passwords (via MCP)
- Restart services
- Verify fixes

**MCP Tools**:
- `check_vpn_status(user)` - Check VPN connection
- `reset_password(user)` - Trigger password reset
- `check_service(service)` - Check service health
- `send_notification(user, message)` - Send alert
- `create_jira_ticket(data)` - External integration

**Input**: Action request + parameters
**Output**: Action result + status

**Example**:
```python
Query: "Can you check if VPN server is up?"
→ MCP Tool: check_service("vpn")
→ Result: {status: "UP", latency: "12ms"}
→ Response: "VPN server is running normally"
```

---

### 5. **Response Agent** (Quality Assurance)

**Purpose**: Format and verify final responses

**Responsibilities**:
- Format response for user
- Add helpful context
- Include next steps
- Verify response quality
- Add follow-up suggestions

**Checks**:
- ✅ Is answer clear and actionable?
- ✅ Are sources cited?
- ✅ Are next steps included?
- ✅ Is tone professional?
- ✅ Are URLs/commands correct?

**Input**: Agent output + conversation context
**Output**: Formatted final response

---

## 🔄 **LangGraph State Machine**

### State Definition
```python
class AgentState(TypedDict):
    """Shared state across all agents"""
    # Input
    user_message: str
    session_id: str
    user_email: str

    # Triage
    intent: str  # QUESTION, TICKET_CREATE, ACTION_REQUEST
    category: str  # VPN, PASSWORD, WIFI, etc.
    priority: str  # LOW, MEDIUM, HIGH, URGENT

    # RAG Agent
    context: str
    sources: List[str]
    answer: str
    confidence: float
    needs_ticket: bool

    # Ticket Agent
    ticket_id: Optional[int]
    ticket_status: Optional[str]

    # Action Agent
    action_result: Optional[dict]

    # Response Agent
    final_response: str
    next_steps: List[str]

    # Metadata
    agent_path: List[str]  # Track which agents were called
    errors: List[str]
```

### Workflow Graph
```python
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("triage", triage_agent)
workflow.add_node("rag", rag_agent)
workflow.add_node("ticket", ticket_agent)
workflow.add_node("action", action_agent)
workflow.add_node("response", response_agent)

# Set entry point
workflow.set_entry_point("triage")

# Add conditional edges from triage
workflow.add_conditional_edges(
    "triage",
    route_to_agent,  # Function that returns next agent
    {
        "rag": "rag",
        "ticket": "ticket",
        "action": "action",
        "end": END
    }
)

# RAG can trigger ticket creation
workflow.add_conditional_edges(
    "rag",
    check_needs_ticket,
    {
        "ticket": "ticket",
        "response": "response"
    }
)

# All agents eventually go to response
workflow.add_edge("ticket", "response")
workflow.add_edge("action", "response")

# Response is the end
workflow.add_edge("response", END)
```

---

## 🛠️ **MCP Server Architecture**

### MCP Tools Server (TypeScript)

```typescript
// mcp_server/index.ts

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({
  name: "it-support-tools",
  version: "1.0.0"
});

// Tool 1: Check VPN Status
server.setRequestHandler("tools/call", async (request) => {
  if (request.params.name === "check_vpn_status") {
    const { username } = request.params.arguments;

    // Call actual VPN API
    const result = await checkVPNConnection(username);

    return {
      content: [{
        type: "text",
        text: JSON.stringify(result)
      }]
    };
  }
});

// Tool 2: Reset Password
server.setRequestHandler("tools/call", async (request) => {
  if (request.params.name === "reset_password") {
    const { username } = request.params.arguments;

    // Trigger password reset
    const result = await triggerPasswordReset(username);

    return {
      content: [{
        type: "text",
        text: JSON.stringify(result)
      }]
    };
  }
});

// Tool 3: Check Service Health
server.setRequestHandler("tools/call", async (request) => {
  if (request.params.name === "check_service") {
    const { service_name } = request.params.arguments;

    const health = await checkServiceHealth(service_name);

    return {
      content: [{
        type: "text",
        text: JSON.stringify(health)
      }]
    };
  }
});
```

### Python MCP Client

```python
# backend/agents/mcp_client.py

import asyncio
from mcp.client import Client

class MCPToolExecutor:
    """Client to execute MCP tools"""

    def __init__(self, server_url="http://localhost:3001"):
        self.server_url = server_url
        self.client = Client()

    async def check_vpn_status(self, username: str) -> dict:
        """Check VPN connection status"""
        result = await self.client.call_tool(
            "check_vpn_status",
            {"username": username}
        )
        return result

    async def reset_password(self, username: str) -> dict:
        """Trigger password reset"""
        result = await self.client.call_tool(
            "reset_password",
            {"username": username}
        )
        return result

    async def check_service(self, service_name: str) -> dict:
        """Check service health"""
        result = await self.client.call_tool(
            "check_service",
            {"service_name": service_name}
        )
        return result
```

---

## 📋 **Agent Implementation Plan (TDD)**

### Phase 1: Triage Agent (Week 3)

**Tests to Write (RED)**:
```python
def test_triage_vpn_question_routes_to_rag()
def test_triage_ticket_request_routes_to_ticket()
def test_triage_action_request_routes_to_action()
def test_triage_extracts_category_correctly()
def test_triage_determines_priority()
def test_triage_handles_ambiguous_query()
```

**Implementation (GREEN)**:
- Create `backend/agents/triage.py`
- Use LLM for intent classification
- Extract entities (category, priority)
- Return routing decision

### Phase 2: Enhanced RAG Agent (Week 3)

**Tests to Write (RED)**:
```python
def test_rag_retrieves_context()
def test_rag_generates_answer()
def test_rag_detects_needs_ticket()
def test_rag_low_confidence_escalates()
def test_rag_provides_sources()
```

**Implementation (GREEN)**:
- Enhance existing RAG retrieval
- Add confidence scoring
- Implement complexity detection
- Format with sources

### Phase 3: Ticket Agent (Week 4)

**Tests to Write (RED)**:
```python
def test_ticket_creates_from_description()
def test_ticket_updates_status()
def test_ticket_links_to_conversation()
def test_ticket_escalates_high_priority()
def test_ticket_searches_similar()
```

**Implementation (GREEN)**:
- Use existing database CRUD
- Add ticket creation logic
- Implement escalation rules
- Link tickets to sessions

### Phase 4: Action Agent + MCP (Week 4)

**Tests to Write (RED)**:
```python
def test_action_executes_mcp_tool()
def test_action_handles_tool_failure()
def test_action_validates_parameters()
def test_action_returns_formatted_result()
```

**Implementation (GREEN)**:
- Create MCP server (TypeScript)
- Implement MCP client (Python)
- Add tool wrappers
- Handle errors

### Phase 5: Response Agent (Week 4)

**Tests to Write (RED)**:
```python
def test_response_formats_answer()
def test_response_adds_next_steps()
def test_response_includes_sources()
def test_response_verifies_quality()
```

**Implementation (GREEN)**:
- Create formatting logic
- Add quality checks
- Include next steps
- Professional tone

### Phase 6: LangGraph Orchestration (Week 5)

**Tests to Write (RED)**:
```python
def test_workflow_simple_question()
def test_workflow_ticket_creation()
def test_workflow_action_execution()
def test_workflow_error_handling()
def test_workflow_state_persistence()
```

**Implementation (GREEN)**:
- Define state schema
- Create workflow graph
- Add conditional routing
- Implement error handling

---

## 🎯 **Example Workflows**

### Workflow 1: Simple Question
```
User: "How do I reset my password?"
  ↓
Triage: intent=QUESTION, category=PASSWORD, priority=LOW
  ↓
RAG Agent: retrieves password_reset_sop.md
  ↓
RAG Agent: generates answer, confidence=HIGH, needs_ticket=False
  ↓
Response Agent: formats with sources, adds next steps
  ↓
User: "To reset your password: 1. Go to..."
```

### Workflow 2: Complex Issue → Ticket
```
User: "VPN error 422, tried all fixes, still broken"
  ↓
Triage: intent=QUESTION, category=VPN, priority=HIGH
  ↓
RAG Agent: retrieves fixes, confidence=MEDIUM, needs_ticket=True
  ↓
Ticket Agent: creates ticket #1234, priority=HIGH
  ↓
Response Agent: combines answer + ticket info
  ↓
User: "Here's what to try... I've also created ticket #1234"
```

### Workflow 3: Action Request
```
User: "Can you check if the VPN server is working?"
  ↓
Triage: intent=ACTION_REQUEST, category=VPN
  ↓
Action Agent: calls MCP check_service("vpn")
  ↓
Action Agent: result={status: "UP", latency: "12ms"}
  ↓
Response Agent: formats result
  ↓
User: "VPN server is operating normally with 12ms latency"
```

### Workflow 4: Ticket Update
```
User: "What's the status of ticket #1234?"
  ↓
Triage: intent=TICKET_UPDATE, ticket_id=1234
  ↓
Ticket Agent: retrieves ticket, status=IN_PROGRESS
  ↓
Response Agent: formats status update
  ↓
User: "Ticket #1234 is in progress. IT is investigating..."
```

---

## 📊 **Success Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Triage Accuracy** | >95% | Intent classification correct |
| **RAG Relevance** | >90% | Retrieved docs relevant |
| **Ticket Auto-Create** | >80% | Complex issues → tickets |
| **Action Success** | >95% | MCP tools execute |
| **Response Quality** | >90% | User satisfaction score |
| **End-to-End Time** | <10s | Query to response |

---

## 🚀 **Next Steps**

1. **Create agent directory structure**
2. **Write triage agent tests (RED)**
3. **Implement triage agent (GREEN)**
4. **Write RAG agent tests (RED)**
5. **Enhance RAG agent (GREEN)**
6. **Create MCP server skeleton**
7. **Continue with remaining agents...**

Following TDD: **Test First, Then Implement!**

---

**Status**: 📋 **ARCHITECTURE COMPLETE - READY FOR IMPLEMENTATION**

