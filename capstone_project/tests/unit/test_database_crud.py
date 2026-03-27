"""
Unit tests for database CRUD operations.
RED PHASE - These tests will fail until we implement crud.py

Test Priority: P0-P1 (Critical database operations)
Category: Unit, Data Integrity
"""

import pytest
from datetime import datetime


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.database
class TestTicketCRUD:
    """Tests for ticket CRUD operations"""

    def test_create_ticket_returns_ticket_with_id(self, db_session):
        """
        Test Name: CRUD_CreateTicket_ValidData_ReturnsTicketWithID
        Priority: P0
        Category: Happy Path
        """
        from backend.database.crud import create_ticket

        # Act
        ticket = create_ticket(
            db=db_session,
            title="Cannot connect to VPN",
            description="Getting error 422",
            priority="HIGH",
            category="NETWORK",
            user_email="test@acmecorp.com"
        )

        # Assert
        assert ticket.id is not None
        assert ticket.title == "Cannot connect to VPN"
        assert ticket.priority.value == "HIGH"
        assert ticket.category.value == "NETWORK"

    def test_get_ticket_by_existing_id_returns_ticket(self, db_session):
        """
        Test Name: CRUD_GetTicket_ExistingID_ReturnsTicket
        Priority: P0
        Category: Happy Path
        """
        from backend.database.crud import create_ticket, get_ticket

        # Arrange
        created_ticket = create_ticket(
            db=db_session,
            title="Test Ticket",
            description="Test",
            priority="MEDIUM",
            category="SOFTWARE",
            user_email="test@acmecorp.com"
        )

        # Act
        retrieved_ticket = get_ticket(db_session, created_ticket.id)

        # Assert
        assert retrieved_ticket is not None
        assert retrieved_ticket.id == created_ticket.id
        assert retrieved_ticket.title == "Test Ticket"

    def test_get_ticket_by_nonexistent_id_returns_none(self, db_session):
        """
        Test Name: CRUD_GetTicket_NonexistentID_ReturnsNone
        Priority: P0
        Category: Negative
        """
        from backend.database.crud import get_ticket

        # Act
        ticket = get_ticket(db_session, 99999)

        # Assert
        assert ticket is None

    def test_get_all_tickets_returns_list(self, db_session):
        """
        Test Name: CRUD_GetAllTickets_MultipleTickets_ReturnsList
        Priority: P1
        Category: Happy Path
        """
        from backend.database.crud import create_ticket, get_all_tickets

        # Arrange - create 3 tickets
        for i in range(3):
            create_ticket(
                db=db_session,
                title=f"Ticket {i}",
                description=f"Description {i}",
                priority="MEDIUM",
                category="SOFTWARE",
                user_email=f"user{i}@acmecorp.com"
            )

        # Act
        tickets = get_all_tickets(db_session)

        # Assert
        assert len(tickets) >= 3
        assert all(hasattr(t, 'id') for t in tickets)

    def test_get_tickets_filtered_by_status(self, db_session):
        """
        Test Name: CRUD_GetTickets_FilterByStatus_ReturnsFiltered
        Priority: P1
        Category: Happy Path
        """
        from backend.database.crud import create_ticket, get_all_tickets
        from backend.database.models import Ticket, TicketStatus

        # Arrange - create tickets with different statuses
        ticket1 = create_ticket(
            db=db_session,
            title="Open Ticket",
            description="Test",
            priority="LOW",
            category="SOFTWARE",
            user_email="test@acmecorp.com"
        )

        ticket2 = Ticket(
            title="In Progress Ticket",
            description="Test",
            priority="MEDIUM",
            category="NETWORK",
            user_email="test@acmecorp.com",
            status=TicketStatus.IN_PROGRESS
        )
        db_session.add(ticket2)
        db_session.commit()

        # Act
        open_tickets = get_all_tickets(db_session, status="OPEN")

        # Assert
        assert len(open_tickets) >= 1
        assert all(t.status == TicketStatus.OPEN for t in open_tickets)

    def test_update_ticket_status_changes_status(self, db_session):
        """
        Test Name: CRUD_UpdateTicketStatus_ValidStatus_UpdatesStatus
        Priority: P0
        Category: Happy Path
        """
        from backend.database.crud import create_ticket, update_ticket_status
        from backend.database.models import TicketStatus

        # Arrange
        ticket = create_ticket(
            db=db_session,
            title="Test",
            description="Test",
            priority="MEDIUM",
            category="SOFTWARE",
            user_email="test@acmecorp.com"
        )
        original_updated_at = ticket.updated_at

        # Act
        updated_ticket = update_ticket_status(
            db=db_session,
            ticket_id=ticket.id,
            status="IN_PROGRESS"
        )

        # Assert
        assert updated_ticket is not None
        assert updated_ticket.status == TicketStatus.IN_PROGRESS
        assert updated_ticket.updated_at >= original_updated_at

    def test_update_ticket_status_with_note_adds_note(self, db_session):
        """
        Test Name: CRUD_UpdateTicketStatus_WithNote_AppendsNote
        Priority: P1
        Category: Happy Path
        """
        from backend.database.crud import create_ticket, update_ticket_status

        # Arrange
        ticket = create_ticket(
            db=db_session,
            title="Test",
            description="Test",
            priority="MEDIUM",
            category="SOFTWARE",
            user_email="test@acmecorp.com"
        )

        # Act
        updated_ticket = update_ticket_status(
            db=db_session,
            ticket_id=ticket.id,
            status="RESOLVED",
            note="Fixed by rebooting server"
        )

        # Assert
        assert updated_ticket.notes is not None
        assert "Fixed by rebooting server" in updated_ticket.notes

    def test_update_nonexistent_ticket_returns_none(self, db_session):
        """
        Test Name: CRUD_UpdateTicketStatus_NonexistentID_ReturnsNone
        Priority: P1
        Category: Negative
        """
        from backend.database.crud import update_ticket_status

        # Act
        result = update_ticket_status(
            db=db_session,
            ticket_id=99999,
            status="CLOSED"
        )

        # Assert
        assert result is None


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.database
class TestMessageCRUD:
    """Tests for message CRUD operations"""

    def test_create_message_returns_message_with_id(self, db_session):
        """
        Test Name: CRUD_CreateMessage_ValidData_ReturnsMessageWithID
        Priority: P0
        Category: Happy Path
        """
        from backend.database.crud import create_message

        # Act
        message = create_message(
            db=db_session,
            session_id="test-session-123",
            role="user",
            content="I can't connect to VPN"
        )

        # Assert
        assert message.id is not None
        assert message.session_id == "test-session-123"
        assert message.role == "user"
        assert message.content == "I can't connect to VPN"

    def test_create_message_with_metadata(self, db_session):
        """
        Test Name: CRUD_CreateMessage_WithMetadata_StoresMetadata
        Priority: P1
        Category: Happy Path
        """
        from backend.database.crud import create_message

        # Arrange
        metadata = {
            "sources": ["vpn_guide.md"],
            "confidence": 0.85
        }

        # Act
        message = create_message(
            db=db_session,
            session_id="test-session",
            role="assistant",
            content="Try these steps...",
            metadata=metadata
        )

        # Assert
        assert message.msg_metadata is not None
        import json
        parsed = json.loads(message.msg_metadata)
        assert parsed["confidence"] == 0.85

    def test_get_messages_by_session_returns_chronological_order(self, db_session):
        """
        Test Name: CRUD_GetMessagesBySession_MultipleMessages_ReturnedInOrder
        Priority: P0
        Category: Happy Path
        """
        from backend.database.crud import create_message, get_messages_by_session
        import time

        # Arrange - create messages in order
        session_id = "test-session-order"
        create_message(db_session, session_id, "user", "First message")
        time.sleep(0.01)
        create_message(db_session, session_id, "assistant", "Second message")
        time.sleep(0.01)
        create_message(db_session, session_id, "user", "Third message")

        # Act
        messages = get_messages_by_session(db_session, session_id)

        # Assert
        assert len(messages) == 3
        assert messages[0].content == "First message"
        assert messages[1].content == "Second message"
        assert messages[2].content == "Third message"

    def test_get_messages_by_session_with_limit(self, db_session):
        """
        Test Name: CRUD_GetMessagesBySession_WithLimit_ReturnsLimitedResults
        Priority: P2
        Category: Edge Case
        """
        from backend.database.crud import create_message, get_messages_by_session

        # Arrange - create 10 messages
        session_id = "test-session-limit"
        for i in range(10):
            create_message(db_session, session_id, "user", f"Message {i}")

        # Act
        messages = get_messages_by_session(db_session, session_id, limit=5)

        # Assert
        assert len(messages) == 5

    def test_get_conversation_history_returns_formatted_list(self, db_session):
        """
        Test Name: CRUD_GetConversationHistory_MultipleMessages_ReturnsFormatted
        Priority: P0
        Category: Happy Path
        """
        from backend.database.crud import create_message, get_conversation_history

        # Arrange
        session_id = "test-session-history"
        create_message(db_session, session_id, "user", "Hello")
        create_message(db_session, session_id, "assistant", "Hi, how can I help?")

        # Act
        history = get_conversation_history(db_session, session_id)

        # Assert
        assert isinstance(history, list)
        assert len(history) == 2
        assert all("role" in msg and "content" in msg for msg in history)
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"

    def test_get_conversation_history_with_window_size(self, db_session):
        """
        Test Name: CRUD_GetConversationHistory_WindowSize_ReturnsLastN
        Priority: P1
        Category: Edge Case
        """
        from backend.database.crud import create_message, get_conversation_history

        # Arrange - create 10 messages
        session_id = "test-session-window"
        for i in range(10):
            create_message(db_session, session_id, "user", f"Message {i}")

        # Act
        history = get_conversation_history(db_session, session_id, window_size=3)

        # Assert
        assert len(history) == 3
        # Should return last 3 messages
        assert history[-1]["content"] == "Message 9"

    def test_get_messages_for_nonexistent_session_returns_empty(self, db_session):
        """
        Test Name: CRUD_GetMessagesBySession_NonexistentSession_ReturnsEmpty
        Priority: P1
        Category: Negative
        """
        from backend.database.crud import get_messages_by_session

        # Act
        messages = get_messages_by_session(db_session, "nonexistent-session")

        # Assert
        assert messages == []
