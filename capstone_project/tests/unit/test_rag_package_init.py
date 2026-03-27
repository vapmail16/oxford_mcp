"""TDD: backend.rag package lazy exports (CLI runpy + public API)."""

import pytest

pytestmark = pytest.mark.unit


def test_lazy_export_ingest_documents():
    import backend.rag as rag

    assert "ingest_documents" not in rag.__dict__
    fn = rag.ingest_documents
    assert callable(fn)
    assert fn.__module__ == "backend.rag.ingest"


def test_importing_submodule_directly_still_works():
    from backend.rag.ingest import load_documents

    assert callable(load_documents)
