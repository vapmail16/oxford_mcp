"""
Teaching API basics — business logic separated from FastAPI routes.
In-memory notes + optional DB writes via existing CRUD.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional, Tuple

from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from backend.database.crud import create_message

# In-memory notes for GET/PUT/DELETE teaching strip (not production)
_notes: Dict[int, str] = {}
_next_note_id: int = 1


def ping_payload() -> dict[str, Any]:
    return {
        "method": "GET",
        "path": "/teaching/api-basics/ping",
        "status_code": 200,
        "status_meaning": "OK — request succeeded, response has a body.",
    }


def echo_message(message: str) -> dict[str, Any]:
    return {
        "method": "POST",
        "path": "/teaching/api-basics/echo",
        "status_code": 200,
        "status_meaning": "OK — resource created/processed; often used for actions that return a body (201 is common for *created* entities).",
        "echo": message.strip(),
    }


def invoke_teaching_llm(llm: ChatOpenAI, message: str) -> dict[str, Any]:
    prompt = (
        "Reply in one short sentence for a classroom API demo.\n\n"
        f"User: {message.strip()}"
    )
    out = llm.invoke(prompt)
    text = out.content if hasattr(out, "content") else str(out)
    return {
        "method": "POST",
        "path": "/teaching/api-basics/llm",
        "status_code": 200,
        "status_meaning": "OK — LLM call completed successfully.",
        "assistant_reply": text,
    }


def persist_user_message(db: Session, content: str, user_email: str) -> dict[str, Any]:
    session_id = f"teaching-api-{uuid.uuid4()}"
    row = create_message(
        db=db,
        session_id=session_id,
        role="user",
        content=content.strip(),
        metadata={"teaching_api_basics": True, "user_email": user_email},
    )
    return {
        "method": "POST",
        "path": "/teaching/api-basics/messages",
        "status_code": 201,
        "status_meaning": "Created — a new resource (message row) was stored.",
        "message_id": row.id,
        "session_id": session_id,
    }


def create_note(content: str) -> Tuple[int, dict[str, Any]]:
    global _next_note_id
    nid = _next_note_id
    _next_note_id += 1
    _notes[nid] = content.strip()
    payload = {
        "method": "POST",
        "path": "/teaching/api-basics/notes",
        "status_code": 201,
        "status_meaning": "Created — server assigned a new id for the resource.",
        "id": nid,
        "content": _notes[nid],
    }
    return nid, payload


def get_note(note_id: int) -> Optional[dict[str, Any]]:
    if note_id not in _notes:
        return None
    return {
        "method": "GET",
        "path": f"/teaching/api-basics/notes/{note_id}",
        "status_code": 200,
        "status_meaning": "OK — representation returned.",
        "id": note_id,
        "content": _notes[note_id],
    }


def update_note(note_id: int, content: str) -> Optional[dict[str, Any]]:
    if note_id not in _notes:
        return None
    _notes[note_id] = content.strip()
    return {
        "method": "PUT",
        "path": f"/teaching/api-basics/notes/{note_id}",
        "status_code": 200,
        "status_meaning": "OK — resource updated.",
        "id": note_id,
        "content": _notes[note_id],
    }


def delete_note(note_id: int) -> bool:
    if note_id not in _notes:
        return False
    del _notes[note_id]
    return True


def reset_notes_for_tests() -> None:
    """Test hook only."""
    global _next_note_id
    _notes.clear()
    _next_note_id = 1
