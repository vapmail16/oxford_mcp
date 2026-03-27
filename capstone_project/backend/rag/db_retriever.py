"""
Semantic retrieval over SQLite-backed tickets and chat messages (structured DB RAG).

Uses a dedicated Qdrant collection `it_support_db`, separate from the markdown KB.
"""

from __future__ import annotations

import backend.env_bootstrap  # noqa: F401 — loads backend/.env before OpenAI embeddings

import gc
import os
from typing import List, Optional, Tuple

from langchain_core.documents import Document
from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from backend.database.models import Message, Ticket
from backend.rag.config_paths import get_qdrant_path
from backend.rag.ingest import create_vector_store
from backend.rag.retriever import format_docs_for_context, get_embeddings

DB_RAG_COLLECTION = "it_support_db"


def documents_from_db(
    db: Session,
    *,
    ticket_limit: int = 200,
    message_limit: int = 200,
) -> List[Document]:
    """Turn recent tickets and messages into LangChain documents for embedding."""
    docs: List[Document] = []

    for t in (
        db.query(Ticket).order_by(Ticket.created_at.desc()).limit(ticket_limit).all()
    ):
        body = (
            f"ticket_id:{t.id}\n"
            f"title:{t.title}\n"
            f"description:{t.description}\n"
            f"status:{t.status.value}\n"
            f"priority:{t.priority.value}\n"
            f"category:{t.category.value}\n"
            f"user_email:{t.user_email}\n"
        )
        docs.append(
            Document(
                page_content=body,
                metadata={
                    "source": f"ticket_{t.id}",
                    "source_type": "db_ticket",
                },
            )
        )

    for m in (
        db.query(Message).order_by(Message.created_at.desc()).limit(message_limit).all()
    ):
        body = (
            f"message_id:{m.id}\n"
            f"session_id:{m.session_id}\n"
            f"role:{m.role}\n"
            f"content:{m.content}\n"
        )
        docs.append(
            Document(
                page_content=body,
                metadata={
                    "source": f"message_{m.id}",
                    "source_type": "db_message",
                },
            )
        )

    return docs


def get_db_rag_context(
    db: Session,
    query: str,
    *,
    k: int = 5,
    embeddings=None,
    qdrant_path: Optional[str] = None,
    collection_name: str = DB_RAG_COLLECTION,
) -> Tuple[str, List[str]]:
    """
    Embed DB rows into Qdrant (fresh index per call for demo correctness), then retrieve.

    Args:
        db: SQLAlchemy session
        query: User question
        k: Top-k chunks
        embeddings: Optional embeddings (for tests)
        qdrant_path: Storage path (isolated tmp dir in tests)
        collection_name: Qdrant collection name (default it_support_db)
    """
    docs = documents_from_db(db)
    if not docs:
        return "", ["no_db_records"]

    persist = qdrant_path or get_qdrant_path()
    os.makedirs(persist, exist_ok=True)

    emb = embeddings if embeddings is not None else get_embeddings(None)

    _pre = QdrantClient(path=persist)
    try:
        if _pre.collection_exists(collection_name):
            _pre.delete_collection(collection_name)
    finally:
        _close = getattr(_pre, "close", None)
        if callable(_close):
            _close()
        del _pre
        gc.collect()

    vectorstore = create_vector_store(
        chunks=docs,
        persist_directory=persist,
        embeddings=emb,
        collection_name=collection_name,
    )

    try:
        found = vectorstore.similarity_search(query, k=k)
        context = format_docs_for_context(found, include_sources=False)
        sources: List[str] = []
        for doc in found:
            st = doc.metadata.get("source_type", "db")
            src = doc.metadata.get("source", st)
            label = f"{st}:{src}"
            if label not in sources:
                sources.append(label)
        return context, sources if sources else ["db_rag"]
    finally:
        _vc = getattr(vectorstore, "client", None)
        if _vc is not None:
            _cclose = getattr(_vc, "close", None)
            if callable(_cclose):
                try:
                    _cclose()
                except Exception:
                    pass
        del vectorstore
        gc.collect()
