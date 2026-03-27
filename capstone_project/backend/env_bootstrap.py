"""
Load `backend/.env` regardless of current working directory (uvicorn from capstone_project).
Import this module before other `backend.*` imports in entry points (main, pytest conftest).
"""
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")
