"""
TICKET ESCALATION HEURISTICS
============================
What this module demonstrates:
  - Simple rules for deciding when to open a real support ticket.
  - Priority/category inference from user wording.
  - SQLite ticket creation plus a user-facing confirmation message.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from backend.database.crud import create_ticket


def should_escalate_to_ticket(message: str) -> bool:
    """
    True when the user likely needs a tracked ticket (urgency, failure, or explicit ask).
    Kept conservative so short chit-chat does not spam tickets.
    """
    # Normalize once so all keyword checks behave consistently.
    m = message.lower().strip()
    if len(m) < 12:
        return False

    ticket_phrase = any(
        p in m
        for p in (
            "create a ticket",
            "open a ticket",
            "file a ticket",
            "log a ticket",
            "raise a ticket",
        )
    )
    if ticket_phrase:
        return True

    urgent = any(
        w in m
        for w in (
            "urgent",
            "emergency",
            "critical",
            "asap",
            "immediately",
            "severe",
            "very urgent",
        )
    )
    problem = any(
        w in m
        for w in (
            "issue",
            "problem",
            "broken",
            "not working",
            "doesn't work",
            "doesnt work",
            "cannot",
            "can't",
            "down",
            "failed",
            "error",
            "crash",
        )
    )
    if urgent and problem:
        return True
    if urgent and len(m) > 28:
        return True
    if problem and len(m) > 45:
        return True
    return False


def infer_priority(message: str) -> str:
    """Map urgency language to a support priority band."""
    m = message.lower()
    if any(
        w in m
        for w in ("emergency", "critical", "system down", "entire company", "data loss")
    ):
        return "CRITICAL"
    if any(w in m for w in ("urgent", "asap", "immediately", "severe", "very urgent")):
        return "HIGH"
    return "MEDIUM"


def infer_category(message: str) -> str:
    """Map issue keywords to coarse IT categories used in ticket rows."""
    m = message.lower()
    if any(w in m for w in ("vpn", "network", "wifi", "wi-fi", "connection")):
        return "NETWORK"
    if any(w in m for w in ("password", "login", "mfa", "access", "permission")):
        return "ACCESS"
    if any(w in m for w in ("install", "software", "app ", "application")):
        return "SOFTWARE"
    if any(w in m for w in ("laptop", "hardware", "monitor", "keyboard", "screen")):
        return "HARDWARE"
    return "UNKNOWN"


def _title_from_message(message: str) -> str:
    """Turn free text into a short single-line ticket title."""
    one_line = re.sub(r"\s+", " ", message.strip())
    if len(one_line) <= 90:
        return one_line
    return one_line[:87] + "..."


def try_create_ticket_from_escalation(
    db: "Session",
    *,
    message: str,
    user_email: str,
    session_id: Optional[str],
) -> Optional[Tuple[int, str, str, str]]:
    """
    If escalation applies, create ticket and return
    (ticket_id, priority, category, user_facing_reply).

    Otherwise return None.
    """
    # Step 1: decide whether this message should become a tracked incident.
    if not should_escalate_to_ticket(message):
        return None

    # Step 2: infer ticket metadata from the message.
    priority = infer_priority(message)
    category = infer_category(message)
    title = _title_from_message(message)

    # Step 3: persist ticket to SQLite.
    ticket = create_ticket(
        db=db,
        title=title,
        description=message.strip(),
        priority=priority,
        category=category,
        user_email=user_email,
        session_id=session_id,
    )

    # Step 4: return a markdown response shown directly to the user.
    reply = f"""### Ticket opened

**Ticket #{ticket.id}** — priority **{priority}**, category **{category}**.

I've logged your request in our queue. A technician will follow up using the email on file.

**Notification (demo):** a confirmation would be sent to `{user_email}` — in this environment no real email is delivered.

**What happens next:** triage → assignment → updates on this ticket. If this is life-safety or total outage, call the IT hotline as well."""

    return (ticket.id, priority, category, reply)
