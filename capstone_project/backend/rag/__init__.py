"""
RAG (Retrieval-Augmented Generation) package for IT Support Agent.

Exports from ``ingest`` are loaded lazily so ``python -m backend.rag.ingest`` does not
trigger runpy's "found in sys.modules" warning.
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
    if name in __all__:
        mod = import_module("backend.rag.ingest")
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
