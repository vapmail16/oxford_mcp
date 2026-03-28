"""
RAG PACKAGE EXPORTS
===================
This package re-exports ingestion helpers with lazy loading.

Why lazy loading here:
  - Keeps import side effects minimal.
  - Avoids runpy warnings when running ``python -m backend.rag.ingest``.
  - Preserves a simple import surface for callers/tests.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "load_documents",
    "chunk_documents",
    "get_embeddings",
    "create_vector_store",
    "reset_vector_store",
    "ingest_documents",
]


def __getattr__(name: str) -> Any:
    """Lazily forward selected symbols to backend.rag.ingest."""
    if name in __all__:
        mod = import_module("backend.rag.ingest")
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
