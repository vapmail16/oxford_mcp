"""TDD: canonical Qdrant path resolution."""

import pytest

pytestmark = pytest.mark.unit


class TestGetQdrantPath:
    def test_default_points_under_backend(self, monkeypatch):
        monkeypatch.delenv("QDRANT_PATH", raising=False)
        from backend.rag.config_paths import get_qdrant_path
        from pathlib import Path

        p = Path(get_qdrant_path())
        assert p.name == "qdrant_storage"
        assert p.parent.name == "backend"

    def test_absolute_env_passthrough(self, monkeypatch, tmp_path):
        abs_dir = str(tmp_path / "custom_store")
        monkeypatch.setenv("QDRANT_PATH", abs_dir)
        from backend.rag.config_paths import get_qdrant_path

        assert get_qdrant_path() == abs_dir
