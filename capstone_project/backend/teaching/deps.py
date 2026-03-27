"""Shared FastAPI dependencies for teaching routes."""

from __future__ import annotations

import os
from typing import Generator

from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from backend.database import SessionLocal


def get_teaching_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_teaching_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.3,
    )
