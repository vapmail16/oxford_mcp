"""
CHAT DEMO PACKAGE
=================
Exports the main router entrypoint used by FastAPI chat handlers.
"""

from backend.chat_demo.router import compute_chat_reply

__all__ = ["compute_chat_reply"]
