"""TDD: demo track resolution for main /chat (Oxford menu + explicit tracks)."""

import pytest

pytestmark = pytest.mark.unit


class TestNormalizeDemoTrack:
    def test_accepts_plain_llm(self):
        from backend.chat_demo.tracks import normalize_demo_track

        assert normalize_demo_track("plain_llm") == "plain_llm"

    def test_accepts_rag_kb_aliases(self):
        from backend.chat_demo.tracks import normalize_demo_track

        assert normalize_demo_track("rag_kb") == "rag_kb"
        assert normalize_demo_track("RAG_KB") == "rag_kb"

    def test_accepts_agentic_mcp(self):
        from backend.chat_demo.tracks import normalize_demo_track

        assert normalize_demo_track("agentic_mcp") == "agentic_mcp"

    def test_accepts_rag_db_and_structured_alias(self):
        from backend.chat_demo.tracks import normalize_demo_track

        assert normalize_demo_track("rag_db") == "rag_db"
        assert normalize_demo_track("rag_structured") == "rag_db"

    def test_accepts_menu(self):
        from backend.chat_demo.tracks import normalize_demo_track

        assert normalize_demo_track("menu") == "menu"

    def test_unknown_returns_none(self):
        from backend.chat_demo.tracks import normalize_demo_track

        assert normalize_demo_track("structured_rag") is None
        assert normalize_demo_track("") is None


class TestResolveEffectiveTrack:
    def test_demo_track_field_wins_over_message(self):
        from backend.chat_demo.tracks import resolve_effective_track

        assert (
            resolve_effective_track(
                message="__DEMO__:menu",
                demo_track_field="plain_llm",
                demo_mode=True,
            )
            == "plain_llm"
        )

    def test_prefix_in_message_when_no_field(self):
        from backend.chat_demo.tracks import resolve_effective_track

        assert (
            resolve_effective_track(
                message="__DEMO__:rag_kb VPN issue",
                demo_track_field=None,
                demo_mode=True,
            )
            == "rag_kb"
        )

    def test_short_greeting_with_demo_mode_returns_menu(self):
        from backend.chat_demo.tracks import resolve_effective_track

        assert (
            resolve_effective_track(message="Hi", demo_track_field=None, demo_mode=True)
            == "menu"
        )
        assert (
            resolve_effective_track(
                message="hello there", demo_track_field=None, demo_mode=True
            )
            == "menu"
        )

    def test_greeting_ignored_when_demo_mode_false(self):
        from backend.chat_demo.tracks import resolve_effective_track

        assert (
            resolve_effective_track(message="Hi", demo_track_field=None, demo_mode=False)
            is None
        )

    def test_normal_question_returns_none_for_legacy_path(self):
        from backend.chat_demo.tracks import resolve_effective_track

        assert (
            resolve_effective_track(
                message="My VPN is broken",
                demo_track_field=None,
                demo_mode=True,
            )
            is None
        )
