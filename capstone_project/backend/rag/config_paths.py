"""
RAG PATH RESOLUTION
===================
What this module demonstrates:
  - One canonical resolver for where Qdrant data is stored on disk.
  - Stable behavior regardless of shell working directory.
  - Support for both absolute and relative QDRANT_PATH values.
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
    # Read optional override from environment.
    raw = os.getenv("QDRANT_PATH")
    if not raw:
        # Default local storage under backend/.
        return str(_BACKEND_DIR / "qdrant_storage")
    p = Path(raw)
    if p.is_absolute():
        # Absolute path is used as-is.
        return str(p)
    # Relative path is anchored under backend/ for consistency.
    return str((_BACKEND_DIR / p).resolve())
