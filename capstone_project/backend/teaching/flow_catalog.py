"""
Deterministic teaching copy for frontend → middleware → route → service → DB/LLM.
Same vocabulary for every operation so the UI can render rows consistently.
"""

from __future__ import annotations

from typing import Any, List

# Canonical layer ids (match frontend CSS)
LAYERS = ("frontend", "middleware", "route", "service", "database", "llm")


def _step(
    layer: str,
    title: str,
    summary: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "layer": layer,
        "title": title,
        "summary": summary,
        "detail": detail,
    }


def flow_ping() -> List[dict[str, Any]]:
    return [
        _step(
            "frontend",
            "Browser sends HTTP GET",
            "Axios GET to the teaching base URL.",
            "GET /teaching/api-basics/ping — no request body.",
        ),
        _step(
            "middleware",
            "Request passes ASGI stack",
            "Starlette → FastAPI; CORS middleware may add headers for localhost origins.",
            "Order: ASGI app → CORSMiddleware → FastAPI routing.",
        ),
        _step(
            "route",
            "Route handler is selected",
            "FastAPI matches path prefix /teaching and route GET /api-basics/ping.",
            "Handler: api_basics_ping() in backend/teaching/api_basics.py.",
        ),
        _step(
            "service",
            "Teaching service builds response",
            "api_basics_service.ping_payload() returns JSON fields (status meaning, path).",
            "No side effects — pure in-memory dict.",
        ),
        _step(
            "database",
            "No database access",
            "This path does not open a SQLAlchemy session or touch SQLite.",
            "Deterministic: DB layer is skipped for ping.",
        ),
        _step(
            "llm",
            "No LLM call",
            "No LangChain / OpenAI on this route.",
            "Deterministic: LLM layer is skipped.",
        ),
    ]


def flow_echo() -> List[dict[str, Any]]:
    return [
        _step(
            "frontend",
            "Browser sends HTTP POST + JSON body",
            "POST with { message: string }.",
            "Content-Type: application/json.",
        ),
        _step(
            "middleware",
            "Body parsed & validated",
            "FastAPI + Pydantic validate EchoBody before the route runs.",
            "Invalid body → 422 before your handler.",
        ),
        _step(
            "route",
            "Route handler: POST /api-basics/echo",
            "api_basics_echo(body: EchoBody) receives validated model.",
            "File: api_basics.py.",
        ),
        _step(
            "service",
            "Echo service",
            "api_basics_service.echo_message() returns trimmed string for response.",
            "Still no DB — deterministic echo only.",
        ),
        _step(
            "database",
            "No database access",
            "Echo does not call SessionLocal or create_message.",
            "SQLite not touched.",
        ),
        _step(
            "llm",
            "No LLM call",
            "Echo does not invoke ChatOpenAI.",
            "LLM layer skipped.",
        ),
    ]


def flow_llm() -> List[dict[str, Any]]:
    return [
        _step(
            "frontend",
            "Browser sends POST with user text",
            "POST /teaching/api-basics/llm with { message }.",
            "Same axios client as other teaching calls.",
        ),
        _step(
            "middleware",
            "Validation then dependency injection",
            "Pydantic validates LLMBody; Depends(get_teaching_llm) builds ChatOpenAI.",
            "API key from environment (OPENAI_API_KEY).",
        ),
        _step(
            "route",
            "Route handler: api_basics_llm",
            "Assembles prompt string and calls llm.invoke(prompt).",
            "Handler in api_basics.py.",
        ),
        _step(
            "service",
            "LLM helper (optional thin wrapper)",
            "teaching.services.api_basics_service.invoke_teaching_llm(llm, message).",
            "Keeps route thin — same pattern as larger apps.",
        ),
        _step(
            "database",
            "No database access",
            "This handler does not use SessionLocal.",
            "No rows written for LLM-only demo.",
        ),
        _step(
            "llm",
            "OpenAI completion",
            "LangChain ChatOpenAI.invoke → model returns assistant_reply text.",
            "Model name from OPENAI_MODEL (default gpt-4o-mini).",
        ),
    ]


def flow_db_message() -> List[dict[str, Any]]:
    return [
        _step(
            "frontend",
            "POST with content + user_email",
            "POST /teaching/api-basics/messages.",
            "Body describes one chat row to store.",
        ),
        _step(
            "middleware",
            "Depends(get_teaching_db)",
            "FastAPI opens a SQLAlchemy session per request (generator dependency).",
            "Session closed in finally after handler returns.",
        ),
        _step(
            "route",
            "Route handler: api_basics_persist_message",
            "Calls create_message(...) with role=user and teaching metadata.",
            "api_basics.py.",
        ),
        _step(
            "service",
            "Persistence service",
            "api_basics_service.persist_user_message(db, ...) wraps crud.create_message.",
            "Single INSERT — one deterministic path.",
        ),
        _step(
            "database",
            "SQLite INSERT into messages",
            "SQLAlchemy ORM → messages table; session_id prefixed teaching-api-…",
            "Returns 201 Created with message_id.",
        ),
        _step(
            "llm",
            "No LLM call",
            "This route only persists; does not call the model.",
            "LLM skipped.",
        ),
    ]


def flow_note_post() -> List[dict[str, Any]]:
    return [
        _step(
            "frontend",
            "POST new note content",
            "POST /teaching/api-basics/notes.",
            "JSON body { content }.",
        ),
        _step(
            "middleware",
            "Request validation",
            "NoteCreate validated; then route runs.",
            "Same middleware stack as other routes.",
        ),
        _step(
            "route",
            "Route handler: api_basics_create_note",
            "Delegates to service and returns 201 + id.",
            "api_basics.py.",
        ),
        _step(
            "service",
            "In-memory note service",
            "api_basics_service.create_note() assigns monotonic id, stores in dict.",
            "Not SQLite — so PUT/GET/DELETE demos stay self-contained.",
        ),
        _step(
            "database",
            "No SQLite for notes",
            "Teaching notes live in process memory (dict), not messages table.",
            "Use POST /messages for real DB demo.",
        ),
        _step(
            "llm",
            "No LLM call",
            "Notes CRUD does not touch OpenAI.",
            "LLM skipped.",
        ),
    ]


def flow_note_get(*, found: bool, note_id: int) -> List[dict[str, Any]]:
    if found:
        return [
            _step(
                "frontend",
                "GET by id",
                f"GET /teaching/api-basics/notes/{note_id}.",
                "Browser requests one resource representation.",
            ),
            _step(
                "middleware",
                "Path parameter coercion",
                f"note_id={note_id} parsed as int from URL path.",
                "FastAPI validates type before handler.",
            ),
            _step(
                "route",
                "Route handler: api_basics_get_note",
                "Looks up id in in-memory store; returns 200 + JSON.",
                "api_basics.py.",
            ),
            _step(
                "service",
                "Note read service",
                "api_basics_service.get_note(note_id) reads dict _notes.",
                "Deterministic read.",
            ),
            _step(
                "database",
                "No SQLite for notes",
                "In-memory dict only for this CRUD strip.",
                "Not the messages table.",
            ),
            _step(
                "llm",
                "No LLM call",
                "GET is read-only.",
                "LLM skipped.",
            ),
        ]
    return flow_not_found(
        http_method="GET", note_id=note_id, path=f"/teaching/api-basics/notes/{note_id}"
    )


def flow_note_put(*, found: bool, note_id: int) -> List[dict[str, Any]]:
    if found:
        return [
            _step(
                "frontend",
                "PUT with new content",
                f"PUT /teaching/api-basics/notes/{note_id}.",
                "JSON body { content } — idempotent update of this resource.",
            ),
            _step(
                "middleware",
                "Validation",
                "NoteUpdate body validated.",
                "Then route executes.",
            ),
            _step(
                "route",
                "Route handler: api_basics_put_note",
                "If id exists: overwrite in dict; return 200.",
                "api_basics.py.",
            ),
            _step(
                "service",
                "Note update service",
                "api_basics_service.update_note(note_id, content).",
                "In-memory dict mutation.",
            ),
            _step(
                "database",
                "No SQLite for notes",
                "Still process-local dict.",
                "Not messages table.",
            ),
            _step(
                "llm",
                "No LLM call",
                "PUT does not invoke the model.",
                "LLM skipped.",
            ),
        ]
    return flow_not_found(http_method="PUT", note_id=note_id, path=f"/teaching/api-basics/notes/{note_id}")


def flow_not_found(*, http_method: str, note_id: int, path: str) -> List[dict[str, Any]]:
    """Generic 404 flow for note id misses (GET/PUT/DELETE)."""
    return [
        _step(
            "frontend",
            f"{http_method} targets a resource id",
            f"{http_method} {path}.",
            "The URL identifies one resource; missing id yields 404.",
        ),
        _step(
            "middleware",
            "Request reaches application",
            "Path and method are valid; failure is not a network error.",
            "Starlette/FastAPI still run middleware.",
        ),
        _step(
            "route",
            "Handler checks store / service result",
            "Route calls service; empty result → HTTPException(404).",
            "Deterministic application-level 404.",
        ),
        _step(
            "service",
            "Lookup or mutation finds nothing",
            "api_basics_service returns None/False for unknown id.",
            "No exception in service — route maps to HTTP error.",
        ),
        _step(
            "database",
            "No SQL error here",
            "404 is ‘not found’ semantics for this teaching store.",
            "SQLite was not queried for in-memory notes.",
        ),
        _step(
            "llm",
            "No LLM call",
            "Error responses do not invoke the model.",
            "—",
        ),
    ]


def flow_note_delete(*, found: bool, note_id: int) -> List[dict[str, Any]]:
    if found:
        return [
            _step(
                "frontend",
                "DELETE request",
                f"DELETE /teaching/api-basics/notes/{note_id}.",
                "Often no body; success returns 204 No Content.",
            ),
            _step(
                "middleware",
                "Method routed to DELETE handler",
                "FastAPI dispatches to delete_note.",
                "CORS may apply to DELETE.",
            ),
            _step(
                "route",
                "Route handler: api_basics_delete_note",
                "Removes key from dict; returns JSON (200) so flow_steps can be shown.",
                "RFC often uses 204 No Content; teaching uses 200 + body for the lab UI.",
            ),
            _step(
                "service",
                "Delete service",
                "api_basics_service.delete_note(note_id).",
                "dict.pop / del.",
            ),
            _step(
                "database",
                "No SQLite for notes",
                "In-memory only.",
                "Success: resource removed from dict.",
            ),
            _step(
                "llm",
                "No LLM call",
                "DELETE does not invoke OpenAI.",
                "LLM skipped.",
            ),
        ]
    return flow_not_found(http_method="DELETE", note_id=note_id, path=f"/teaching/api-basics/notes/{note_id}")


def merge_flow(payload: dict[str, Any], flow_steps: List[dict[str, Any]]) -> dict[str, Any]:
    """Attach deterministic flow to a JSON-serializable response dict."""
    out = dict(payload)
    out["flow_steps"] = flow_steps
    return out
