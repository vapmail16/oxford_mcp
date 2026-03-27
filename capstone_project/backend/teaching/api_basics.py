"""
Teaching-only HTTP / REST examples: GET, POST, PUT, DELETE, status codes.
Separate from production /chat — uses in-memory notes + optional one-row DB write.

Each successful JSON body includes `flow_steps`: deterministic rows for
frontend → middleware → route → service → database → llm.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.teaching.deps import get_teaching_db, get_teaching_llm
from backend.teaching.flow_catalog import (
    flow_db_message,
    flow_echo,
    flow_llm,
    flow_note_delete,
    flow_note_get,
    flow_note_post,
    flow_note_put,
    flow_ping,
    merge_flow,
)
from backend.teaching.services import api_basics_service as svc

api_basics_router = APIRouter(prefix="/api-basics", tags=["teaching-api-basics"])


class EchoBody(BaseModel):
    message: str = Field(..., min_length=1)


class LLMBody(BaseModel):
    message: str = Field(..., min_length=1)


class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1)


class NoteUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class DbMessageBody(BaseModel):
    content: str = Field(..., min_length=1)
    user_email: str = Field(default="demo@acmecorp.com")


@api_basics_router.get("/ping")
def api_basics_ping() -> dict[str, Any]:
    payload = svc.ping_payload()
    return merge_flow(payload, flow_ping())


@api_basics_router.post("/echo")
def api_basics_echo(body: EchoBody) -> dict[str, Any]:
    payload = svc.echo_message(body.message)
    return merge_flow(payload, flow_echo())


@api_basics_router.post("/llm")
def api_basics_llm(
    body: LLMBody,
    llm: ChatOpenAI = Depends(get_teaching_llm),
) -> dict[str, Any]:
    payload = svc.invoke_teaching_llm(llm, body.message)
    return merge_flow(payload, flow_llm())


@api_basics_router.post("/messages", status_code=201)
def api_basics_persist_message(
    body: DbMessageBody,
    db: Session = Depends(get_teaching_db),
) -> dict[str, Any]:
    payload = svc.persist_user_message(db, body.content, body.user_email)
    return merge_flow(payload, flow_db_message())


@api_basics_router.post("/notes", status_code=201)
def api_basics_create_note(body: NoteCreate) -> dict[str, Any]:
    _, payload = svc.create_note(body.content)
    return merge_flow(payload, flow_note_post())


@api_basics_router.get("/notes/{note_id}")
def api_basics_get_note(note_id: int) -> dict[str, Any]:
    row = svc.get_note(note_id)
    if row is None:
        base = {
            "method": "GET",
            "path": f"/teaching/api-basics/notes/{note_id}",
            "status_code": 404,
            "status_meaning": "Not Found — no resource at this URL.",
        }
        raise HTTPException(
            status_code=404,
            detail=merge_flow(base, flow_note_get(found=False, note_id=note_id)),
        )
    return merge_flow(row, flow_note_get(found=True, note_id=note_id))


@api_basics_router.put("/notes/{note_id}")
def api_basics_put_note(note_id: int, body: NoteUpdate) -> dict[str, Any]:
    row = svc.update_note(note_id, body.content)
    if row is None:
        base = {
            "method": "PUT",
            "path": f"/teaching/api-basics/notes/{note_id}",
            "status_code": 404,
            "status_meaning": "Not Found — cannot update a missing resource.",
        }
        raise HTTPException(
            status_code=404,
            detail=merge_flow(base, flow_note_put(found=False, note_id=note_id)),
        )
    return merge_flow(row, flow_note_put(found=True, note_id=note_id))


@api_basics_router.delete("/notes/{note_id}")
def api_basics_delete_note(note_id: int) -> dict[str, Any]:
    """
    DELETE success returns 200 + JSON (not 204) so the UI can show flow_steps.
    Many production APIs use 204 with no body; this route is teaching-first.
    """
    ok = svc.delete_note(note_id)
    if not ok:
        base = {
            "method": "DELETE",
            "path": f"/teaching/api-basics/notes/{note_id}",
            "status_code": 404,
            "status_meaning": "Not Found — nothing to delete.",
        }
        raise HTTPException(
            status_code=404,
            detail=merge_flow(base, flow_note_delete(found=False, note_id=note_id)),
        )
    payload = {
        "method": "DELETE",
        "path": f"/teaching/api-basics/notes/{note_id}",
        "status_code": 200,
        "status_meaning": "OK — deleted. (RFC often uses 204 with no body; 200 here carries JSON for teaching.)",
        "deleted": True,
    }
    return merge_flow(payload, flow_note_delete(found=True, note_id=note_id))
