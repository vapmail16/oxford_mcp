"""TDD: IT-scope guardrail heuristics."""

import pytest

pytestmark = pytest.mark.unit


class TestIsClearlyNonIt:
    def test_geography_capital_is_non_it(self):
        from backend.chat_demo.guardrails import is_clearly_non_it

        assert is_clearly_non_it("what is the capital of france") is True

    def test_it_question_with_capital_in_context_stays_on_topic(self):
        """Do not block when IT keywords appear (e.g. 'capital' in a different sense)."""
        from backend.chat_demo.guardrails import is_clearly_non_it

        assert is_clearly_non_it("VPN keeps asking for capital letters in password") is False

    def test_vpn_question_not_blocked(self):
        from backend.chat_demo.guardrails import is_clearly_non_it

        assert is_clearly_non_it("My VPN disconnects every 10 minutes") is False

    def test_short_message_not_flagged(self):
        from backend.chat_demo.guardrails import is_clearly_non_it

        assert is_clearly_non_it("help") is False
