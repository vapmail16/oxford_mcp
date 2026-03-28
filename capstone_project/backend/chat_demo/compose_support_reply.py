"""
COMPOSE SUPPORT REPLY
=====================
What this module demonstrates:
  - Deterministic reply assembly for the MCP compose step.
  - Category-aware "what to try now" bullets.
  - Optional KB/DB retrieval snippets and source citations.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _coerce_ticket_id(tid: Any) -> Optional[int]:
    """Accept int-like values from MCP payloads and normalize to Optional[int]."""
    if tid is None:
        return None
    if isinstance(tid, bool):
        return None
    if isinstance(tid, int):
        return tid
    if isinstance(tid, float) and tid == int(round(tid)):
        return int(round(tid))
    if isinstance(tid, str) and tid.strip().isdigit():
        return int(tid.strip())
    return None


def _bullets_hardware(msg: str) -> List[str]:
    m = msg.lower()
    out: List[str] = []
    if any(
        w in m
        for w in (
            "crash",
            "crashed",
            "data",
            "lost",
            "disk",
            "drive",
            "won't boot",
            "wont boot",
            "dead",
            "blue screen",
            "bsod",
        )
    ):
        out.extend(
            [
                "If it will not boot: stop repeated power cycles; unplug power, hold the power button 10s, then restart with the charger connected.",
                "If it boots even once: copy important files to **OneDrive** or a network share **before** running disk repair or reinstalls.",
                "Avoid saving new large files to the machine if you suspect disk failure—ask IT for imaging/recovery options.",
            ]
        )
    if any(w in m for w in ("screen", "display", "flicker", "black")):
        out.append(
            "External monitor test: if the lid is black but an external display works, note that for IT (possible panel or cable)."
        )
    if not out:
        out.append(
            "Try a full shutdown (not just sleep), then power on with AC power connected."
        )
        out.append(
            "Run any built-in hardware diagnostics from the vendor (e.g. startup diagnostics) and note error codes for IT."
        )
    return out[:5]


def _bullets_network(msg: str) -> List[str]:
    m = msg.lower()
    out: List[str] = []
    if "vpn" in m:
        out.extend(
            [
                "Quit the VPN client completely, wait 30 seconds, reopen, and reconnect (watch for MFA prompts).",
                "If unstable on Wi‑Fi, try wired Ethernet once to rule out wireless issues.",
            ]
        )
    if "wifi" in m or "wi-fi" in m or "wireless" in m:
        out.append(
            "Forget and rejoin the corporate SSID, or run the OS network troubleshooter."
        )
    if not out:
        out.extend(
            [
                "Check physical connections and reboot the modem/router if on site.",
                "Confirm whether colleagues have the same outage (helps narrow service vs device).",
            ]
        )
    return out[:5]


def _bullets_password(_msg: str) -> List[str]:
    return [
        "Use the self-service password portal if your org has one; complete MFA within the time limit.",
        "If locked out after failed attempts, wait for the lockout window or contact the service desk with your verified work email.",
    ]


def _bullets_software(msg: str) -> List[str]:
    return [
        "Note the exact app name and version; try a full quit and relaunch first.",
        "Check for pending OS or app updates; install during a maintenance window if policy allows.",
        "If the app crashes on open, capture a screenshot of the error text for IT (ticket already references your report).",
    ][:4]


def _bullets_access(_msg: str) -> List[str]:
    return [
        "Confirm which folder, app, or system you need access to and your business reason.",
        "Your manager or resource owner may need to approve—mention them in the ticket thread if asked.",
    ]


def _bullets_unknown(_msg: str) -> List[str]:
    return [
        "Reply with any error codes, screenshots, or “what changed” since it last worked.",
        "If this blocks work, say so in the ticket—priority can be adjusted by the service desk.",
    ]


def _truncate_block(text: str, limit: int = 1400) -> str:
    """Clamp long retrieval excerpts so responses stay readable."""
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 3] + "..."


def _normalize_source_list(raw: Any, max_items: int = 16) -> List[str]:
    """Convert unknown source payloads into a clean string list."""
    if raw is None:
        return []
    if isinstance(raw, list):
        out = [str(x).strip() for x in raw if str(x).strip()]
        return out[:max_items]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()[:200]]
    return []


def coerce_rag_source_arg(raw: Any, max_items: int = 32) -> List[str]:
    """Normalize MCP params (list or JSON array string) to citation labels."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return _normalize_source_list(raw, max_items)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return _normalize_source_list(parsed, max_items)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def format_rag_citations(
    kb_sources: Optional[List[str]] = None,
    db_sources: Optional[List[str]] = None,
    *,
    max_each: int = 12,
) -> str:
    """One or two lines naming retrieved KB docs and DB ticket/message ids."""
    kb = _normalize_source_list(kb_sources, max_each)
    db = _normalize_source_list(db_sources, max_each)
    if not kb and not db:
        return ""
    parts: List[str] = []
    if kb:
        parts.append("**Knowledge base:** " + ", ".join(kb))
    if db:
        parts.append("**Internal records:** " + ", ".join(db))
    return "\n".join(parts)


def build_support_reply(
    *,
    user_message: str,
    triage: Optional[Dict[str, Any]],
    ticket_id: Optional[int],
    source_note: str,
    rag_kb_text: str = "",
    rag_db_text: str = "",
    rag_kb_sources: Optional[List[str]] = None,
    rag_db_sources: Optional[List[str]] = None,
) -> str:
    """
    Full markdown-style reply body for the compose step.

    source_note: e.g. "MCP TS server" or "simulated MCP" for the triage line only.
    """
    # Step 1: normalize key inputs used by every response branch.
    triage = triage or {}
    cat = str(triage.get("category") or "UNKNOWN").upper()
    msg = user_message or ""
    tid = _coerce_ticket_id(ticket_id)

    lines: List[str] = [
        f"**Triage:** category **{cat}** ({source_note}).",
    ]

    # Step 2: include retrieval excerpts (if present) before recommendations.
    kb = (rag_kb_text or "").strip()
    db = (rag_db_text or "").strip()
    if kb:
        lines.append("")
        lines.append("**From knowledge base (markdown RAG):**")
        lines.append(_truncate_block(kb))
    if db:
        lines.append("")
        lines.append("**From internal tickets / messages (DB RAG):**")
        lines.append(_truncate_block(db))

    # Step 3: append compact citation labels for transparency.
    cite = format_rag_citations(rag_kb_sources, rag_db_sources)
    if cite:
        lines.append("")
        lines.append("**Citations (retrieval):**")
        lines.append(cite)

    # Step 4: choose actionable bullets based on triage category.
    if cat == "HARDWARE":
        bullets = _bullets_hardware(msg)
    elif cat == "NETWORK":
        bullets = _bullets_network(msg)
    elif cat == "PASSWORD":
        bullets = _bullets_password(msg)
    elif cat == "SOFTWARE":
        bullets = _bullets_software(msg)
    elif cat == "ACCESS":
        bullets = _bullets_access(msg)
    else:
        bullets = _bullets_unknown(msg)

    # Step 5: include ticket status and the next communication instruction.
    lines.append("")
    lines.append("**What to try now:**")
    for b in bullets:
        lines.append(f"- {b}")

    lines.append("")
    if tid is not None:
        lines.append(
            f"**Ticket #{tid}** is logged so IT can follow up or escalate if needed."
        )
    else:
        lines.append(
            "**Note:** No ticket id in this session—describe your issue again when contacting the service desk."
        )

    lines.append(
        "You can reply in this chat with updates (error codes, screenshots) to attach context to your request."
    )

    return "\n".join(lines)
