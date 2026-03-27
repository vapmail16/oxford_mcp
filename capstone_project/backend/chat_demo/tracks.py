"""Resolve which demo track applies (explicit field, __DEMO__: prefix, or greeting + demo_mode)."""

from __future__ import annotations

from typing import Optional

DEMO_PREFIX = "__DEMO__:"

_VALID = frozenset({"plain_llm", "rag_kb", "rag_db", "agentic_mcp", "menu"})
# Plan / API alias: structured DB RAG
_TRACK_ALIASES = {"rag_structured": "rag_db"}

_GREETING_WORDS = frozenset({"hi", "hello", "hey", "hiya"})


def normalize_demo_track(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    s = raw.strip().lower()
    if not s:
        return None
    if s in _TRACK_ALIASES:
        return _TRACK_ALIASES[s]
    if s in _VALID:
        return s
    return None


def _is_short_greeting(message: str) -> bool:
    t = message.strip().lower()
    if not t or len(t) > 50:
        return False
    parts = t.split()
    if not parts:
        return False
    return parts[0] in _GREETING_WORDS


def _track_from_message_prefix(message: str) -> Optional[str]:
    s = message.strip()
    if not s.startswith(DEMO_PREFIX):
        return None
    rest = s[len(DEMO_PREFIX) :].strip()
    if not rest:
        return None
    token = rest.split()[0]
    return normalize_demo_track(token)


def resolve_effective_track(
    *,
    message: str,
    demo_track_field: Optional[str],
    demo_mode: bool,
) -> Optional[str]:
    from_field = normalize_demo_track(demo_track_field)
    if from_field is not None:
        return from_field

    from_prefix = _track_from_message_prefix(message)
    if from_prefix is not None:
        return from_prefix

    if demo_mode and _is_short_greeting(message):
        return "menu"

    return None
