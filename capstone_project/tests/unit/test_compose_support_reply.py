"""TDD: composed user-facing support text includes actionable steps, not only ticket boilerplate."""

import pytest

pytestmark = pytest.mark.unit


def test_hardware_crash_data_includes_recovery_steps():
    from backend.chat_demo.compose_support_reply import build_support_reply

    text = build_support_reply(
        user_message="my laptop crashed i am worried about the data? what do i do?",
        triage={"category": "HARDWARE", "priority": "MEDIUM"},
        ticket_id=109,
        source_note="test",
    )
    assert "109" in text
    assert "data" in text.lower() or "backup" in text.lower() or "file" in text.lower()
    assert "What to try" in text or "try now" in text.lower()


def test_network_vpn_includes_connectivity_steps():
    from backend.chat_demo.compose_support_reply import build_support_reply

    text = build_support_reply(
        user_message="VPN keeps disconnecting at home",
        triage={"category": "NETWORK", "priority": "MEDIUM"},
        ticket_id=1,
        source_note="test",
    )
    assert "VPN" in text or "network" in text.lower()


def test_password_includes_reset_guidance():
    from backend.chat_demo.compose_support_reply import build_support_reply

    text = build_support_reply(
        user_message="I need to reset my password",
        triage={"category": "PASSWORD", "priority": "MEDIUM"},
        ticket_id=2,
        source_note="test",
    )
    assert "password" in text.lower()


def test_ticket_footer_when_no_id():
    from backend.chat_demo.compose_support_reply import build_support_reply

    text = build_support_reply(
        user_message="help",
        triage={"category": "UNKNOWN", "priority": "LOW"},
        ticket_id=None,
        source_note="test",
    )
    assert "session" in text.lower() or "ticket" in text.lower()


def test_rag_sections_appear_when_kb_and_db_provided():
    from backend.chat_demo.compose_support_reply import build_support_reply

    text = build_support_reply(
        user_message="VPN",
        triage={"category": "NETWORK", "priority": "MEDIUM"},
        ticket_id=1,
        source_note="test",
        rag_kb_text="Step 1: open AnyConnect",
        rag_db_text="ticket_id:3 previous VPN case",
        rag_kb_sources=["vpn_setup_guide.md"],
        rag_db_sources=["db_ticket:ticket_3"],
    )
    assert "markdown RAG" in text or "knowledge base" in text.lower()
    assert "DB RAG" in text or "internal tickets" in text.lower()
    assert "AnyConnect" in text
    assert "Citations (retrieval)" in text
    assert "vpn_setup_guide.md" in text
    assert "db_ticket:ticket_3" in text
