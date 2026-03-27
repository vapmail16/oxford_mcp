"""
API tests: POST /teaching/pipeline/trace — teaching-only route.

Invokes the FastAPI handler directly (avoids httpx/ASGI transport version quirks);
HTTP contract is identical to mounted route on app.
"""

import pytest
from unittest.mock import MagicMock
from pydantic import ValidationError


@pytest.mark.api
@pytest.mark.teaching
class TestTeachingTraceEndpoint:
    @pytest.fixture
    def mock_teaching_llm(self):
        m = MagicMock()
        msg = MagicMock()
        msg.content = "API trace reply."
        m.invoke.return_value = msg
        return m

    def test_trace_returns_steps_via_handler(self, db_session, mock_teaching_llm):
        from backend.teaching.router import TeachingTraceRequest, post_teaching_trace

        body = TeachingTraceRequest(message="Hello teaching API", user_email="api@test.com")
        out = post_teaching_trace(body=body, db=db_session, llm=mock_teaching_llm)
        assert len(out["steps"]) >= 4
        assert out["assistant_response"] == "API trace reply."

    def test_trace_empty_message_validation(self):
        from backend.teaching.router import TeachingTraceRequest

        with pytest.raises(ValidationError):
            TeachingTraceRequest(message="  ", user_email="api@test.com")
