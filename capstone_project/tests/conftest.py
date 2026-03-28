"""
Shared pytest fixtures for IT Support Agent tests.
This file is automatically discovered by pytest.
"""

import backend.env_bootstrap  # noqa: F401 — load backend/.env for local runs

import os

# Unit tests must not spawn the Node MCP stdio server by default (no npx/npm required in CI).
os.environ["USE_SIMULATED_MCP"] = "1"

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import Mock, MagicMock

# This will be implemented later - just defining the imports for now
# from backend.database.models import Base

@pytest.fixture(scope="session")
def test_database_url():
    """Provide test database URL (in-memory SQLite)."""
    return "sqlite:///:memory:"


@pytest.fixture
def db_engine(test_database_url):
    """Create a test database engine."""
    from backend.database.models import Base

    engine = create_engine(
        test_database_url,
        connect_args={"check_same_thread": False},
        echo=False  # Set to True for SQL debugging
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Provide a transactional database session for tests.
    Each test gets a fresh session that rolls back after the test.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()

    yield session

    session.rollback()
    session.close()


@pytest.fixture
def sample_ticket_data():
    """Provide sample ticket data for tests."""
    return {
        "title": "Cannot connect to VPN",
        "description": "Getting error 422 when trying to connect to VPN. Tried restarting already.",
        "priority": "HIGH",
        "category": "NETWORK",
        "user_email": "john.doe@oxforduniversity.com",
        "status": "OPEN"
    }


@pytest.fixture
def sample_message_data():
    """Provide sample message data for tests."""
    return {
        "session_id": "test-session-123",
        "role": "user",
        "content": "I can't connect to the VPN",
        "msg_metadata": None
    }


@pytest.fixture
def temp_docs_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory with sample documents for testing.
    """
    temp_dir = Path(tempfile.mkdtemp())

    # Create sample documents
    sample_docs = {
        "vpn_guide.md": """# VPN Setup Guide

## VPN Error 422

If you get error 422:
1. Close Cisco AnyConnect
2. Wait 30 seconds
3. Reopen and try again
4. Respond to MFA within 60 seconds
""",
        "password_reset.md": """# Password Reset

To reset your password:
1. Go to https://password.oxforduniversity.com
2. Click "Forgot Password"
3. Answer security questions
4. Enter new password
""",
        "wifi_troubleshooting.md": """# WiFi Issues

Cannot connect to WiFi:
1. Forget the network
2. Reconnect with credentials
3. Ensure using OxfordUniversity-Secure network
"""
    }

    for filename, content in sample_docs.items():
        filepath = temp_dir / filename
        filepath.write_text(content)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_llm():
    """
    Provide a mock LLM that returns fixed responses.
    Useful for deterministic testing without API calls.
    """
    mock = MagicMock()

    # Default response
    mock.invoke.return_value = "This is a mock LLM response."

    # For streaming
    mock.stream.return_value = iter(["This ", "is ", "a ", "mock ", "stream."])

    return mock


@pytest.fixture
def mock_embeddings():
    """
    Small deterministic embedding model for tests (Qdrant + LangChain validate type/dim).
    """
    from langchain_core.embeddings import FakeEmbeddings

    return FakeEmbeddings(size=3)


@pytest.fixture
def mock_vectorstore():
    """
    Provide a mock vector store with canned retrieval results.
    """
    from backend.rag.retriever import Document  # Will be implemented

    mock = MagicMock()

    # Mock retrieval results
    mock_docs = [
        Document(
            page_content="VPN Error 422: Close AnyConnect, wait 30 seconds, reopen.",
            metadata={"source": "vpn_guide.md"}
        ),
        Document(
            page_content="Respond to MFA within 60 seconds to avoid timeout.",
            metadata={"source": "vpn_guide.md"}
        )
    ]

    mock.similarity_search.return_value = mock_docs
    mock.as_retriever.return_value.invoke.return_value = mock_docs

    return mock


@pytest.fixture
def golden_rag_dataset():
    """
    Provide golden dataset for RAG testing.
    These are verified query/answer pairs.
    """
    return [
        {
            "query": "I'm getting VPN error 422",
            "expected_category": "NETWORK",
            "expected_sources": ["vpn_guide.md"],
            "must_include_phrases": ["Close AnyConnect", "wait 30 seconds"],
            "must_not_include": ["password", "wifi", "printer"],
            "min_confidence": 0.7
        },
        {
            "query": "How do I reset my password?",
            "expected_category": "PASSWORD",
            "expected_sources": ["password_reset.md"],
            "must_include_phrases": ["password.oxforduniversity.com", "security questions"],
            "must_not_include": ["VPN", "wifi"],
            "min_confidence": 0.8
        },
        {
            "query": "Can't connect to WiFi",
            "expected_category": "NETWORK",
            "expected_sources": ["wifi_troubleshooting.md"],
            "must_include_phrases": ["Forget the network", "OxfordUniversity-Secure"],
            "must_not_include": ["password reset", "VPN"],
            "min_confidence": 0.7
        }
    ]


@pytest.fixture
def golden_triage_dataset():
    """
    Provide golden dataset for triage agent testing.
    These are verified issue classifications.
    """
    return [
        {
            "issue": "I forgot my password",
            "expected_category": "PASSWORD",
            "expected_confidence_min": 0.9,
            "expected_priority": "MEDIUM"
        },
        {
            "issue": "My laptop won't turn on at all",
            "expected_category": "HARDWARE",
            "expected_confidence_min": 0.85,
            "expected_priority": "HIGH"
        },
        {
            "issue": "Can't connect to company WiFi",
            "expected_category": "NETWORK",
            "expected_confidence_min": 0.85,
            "expected_priority": "MEDIUM"
        },
        {
            "issue": "Need access to the sales folder",
            "expected_category": "ACCESS",
            "expected_confidence_min": 0.8,
            "expected_priority": "MEDIUM"
        },
        {
            "issue": "Excel keeps crashing when I open large files",
            "expected_category": "SOFTWARE",
            "expected_confidence_min": 0.75,
            "expected_priority": "MEDIUM"
        },
        {
            "issue": "help",
            "expected_category": "UNKNOWN",
            "expected_confidence_max": 0.5,
            "expected_priority": "MEDIUM"
        }
    ]


@pytest.fixture
def sample_conversation_state():
    """
    Provide sample LangGraph state for agent testing.
    """
    return {
        "session_id": "test-session-456",
        "messages": [
            {"role": "user", "content": "I can't connect to VPN"}
        ],
        "issue_category": None,
        "retrieved_docs": [],
        "ticket_id": None,
        "resolved": False
    }


@pytest.fixture(autouse=True)
def reset_environment():
    """
    Auto-used fixture that resets environment for each test.
    """
    # Set test mode
    os.environ["TESTING"] = "True"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    yield

    # Cleanup after test
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture
def mock_mcp_server():
    """
    Provide a mock MCP server for testing tool execution.
    """
    mock = MagicMock()

    # Mock tool responses
    mock.create_ticket.return_value = {
        "ticket_id": 12345,
        "status": "OPEN",
        "success": True
    }

    mock.get_ticket.return_value = {
        "ticket_id": 12345,
        "title": "VPN Connection Issue",
        "status": "OPEN"
    }

    mock.check_system_status.return_value = {
        "service": "vpn",
        "status": "UP"
    }

    return mock


# Pytest hooks for custom behavior

def pytest_configure(config):
    """
    Configure pytest with custom settings.
    """
    # Add custom markers
    config.addinivalue_line(
        "markers", "database: mark test as database test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers automatically.
    """
    for item in items:
        # Auto-mark database tests
        if "db_session" in item.fixturenames or "db_engine" in item.fixturenames:
            item.add_marker(pytest.mark.database)

        # Auto-mark AI quality tests
        if "tests/ai_quality" in str(item.fspath):
            item.add_marker(pytest.mark.ai_quality)
            item.add_marker(pytest.mark.slow)
