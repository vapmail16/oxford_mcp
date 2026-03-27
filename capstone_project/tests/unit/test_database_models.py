"""
Unit tests for database models.
These tests are written FIRST (TDD Red phase).
The models don't exist yet - that's the point!

Test Priority: P0 (Critical - data persistence)
Category: Unit, Data Integrity
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.database
class TestTicketModel:
    """
    Tests for the Ticket model.
    Red phase - these will fail until we implement the model.
    """

    def test_create_ticket_with_all_required_fields(self, db_session, sample_ticket_data):
        """
        Test Name: DATABASE_CreateTicket_AllFields_Success
        Priority: P0
        Category: Happy Path

        Description:
            Creating a ticket with all required fields should succeed
            and store all data correctly.

        Preconditions:
            - Database tables exist
            - Valid ticket data provided

        Expected Result:
            - Ticket created with auto-generated ID
            - All fields stored correctly
            - Timestamps auto-populated
        """
        from backend.database.models import Ticket, TicketStatus, TicketPriority, IssueCategory

        # Arrange
        ticket = Ticket(
            title=sample_ticket_data["title"],
            description=sample_ticket_data["description"],
            priority=TicketPriority[sample_ticket_data["priority"]],
            category=IssueCategory[sample_ticket_data["category"]],
            user_email=sample_ticket_data["user_email"]
        )

        # Act
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)

        # Assert
        assert ticket.id is not None
        assert ticket.title == sample_ticket_data["title"]
        assert ticket.description == sample_ticket_data["description"]
        assert ticket.priority == TicketPriority.HIGH
        assert ticket.category == IssueCategory.NETWORK
        assert ticket.user_email == sample_ticket_data["user_email"]
        assert ticket.status == TicketStatus.OPEN  # Default status
        assert isinstance(ticket.created_at, datetime)
        assert isinstance(ticket.updated_at, datetime)

    def test_create_ticket_without_user_email_raises_error(self, db_session):
        """
        Test Name: DATABASE_CreateTicket_MissingEmail_RaisesError
        Priority: P0
        Category: Negative

        Description:
            Attempting to create a ticket without user_email should fail.
            user_email is a required field.
        """
        from backend.database.models import Ticket, TicketPriority, IssueCategory

        # Arrange
        ticket = Ticket(
            title="Test Ticket",
            description="Test Description",
            priority=TicketPriority.MEDIUM,
            category=IssueCategory.SOFTWARE,
            user_email=None  # Missing required field
        )

        # Act & Assert
        with pytest.raises(IntegrityError):
            db_session.add(ticket)
            db_session.commit()

    def test_ticket_status_defaults_to_open(self, db_session):
        """
        Test Name: DATABASE_TicketStatus_NoStatusProvided_DefaultsToOpen
        Priority: P1
        Category: Happy Path

        Description:
            When creating a ticket without specifying status,
            it should default to OPEN.
        """
        from backend.database.models import Ticket, TicketStatus, TicketPriority, IssueCategory

        # Arrange & Act
        ticket = Ticket(
            title="Test",
            description="Test",
            priority=TicketPriority.LOW,
            category=IssueCategory.HARDWARE,
            user_email="test@acmecorp.com"
        )
        db_session.add(ticket)
        db_session.commit()

        # Assert
        assert ticket.status == TicketStatus.OPEN

    def test_ticket_priority_defaults_to_medium(self, db_session):
        """
        Test Name: DATABASE_TicketPriority_NoPriorityProvided_DefaultsToMedium
        Priority: P1
        Category: Happy Path
        """
        from backend.database.models import Ticket, TicketPriority, IssueCategory

        # Arrange & Act
        ticket = Ticket(
            title="Test",
            description="Test",
            category=IssueCategory.ACCESS,
            user_email="test@acmecorp.com"
            # priority not specified
        )
        db_session.add(ticket)
        db_session.commit()

        # Assert
        assert ticket.priority == TicketPriority.MEDIUM

    def test_ticket_updated_at_changes_on_update(self, db_session, sample_ticket_data):
        """
        Test Name: DATABASE_TicketUpdate_FieldChanged_UpdatedAtChanges
        Priority: P1
        Category: Data Integrity

        Description:
            When a ticket is updated, the updated_at timestamp
            should change to reflect the modification.
        """
        from backend.database.models import Ticket, TicketPriority, IssueCategory
        import time

        # Arrange
        ticket = Ticket(
            title=sample_ticket_data["title"],
            description=sample_ticket_data["description"],
            priority=TicketPriority[sample_ticket_data["priority"]],
            category=IssueCategory[sample_ticket_data["category"]],
            user_email=sample_ticket_data["user_email"]
        )
        db_session.add(ticket)
        db_session.commit()
        original_updated_at = ticket.updated_at

        # Act
        time.sleep(0.1)  # Ensure timestamp difference
        ticket.description = "Updated description"
        db_session.commit()
        db_session.refresh(ticket)

        # Assert
        assert ticket.updated_at > original_updated_at

    def test_all_ticket_statuses_are_valid(self, db_session):
        """
        Test Name: DATABASE_TicketStatus_AllValues_AcceptedByDatabase
        Priority: P1
        Category: Edge Case

        Description:
            All defined ticket statuses should be valid database values.
        """
        from backend.database.models import Ticket, TicketStatus, TicketPriority, IssueCategory

        # Test all status values
        for status in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS,
                       TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            ticket = Ticket(
                title=f"Test {status.value}",
                description="Test",
                priority=TicketPriority.LOW,
                category=IssueCategory.SOFTWARE,
                user_email="test@acmecorp.com",
                status=status
            )
            db_session.add(ticket)
            db_session.commit()

            assert ticket.status == status
            db_session.delete(ticket)  # Cleanup for next iteration

    def test_ticket_with_session_id_links_to_conversation(self, db_session):
        """
        Test Name: DATABASE_Ticket_WithSessionId_LinksToConversation
        Priority: P1
        Category: Happy Path

        Description:
            Tickets can optionally be linked to a conversation session.
        """
        from backend.database.models import Ticket, TicketPriority, IssueCategory

        # Arrange & Act
        session_id = "test-session-789"
        ticket = Ticket(
            title="Test",
            description="Test",
            priority=TicketPriority.MEDIUM,
            category=IssueCategory.NETWORK,
            user_email="test@acmecorp.com",
            session_id=session_id
        )
        db_session.add(ticket)
        db_session.commit()

        # Assert
        assert ticket.session_id == session_id


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.database
class TestMessageModel:
    """
    Tests for the Message model (conversation history).
    Red phase - model doesn't exist yet.
    """

    def test_create_message_with_all_fields(self, db_session, sample_message_data):
        """
        Test Name: DATABASE_CreateMessage_AllFields_Success
        Priority: P0
        Category: Happy Path

        Description:
            Creating a message should store all conversation data correctly.
        """
        from backend.database.models import Message

        # Arrange & Act
        message = Message(
            session_id=sample_message_data["session_id"],
            role=sample_message_data["role"],
            content=sample_message_data["content"]
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)

        # Assert
        assert message.id is not None
        assert message.session_id == sample_message_data["session_id"]
        assert message.role == sample_message_data["role"]
        assert message.content == sample_message_data["content"]
        assert isinstance(message.created_at, datetime)

    def test_message_without_session_id_raises_error(self, db_session):
        """
        Test Name: DATABASE_CreateMessage_MissingSessionId_RaisesError
        Priority: P0
        Category: Negative

        Description:
            session_id is required to group messages into conversations.
        """
        from backend.database.models import Message

        # Arrange
        message = Message(
            session_id=None,  # Missing required field
            role="user",
            content="Test message"
        )

        # Act & Assert
        with pytest.raises(IntegrityError):
            db_session.add(message)
            db_session.commit()

    def test_message_role_can_be_user_or_assistant(self, db_session):
        """
        Test Name: DATABASE_MessageRole_UserAndAssistant_BothValid
        Priority: P1
        Category: Happy Path

        Description:
            Messages can be from either user or assistant.
        """
        from backend.database.models import Message

        # Test user message
        user_msg = Message(
            session_id="test-session",
            role="user",
            content="User question"
        )
        db_session.add(user_msg)
        db_session.commit()
        assert user_msg.role == "user"

        # Test assistant message
        assistant_msg = Message(
            session_id="test-session",
            role="assistant",
            content="Assistant response"
        )
        db_session.add(assistant_msg)
        db_session.commit()
        assert assistant_msg.role == "assistant"

    def test_message_metadata_can_store_json(self, db_session):
        """
        Test Name: DATABASE_MessageMetadata_JSONString_StoredCorrectly
        Priority: P1
        Category: Happy Path

        Description:
            Metadata field can store JSON string for sources, ticket_id, etc.
        """
        from backend.database.models import Message
        import json

        # Arrange
        metadata = json.dumps({
            "sources": ["vpn_guide.md", "password_reset.md"],
            "ticket_id": 12345,
            "confidence": 0.85
        })

        # Act
        message = Message(
            session_id="test-session",
            role="assistant",
            content="Here's your answer",
            msg_metadata=metadata
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)

        # Assert
        assert message.msg_metadata is not None
        parsed_metadata = json.loads(message.msg_metadata)
        assert parsed_metadata["ticket_id"] == 12345
        assert len(parsed_metadata["sources"]) == 2

    def test_messages_in_same_session_can_be_queried(self, db_session):
        """
        Test Name: DATABASE_MessagesBySession_MultipleMessages_AllRetrieved
        Priority: P0
        Category: Happy Path

        Description:
            All messages in a session should be retrievable by session_id.
        """
        from backend.database.models import Message

        # Arrange
        session_id = "test-session-multi"
        messages = [
            Message(session_id=session_id, role="user", content="Question 1"),
            Message(session_id=session_id, role="assistant", content="Answer 1"),
            Message(session_id=session_id, role="user", content="Question 2"),
            Message(session_id=session_id, role="assistant", content="Answer 2"),
        ]

        for msg in messages:
            db_session.add(msg)
        db_session.commit()

        # Act
        retrieved = db_session.query(Message).filter_by(session_id=session_id).all()

        # Assert
        assert len(retrieved) == 4
        assert retrieved[0].content == "Question 1"
        assert retrieved[3].content == "Answer 2"

    def test_very_long_message_content_stored_correctly(self, db_session):
        """
        Test Name: DATABASE_MessageContent_VeryLongText_StoredCorrectly
        Priority: P2
        Category: Edge Case

        Description:
            Messages can be very long (user pasting logs, etc.).
            Test storage of 10,000+ character message.
        """
        from backend.database.models import Message

        # Arrange
        long_content = "A" * 15000  # 15,000 characters

        # Act
        message = Message(
            session_id="test-session",
            role="user",
            content=long_content
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)

        # Assert
        assert len(message.content) == 15000
        assert message.content == long_content


@pytest.mark.unit
@pytest.mark.priority_p0
class TestDatabaseEnums:
    """
    Tests for database enums (TicketStatus, TicketPriority, IssueCategory).
    """

    def test_ticket_status_has_all_required_values(self):
        """
        Test Name: DATABASE_TicketStatus_AllValues_Defined
        Priority: P0
        Category: Happy Path

        Description:
            TicketStatus enum must have all required workflow states.
        """
        from backend.database.models import TicketStatus

        assert hasattr(TicketStatus, "OPEN")
        assert hasattr(TicketStatus, "IN_PROGRESS")
        assert hasattr(TicketStatus, "RESOLVED")
        assert hasattr(TicketStatus, "CLOSED")

        assert TicketStatus.OPEN.value == "OPEN"
        assert TicketStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert TicketStatus.RESOLVED.value == "RESOLVED"
        assert TicketStatus.CLOSED.value == "CLOSED"

    def test_ticket_priority_has_all_levels(self):
        """
        Test Name: DATABASE_TicketPriority_AllLevels_Defined
        Priority: P0
        Category: Happy Path
        """
        from backend.database.models import TicketPriority

        assert hasattr(TicketPriority, "LOW")
        assert hasattr(TicketPriority, "MEDIUM")
        assert hasattr(TicketPriority, "HIGH")
        assert hasattr(TicketPriority, "CRITICAL")

        assert TicketPriority.LOW.value == "LOW"
        assert TicketPriority.CRITICAL.value == "CRITICAL"

    def test_issue_category_has_all_types(self):
        """
        Test Name: DATABASE_IssueCategory_AllTypes_Defined
        Priority: P0
        Category: Happy Path
        """
        from backend.database.models import IssueCategory

        required_categories = ["PASSWORD", "NETWORK", "SOFTWARE", "HARDWARE", "ACCESS", "UNKNOWN"]

        for category in required_categories:
            assert hasattr(IssueCategory, category)
            assert getattr(IssueCategory, category).value == category
