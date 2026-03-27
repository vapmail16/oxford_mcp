"""TDD: rule-based fallback when KB/RAG has no hit (`generate_simple_response`)."""

import pytest

pytestmark = pytest.mark.unit


class TestGenerateSimpleResponseVpn:
    def test_vpn_setup_question_returns_steps_not_generic_greeting(self):
        from backend.main import generate_simple_response

        text = generate_simple_response(
            "ok then can you tell me steps to set up vpn"
        )
        assert "AnyConnect" in text or "VPN" in text
        assert "Could you please describe your issue in more detail?" not in text

    def test_vpn_422_still_returns_dedicated_422_guidance(self):
        from backend.main import generate_simple_response

        text = generate_simple_response("vpn error 422 when connecting")
        assert "422" in text
        assert "authentication timeout" in text.lower() or "MFA" in text
