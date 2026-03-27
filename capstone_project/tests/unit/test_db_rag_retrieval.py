"""TDD: RAG over SQLite tickets/messages into Qdrant collection it_support_db."""

import shutil

import pytest
from pathlib import Path
from langchain_core.documents import Document

pytestmark = pytest.mark.unit


@pytest.mark.database
def test_documents_from_db_includes_ticket_fields(db_session, sample_ticket_data):
    from backend.database.crud import create_ticket
    from backend.rag.db_retriever import documents_from_db, DB_RAG_COLLECTION

    assert DB_RAG_COLLECTION == "it_support_db"

    create_ticket(
        db=db_session,
        title=sample_ticket_data["title"],
        description=sample_ticket_data["description"],
        priority=sample_ticket_data["priority"],
        category=sample_ticket_data["category"],
        user_email=sample_ticket_data["user_email"],
    )
    docs = documents_from_db(db_session)
    assert len(docs) >= 1
    joined = " ".join(d.page_content for d in docs)
    assert "VPN" in joined or "vpn" in joined.lower()
    assert any(d.metadata.get("source_type") == "db_ticket" for d in docs)


@pytest.mark.database
def test_documents_from_db_includes_chat_messages(db_session):
    from backend.database.crud import create_message
    from backend.rag.db_retriever import documents_from_db

    create_message(
        db=db_session,
        session_id="sess-1",
        role="user",
        content="Printer on floor 3 is jammed",
    )
    docs = documents_from_db(db_session)
    assert any("Printer" in d.page_content or "printer" in d.page_content.lower() for d in docs)
    assert any(d.metadata.get("source_type") == "db_message" for d in docs)


def test_get_db_rag_context_returns_matching_chunk(
    db_engine, mock_embeddings, tmp_path: Path
):
    """Isolated Qdrant path + in-memory DB with one VPN ticket."""
    from sqlalchemy.orm import sessionmaker
    from backend.database.models import Base, Ticket, TicketStatus, TicketPriority, IssueCategory
    from backend.rag.db_retriever import get_db_rag_context

    Base.metadata.create_all(bind=db_engine)
    Session = sessionmaker(bind=db_engine)
    db = Session()
    try:
        t = Ticket(
            title="VPN flaky for sales",
            description="VPN drops every hour for remote sales team.",
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
            category=IssueCategory.NETWORK,
            user_email="sales@acme.com",
        )
        db.add(t)
        db.commit()

        qdrant_dir = str(tmp_path / "qdb")
        Path(qdrant_dir).mkdir(parents=True, exist_ok=True)

        context, sources = get_db_rag_context(
            db,
            "Why is VPN unstable for sales?",
            k=3,
            embeddings=mock_embeddings,
            qdrant_path=qdrant_dir,
        )
        assert "VPN" in context or "vpn" in context.lower()
        assert len(sources) >= 1
    finally:
        db.close()
        shutil.rmtree(tmp_path / "qdb", ignore_errors=True)


def test_get_db_rag_context_source_labels_include_type_prefix(
    db_engine, mock_embeddings, tmp_path: Path
):
    """Sources returned to the API should distinguish ticket vs message (demo / UI)."""
    from sqlalchemy.orm import sessionmaker
    from backend.database.models import Base, Ticket, TicketStatus, TicketPriority, IssueCategory
    from backend.rag.db_retriever import get_db_rag_context

    Base.metadata.create_all(bind=db_engine)
    Session = sessionmaker(bind=db_engine)
    db = Session()
    qdrant_dir = str(tmp_path / "qlab")
    Path(qdrant_dir).mkdir(parents=True, exist_ok=True)
    try:
        db.add(
            Ticket(
                title="Email sync",
                description="Outlook not syncing.",
                status=TicketStatus.OPEN,
                priority=TicketPriority.LOW,
                category=IssueCategory.SOFTWARE,
                user_email="u@acme.com",
            )
        )
        db.commit()

        _ctx, sources = get_db_rag_context(
            db,
            "Outlook email",
            k=3,
            embeddings=mock_embeddings,
            qdrant_path=qdrant_dir,
        )
        assert any("db_ticket:" in s for s in sources)
    finally:
        db.close()


def test_get_db_rag_context_empty_db_returns_empty(mock_embeddings, tmp_path: Path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.database.models import Base
    from backend.rag.db_retriever import get_db_rag_context

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        ctx, src = get_db_rag_context(
            db,
            "anything",
            k=3,
            embeddings=mock_embeddings,
            qdrant_path=str(tmp_path / "qempty"),
        )
        assert ctx == ""
        assert "no_db_records" in src
    finally:
        db.close()
