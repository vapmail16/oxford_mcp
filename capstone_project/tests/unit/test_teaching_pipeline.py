"""
TDD: Teaching pipeline — isolated LLM → DB → backend trace (not production chat/RAG).
"""

import pytest
import uuid
from unittest.mock import MagicMock

from backend.teaching.pipeline import (
    STEP_KEYS,
    run_teaching_pipeline,
)


@pytest.fixture
def mock_teaching_llm():
    """LangChain-style invoke returning object with .content"""
    m = MagicMock()
    msg = MagicMock()
    msg.content = "Teaching demo reply: OK."
    m.invoke.return_value = msg
    return m


@pytest.mark.unit
@pytest.mark.teaching
class TestTeachingPipeline:
    def test_run_returns_run_id_session_id_and_four_steps(self, db_session, mock_teaching_llm):
        result = run_teaching_pipeline(
            message="Hello, explain the pipeline.",
            user_email="teacher@oxforduniversity.com",
            db=db_session,
            llm=mock_teaching_llm,
        )

        assert "run_id" in result
        assert uuid.UUID(result["run_id"])  # valid UUID string
        assert result["session_id"].startswith("teaching-")
        assert result["assistant_response"] == "Teaching demo reply: OK."
        assert len(result["steps"]) == len(STEP_KEYS)
        for key in STEP_KEYS:
            assert any(s["key"] == key for s in result["steps"])

    def test_steps_include_duration_and_detail(self, db_session, mock_teaching_llm):
        result = run_teaching_pipeline(
            message="Test message",
            user_email="a@b.com",
            db=db_session,
            llm=mock_teaching_llm,
        )

        for step in result["steps"]:
            assert step["status"] == "success"
            assert "duration_ms" in step
            assert step["duration_ms"] >= 0
            assert "detail" in step
            assert isinstance(step["detail"], dict)
            assert "label" in step

    def test_backend_step_describes_request(self, db_session, mock_teaching_llm):
        result = run_teaching_pipeline(
            message="Ping",
            user_email="u@oxforduniversity.com",
            db=db_session,
            llm=mock_teaching_llm,
        )
        backend = next(s for s in result["steps"] if s["key"] == "backend_receive")
        assert backend["detail"]["method"] == "POST"
        assert "/teaching/pipeline/trace" in backend["detail"]["path"]

    def test_db_steps_reference_messages_table(self, db_session, mock_teaching_llm):
        result = run_teaching_pipeline(
            message="DB test",
            user_email="db@oxforduniversity.com",
            db=db_session,
            llm=mock_teaching_llm,
        )
        db_user = next(s for s in result["steps"] if s["key"] == "db_user_message")
        db_asst = next(s for s in result["steps"] if s["key"] == "db_assistant_message")
        assert db_user["detail"]["table"] == "messages"
        assert db_user["detail"]["message_id"] is not None
        assert db_asst["detail"]["table"] == "messages"
        assert db_asst["detail"]["message_id"] is not None

    def test_llm_step_shows_prompt_preview_not_full_key(self, db_session, mock_teaching_llm):
        result = run_teaching_pipeline(
            message="Short",
            user_email="x@y.com",
            db=db_session,
            llm=mock_teaching_llm,
        )
        llm_step = next(s for s in result["steps"] if s["key"] == "llm_generate")
        assert "prompt_preview" in llm_step["detail"]
        assert "model" in llm_step["detail"]
        mock_teaching_llm.invoke.assert_called_once()

    def test_empty_message_raises(self, db_session, mock_teaching_llm):
        with pytest.raises(ValueError, match="message"):
            run_teaching_pipeline(
                message="   ",
                user_email="a@b.com",
                db=db_session,
                llm=mock_teaching_llm,
            )
