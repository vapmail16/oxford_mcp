"""TDD: FastAPI app entrypoint (see README): `backend.main` from capstone_project, or `main` from backend/."""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_backend_main_app_exposes_fastapi_instance():
    import backend.main

    assert backend.main.app.title == "IT Support Agent API"


def test_import_main_module_when_cwd_is_backend_dir():
    """Matches `cd backend && python3 -m uvicorn main:app` — no PYTHONPATH to capstone_project."""
    capstone = Path(__file__).resolve().parent.parent.parent
    backend_dir = capstone / "backend"
    proc = subprocess.run(
        [sys.executable, "-c", "import main; assert main.app.title == 'IT Support Agent API'"],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
