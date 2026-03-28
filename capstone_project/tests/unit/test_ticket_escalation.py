"""Unit tests for KB-miss ticket escalation heuristics."""

import pytest

pytestmark = pytest.mark.unit


class TestShouldEscalate:
    def test_urgent_and_issue(self):
        from backend.chat_demo.ticket_escalation import should_escalate_to_ticket

        assert should_escalate_to_ticket(
            "i have issue with my system its very urgent what do i do"
        )

    def test_explicit_ticket_phrase(self):
        from backend.chat_demo.ticket_escalation import should_escalate_to_ticket

        assert should_escalate_to_ticket("please open a ticket for my laptop screen flicker")

    def test_too_short(self):
        from backend.chat_demo.ticket_escalation import should_escalate_to_ticket

        assert not should_escalate_to_ticket("help")

    def test_wifi_slow_alone_not_escalated(self):
        from backend.chat_demo.ticket_escalation import should_escalate_to_ticket

        assert not should_escalate_to_ticket("WiFi slow")


class TestInferPriority:
    def test_critical(self):
        from backend.chat_demo.ticket_escalation import infer_priority

        assert infer_priority("EMERGENCY entire network is down") == "CRITICAL"

    def test_high(self):
        from backend.chat_demo.ticket_escalation import infer_priority

        assert infer_priority("this is very urgent please help") == "HIGH"

    def test_medium_default(self):
        from backend.chat_demo.ticket_escalation import infer_priority

        assert infer_priority("open a ticket for a minor question") == "MEDIUM"


class TestInferCategory:
    def test_network(self):
        from backend.chat_demo.ticket_escalation import infer_category

        assert infer_category("VPN will not connect") == "NETWORK"


class TestTryCreateTicketIntegration:
    def test_creates_sqlite_ticket(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from backend.database.models import Base
        from backend.chat_demo.ticket_escalation import try_create_ticket_from_escalation

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        out = try_create_ticket_from_escalation(
            db,
            message="i have urgent issue with my system it is not working",
            user_email="demo@oxforduniversity.com",
            session_id="sess-int-1",
        )
        assert out is not None
        tid, priority, category, reply = out
        assert tid >= 1
        assert priority in ("HIGH", "CRITICAL", "MEDIUM")
        assert category in ("UNKNOWN", "NETWORK", "HARDWARE", "SOFTWARE", "ACCESS")
        assert str(tid) in reply
        assert "demo@oxforduniversity.com" in reply
