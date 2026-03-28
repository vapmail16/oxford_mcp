"""
DEMO GUARDRAILS
===============
What this module demonstrates:
  - Fast heuristic filtering of obvious non-IT queries.
  - Shared refusal/system text reused by plain/RAG/agentic tracks.
  - Low-cost pre-check before any model or retrieval call.
"""

from __future__ import annotations

import re
from typing import Final

# Strong hints the user is asking about workplace tech (do not treat as trivia).
IT_HINT_RE = re.compile(
    r"\b("
    r"vpn|wi-?fi|password|reset|outlook|email|laptop|windows|macos|"
    r"drive|teams|slack|error|ticket|login|mfa|disk|printer|screen|"
    r"keyboard|software|install|license|dns|ip address|domain|ldap|"
    r"azure|sso|anyconnect|office|excel|on-?prem|"
    r"admin|acct|account|credential|lockout|unlock|chrome|browser|"
    r"hardware|monitor|usb|dock|bitlocker|intune|okta|sso"
    r")\b",
    re.I,
)

_NON_IT_PATTERN_STRS: tuple[str, ...] = (
    r"\bcapital of\b",
    r"\bwho\s+(won|is)\s+(the\s+)?\d{4}\s*(world\s+cup|oscar|superbowl)\b",
    r"\bweather\s+in\b",
    r"\brecipe\s+for\b",
    r"\bwho\s+(is|was)\s+the\s+(president|prime\s+minister)\b",
    r"\btranslate\s+this\b",
)

_NON_IT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.I) for p in _NON_IT_PATTERN_STRS
)

NON_IT_REFUSAL_MESSAGE: Final[str] = """I'm here to help with **Oxford University IT** topics only (VPN, accounts, passwords, email, Wi-Fi, laptops, apps, and corporate systems).

I can't help with general knowledge or trivia. Try asking about something like password reset, VPN connectivity, or Teams issues."""

SYSTEM_IT_SUPPORT_ONLY: Final[str] = """You are the IT support assistant for Oxford University employees. You ONLY help with workplace technology: VPN, accounts, passwords, hardware, software, Wi-Fi, email, corporate apps, and IT policies.

If the user asks something unrelated (general knowledge, trivia, weather, politics, homework, recipes, etc.), politely refuse in two short sentences and mention 2–3 example IT topics you can help with. Do NOT answer the unrelated question."""


def is_clearly_non_it(message: str) -> bool:
    """Heuristic: obvious geography/trivia/etc. with no IT keywords."""
    # Keep very short messages neutral; they are usually greetings or incomplete asks.
    m = message.strip()
    if len(m) < 6:
        return False
    if IT_HINT_RE.search(m):
        return False
    for pat in _NON_IT_PATTERNS:
        if pat.search(m):
            return True
    return False


def non_it_refusal_message() -> str:
    """Return a standard refusal text for non-IT questions."""
    return NON_IT_REFUSAL_MESSAGE
