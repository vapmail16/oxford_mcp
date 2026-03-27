"""Teaching API basics — HTTP verbs and status codes (isolated routes)."""

import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException

from backend.teaching.services import api_basics_service as svc


@pytest.fixture(autouse=True)
def reset_teaching_notes():
    svc.reset_notes_for_tests()
    yield
    svc.reset_notes_for_tests()


@pytest.mark.unit
@pytest.mark.teaching
class TestTeachingApiBasics:
    def test_get_ping_returns_200_and_flow_steps(self):
        from backend.teaching.api_basics import api_basics_ping

        out = api_basics_ping()
        assert out["status_code"] == 200
        assert out["method"] == "GET"
        assert "flow_steps" in out
        assert len(out["flow_steps"]) == 6
        assert out["flow_steps"][0]["layer"] == "frontend"

    def test_post_echo_returns_200(self):
        from backend.teaching.api_basics import EchoBody, api_basics_echo

        out = api_basics_echo(EchoBody(message="hello"))
        assert out["status_code"] == 200
        assert out["echo"] == "hello"
        assert "flow_steps" in out

    def test_post_llm_returns_200(self):
        from backend.teaching.api_basics import LLMBody, api_basics_llm

        llm = MagicMock()
        msg = MagicMock()
        msg.content = "Reply text"
        llm.invoke.return_value = msg

        out = api_basics_llm(LLMBody(message="hi"), llm=llm)
        assert out["status_code"] == 200
        assert out["assistant_reply"] == "Reply text"
        assert "flow_steps" in out

    def test_post_messages_returns_201(self, db_session):
        from backend.teaching.api_basics import DbMessageBody, api_basics_persist_message

        out = api_basics_persist_message(
            DbMessageBody(content="stored once", user_email="t@test.com"),
            db=db_session,
        )
        assert out["status_code"] == 201
        assert out["message_id"] is not None
        assert "flow_steps" in out

    def test_notes_crud_status_codes(self):
        from backend.teaching.api_basics import (
            NoteCreate,
            NoteUpdate,
            api_basics_create_note,
            api_basics_delete_note,
            api_basics_get_note,
            api_basics_put_note,
        )

        created = api_basics_create_note(NoteCreate(content="alpha"))
        assert created["status_code"] == 201
        nid = created["id"]

        got = api_basics_get_note(nid)
        assert got["status_code"] == 200

        updated = api_basics_put_note(nid, NoteUpdate(content="beta"))
        assert updated["status_code"] == 200
        assert updated["content"] == "beta"

        res = api_basics_delete_note(nid)
        assert res["status_code"] == 200
        assert res["deleted"] is True
        assert "flow_steps" in res

        with pytest.raises(HTTPException) as ei:
            api_basics_get_note(nid)
        assert ei.value.status_code == 404
        assert "flow_steps" in ei.value.detail
