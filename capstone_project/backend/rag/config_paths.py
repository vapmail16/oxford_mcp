"""
Canonical filesystem paths for RAG (embedding store, etc.).

Relative `QDRANT_PATH` values resolve under `backend/` so ingestion and retrieval
match whether uvicorn is started from `capstone_project/` or `backend/`.
"""

from __future__ import annotations

import os
from pathlib import Path

# backend/ directory (parent of package `rag/`)
_BACKEND_DIR = Path(__file__).resolve().parent.parent


def get_qdrant_path() -> str:
    """
    Disk path for the Qdrant KB store (`it_support_kb` collection).

    If `QDRANT_PATH` is unset, defaults to ``backend/qdrant_storage``.

    If set to a relative path (e.g. ``./qdrant_storage`` or ``qdrant_storage``),
    it is resolved under ``backend/``, not the process cwd.
    """
    raw = os.getenv("QDRANT_PATH")
    if not raw:
        return str(_BACKEND_DIR / "qdrant_storage")
    p = Path(raw)
    if p.is_absolute():
        return str(p)
    return str((_BACKEND_DIR / p).resolve())
