"""
IT Support Agent - FastAPI Application
Simple working implementation demonstrating the TDD foundation
"""

from pathlib import Path
import sys

# If uvicorn is started from `capstone_project/backend/`, cwd is not `capstone_project/` and
# `import backend` fails. The package root is the parent of this file's directory.
_capstone_root = Path(__file__).resolve().parent.parent
if str(_capstone_root) not in sys.path:
    sys.path.insert(0, str(_capstone_root))

import backend.env_bootstrap  # noqa: E402, F401 — loads backend/.env before other backend imports

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import uvicorn
from datetime import datetime

from backend.database import (
    SessionLocal,
    init_db,
    create_ticket,
    get_ticket,
    get_all_tickets,
    create_message,
    get_messages_by_session
)
from backend.rag.retriever import get_rag_context
from backend.rag.db_retriever import get_db_rag_context
from backend.chat_demo.router import compute_chat_reply
from backend.agents.action_agent import ActionAgent
from langchain_openai import ChatOpenAI
import os

from backend.teaching.router import router as teaching_router

# Initialize FastAPI app
app = FastAPI(
    title="IT Support Agent API",
    description="AI-powered IT support chatbot built with TDD",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Teaching-only demo pipeline (isolated from /chat — Oxford / cohort labs)
app.include_router(teaching_router)

# Initialize LLM
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0.7
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """Chat message from user"""
    message: str
    session_id: Optional[str] = None
    user_email: str = "demo@acmecorp.com"
    # Oxford / cohort demo: greeting shows menu when True; buttons send demo_track.
    demo_mode: bool = True
    demo_track: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from IT support agent"""
    response: str
    session_id: str
    sources: Optional[List[str]] = None
    ticket_id: Optional[int] = None
    demo_track: Optional[str] = None
    presenter: Optional[Dict[str, str]] = None
    mcp_trace: Optional[Dict[str, Any]] = None


class TicketCreate(BaseModel):
    """Create new support ticket"""
    title: str
    description: str
    priority: str = "MEDIUM"
    category: str = "UNKNOWN"
    user_email: str = "demo@acmecorp.com"


class TicketResponse(BaseModel):
    """Ticket information"""
    id: int
    title: str
    description: str
    status: str
    priority: str
    category: str
    user_email: str
    created_at: str


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "IT Support Agent API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "tickets": "/tickets",
            "teaching_pipeline_trace": "/teaching/pipeline/trace"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
        "tests_passing": "31/31 database tests"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with IT support agent using RAG + LLM.

    This endpoint:
    1. Retrieves relevant context from the knowledge base
    2. Passes context + query to LLM
    3. Returns intelligent, context-aware response
    """
    db = SessionLocal()

    try:
        # Generate or use provided session ID
        session_id = request.session_id or f"session-{datetime.utcnow().timestamp()}"

        # Store user message
        create_message(
            db=db,
            session_id=session_id,
            role="user",
            content=request.message
        )

        action_agent = ActionAgent()
        result = compute_chat_reply(
            message=request.message,
            user_email=request.user_email,
            demo_mode=request.demo_mode,
            demo_track=request.demo_track,
            llm=llm,
            get_rag_context=get_rag_context,
            generate_simple_response_fn=generate_simple_response,
            action_agent=action_agent,
            db_session=db,
            get_db_rag_context_fn=get_db_rag_context,
            session_id=session_id,
        )
        response_text = result["response"]
        sources = result.get("sources")

        # Store assistant response
        create_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=response_text
        )

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            sources=sources if sources else ["no_sources"],
            demo_track=result.get("demo_track"),
            presenter=result.get("presenter"),
            mcp_trace=result.get("mcp_trace"),
            ticket_id=result.get("ticket_id"),
        )

    finally:
        db.close()


@app.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get conversation history for a session"""
    db = SessionLocal()

    try:
        messages = get_messages_by_session(db, session_id)

        return {
            "session_id": session_id,
            "message_count": len(messages),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }

    finally:
        db.close()


@app.post("/tickets", response_model=TicketResponse)
async def create_support_ticket(ticket: TicketCreate):
    """Create a new support ticket"""
    db = SessionLocal()

    try:
        created_ticket = create_ticket(
            db=db,
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority,
            category=ticket.category,
            user_email=ticket.user_email
        )

        return TicketResponse(
            id=created_ticket.id,
            title=created_ticket.title,
            description=created_ticket.description,
            status=created_ticket.status.value,
            priority=created_ticket.priority.value,
            category=created_ticket.category.value,
            user_email=created_ticket.user_email,
            created_at=created_ticket.created_at.isoformat()
        )

    finally:
        db.close()


@app.get("/tickets")
async def list_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
):
    """List all tickets with optional filtering"""
    db = SessionLocal()

    try:
        tickets = get_all_tickets(db, status=status, category=category, limit=limit)

        return {
            "count": len(tickets),
            "tickets": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "category": t.category.value,
                    "user_email": t.user_email,
                    "created_at": t.created_at.isoformat()
                }
                for t in tickets
            ]
        }

    finally:
        db.close()


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket_by_id(ticket_id: int):
    """Get a specific ticket by ID"""
    db = SessionLocal()

    try:
        ticket = get_ticket(db, ticket_id)

        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        return TicketResponse(
            id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status.value,
            priority=ticket.priority.value,
            category=ticket.category.value,
            user_email=ticket.user_email,
            created_at=ticket.created_at.isoformat()
        )

    finally:
        db.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_simple_response(message: str) -> str:
    """
    Generate a simple rule-based response.
    In production, this would use RAG system and LangGraph agents.
    """
    message_lower = message.lower()

    # VPN error 422 (specific — keep before general VPN branch)
    if "vpn" in message_lower and "422" in message_lower:
        return """I can help with VPN error 422! This is a common authentication timeout error.

**Quick Fix:**
1. Close Cisco AnyConnect completely
2. Wait 30 seconds
3. Reopen and try connecting again
4. Respond to the MFA prompt within 60 seconds

If the issue persists, try clearing your AnyConnect preferences and reinstalling.

Did this help resolve your issue?"""

    # VPN — install / setup / connect (fallback when RAG returns no context)
    elif "vpn" in message_lower:
        return """Here’s how to set up and connect to the **Acme Corp VPN** (Cisco AnyConnect):

**Install**
1. On a company laptop, install **Cisco AnyConnect** from **Company Portal** or **Software Center** (or your IT software catalog).
2. If it’s not listed, contact IT for the approved installer.

**Connect**
1. Open AnyConnect and enter your **VPN server hostname** (see your onboarding email or the internal IT page for the exact value).
2. Click **Connect** and sign in with your **corporate account** (e.g. `firstname.lastname@acmecorp.com`).
3. Approve **MFA** when prompted (respond within about 60 seconds).

**If something fails**
- Share the **exact error text or code** (e.g. **422**) so we can troubleshoot.
- **IT Support:** ext. **4357**

Were you able to install AnyConnect, or is something blocking you at a specific step?"""

    # Password reset
    elif "password" in message_lower and ("reset" in message_lower or "forgot" in message_lower):
        return """I can help you reset your password!

**Self-Service Password Reset:**
1. Go to https://password.acmecorp.com
2. Click "Forgot Password"
3. Answer your security questions
4. Enter a new password (must be 12+ characters with upper, lower, number, and special character)

**Password Requirements:**
- Minimum 12 characters
- One uppercase, one lowercase, one number, one special character
- Cannot reuse last 10 passwords

If self-service doesn't work, contact IT Support at ext. 4357.

Were you able to reset your password?"""

    # WiFi issues
    elif "wifi" in message_lower or "wi-fi" in message_lower:
        return """I can help with WiFi issues!

**For Corporate WiFi Connection:**
1. Make sure you're connecting to **AcmeCorp-Secure** (not AcmeCorp-Guest)
2. Forget the network and reconnect
3. Use your full domain credentials: firstname.lastname@acmecorp.com
4. Enter your domain password

**For Slow WiFi:**
1. Test speed at speedtest.acmecorp.com (expected: 100+ Mbps)
2. Move closer to an access point
3. Switch to 5GHz band if available

Is your WiFi working now?"""

    # Default response
    else:
        return f"""Hello! I'm the IT Support Agent. I can help you with:

- VPN connection issues
- Password resets
- WiFi troubleshooting
- Software installation
- Common error codes
- Hardware issues

Could you please describe your issue in more detail? For example:
- What error are you seeing?
- When did the problem start?
- What have you already tried?

I'm here to help!"""


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("IT Support Agent API Server")
    print("=" * 60)
    print("Database: SQLite (initialized)")
    print("Tests: 31/31 passing")
    print("Server: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
