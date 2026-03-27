"""TDD: plain LLM path (no retrieval) for demo track."""

from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

pytestmark = pytest.mark.unit


class TestRunPlainLlm:
    def test_invokes_llm_and_returns_presenter_metadata(self):
        from backend.chat_demo.plain_llm import run_plain_llm, PLAIN_LLM_PRESENTER

        class _Msg:
            def __init__(self, content: str):
                self.content = content

        llm = Mock()
        llm.invoke.return_value = _Msg("Short IT tip: use a password manager.")

        text, presenter = run_plain_llm(llm, "Give one password tip.")

        assert text == "Short IT tip: use a password manager."
        assert presenter == PLAIN_LLM_PRESENTER
        llm.invoke.assert_called_once()
        call_messages = llm.invoke.call_args[0][0]
        assert isinstance(call_messages, list)
        assert len(call_messages) == 2
        assert isinstance(call_messages[0], SystemMessage)
        assert "Acme Corp" in call_messages[0].content
        assert isinstance(call_messages[1], HumanMessage)
        assert "password tip" in call_messages[1].content.lower()

    def test_obvious_non_it_does_not_call_llm(self):
        from backend.chat_demo.plain_llm import run_plain_llm

        llm = Mock()
        text, presenter = run_plain_llm(llm, "what is the capital of france")

        assert "Acme Corp IT" in text
        assert "Guardrail" in presenter.get("note", "")
        llm.invoke.assert_not_called()
