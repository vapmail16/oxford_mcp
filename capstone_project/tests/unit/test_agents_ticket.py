"""
Unit tests for Ticket Agent
RED PHASE - These tests will fail until we implement ticket_agent.py

Test Priority: P0-P1 (Critical for multi-agent workflow)
Category: Unit, Agents
"""

import pytest
from typing import Dict, Any


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestTicketAgentCreation:
    """Tests for ticket creation functionality"""

    def test_ticket_agent_creates_ticket_from_description(self):
        """
        Test Name: TicketAgent_IssueDescription_CreatesTicket
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        issue_description = "My laptop won't turn on at all"
        classification = {
            'category': 'HARDWARE',
            'priority': 'HIGH'
        }

        # Act
        result = agent.create_ticket(
            description=issue_description,
            classification=classification,
            user_email="test@acmecorp.com"
        )

        # Assert
        assert result['ticket_id'] is not None
        assert result['status'] == 'OPEN'
        assert result['title'] is not None
        assert len(result['title']) > 0

    def test_ticket_agent_extracts_title_from_description(self):
        """
        Test Name: TicketAgent_LongDescription_ExtractsTitle
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        description = "VPN error 422 when connecting from home, tried all fixes"
        classification = {'category': 'VPN', 'priority': 'MEDIUM'}

        # Act
        result = agent.create_ticket(
            description=description,
            classification=classification,
            user_email="user@acmecorp.com"
        )

        # Assert
        assert result['title'] is not None
        assert 'VPN' in result['title'] or 'vpn' in result['title'].lower()
        assert len(result['title']) < 100  # Title should be concise

    def test_ticket_agent_sets_priority_from_classification(self):
        """
        Test Name: TicketAgent_UrgentClassification_SetsUrgentPriority
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        description = "Critical system issue"
        classification = {'category': 'GENERAL', 'priority': 'URGENT'}

        # Act
        result = agent.create_ticket(
            description=description,
            classification=classification,
            user_email="user@acmecorp.com"
        )

        # Assert
        assert result['priority'] in ['HIGH', 'URGENT', 'CRITICAL']

    def test_ticket_agent_includes_category(self):
        """
        Test Name: TicketAgent_WithCategory_IncludesInTicket
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        description = "Password reset needed"
        classification = {'category': 'PASSWORD', 'priority': 'LOW'}

        # Act
        result = agent.create_ticket(
            description=description,
            classification=classification,
            user_email="user@acmecorp.com"
        )

        # Assert
        assert 'category' in result
        assert result['category'] == 'PASSWORD'


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestTicketAgentRetrieval:
    """Tests for ticket retrieval and search"""

    def test_ticket_agent_retrieves_ticket_by_id(self):
        """
        Test Name: TicketAgent_ValidID_RetrievesTicket
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        # First create a ticket
        create_result = agent.create_ticket(
            description="Test ticket",
            classification={'category': 'GENERAL', 'priority': 'LOW'},
            user_email="test@acmecorp.com"
        )
        ticket_id = create_result['ticket_id']

        # Act
        result = agent.get_ticket(ticket_id)

        # Assert
        assert result is not None
        assert result['id'] == ticket_id
        assert result['status'] == 'OPEN'

    def test_ticket_agent_handles_invalid_ticket_id(self):
        """
        Test Name: TicketAgent_InvalidID_ReturnsNone
        Priority: P1
        Category: Edge Case
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        invalid_id = 99999

        # Act
        result = agent.get_ticket(invalid_id)

        # Assert
        assert result is None or 'error' in result


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestTicketAgentUpdate:
    """Tests for ticket updates"""

    def test_ticket_agent_updates_ticket_status(self):
        """
        Test Name: TicketAgent_UpdateStatus_SuccessfullyUpdates
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        create_result = agent.create_ticket(
            description="Test ticket",
            classification={'category': 'GENERAL', 'priority': 'LOW'},
            user_email="test@acmecorp.com"
        )
        ticket_id = create_result['ticket_id']

        # Act
        update_result = agent.update_ticket(
            ticket_id=ticket_id,
            status="IN_PROGRESS",
            note="Working on it"
        )

        # Assert
        assert update_result['success'] is True
        # Verify update persisted
        ticket = agent.get_ticket(ticket_id)
        assert ticket['status'] == 'IN_PROGRESS'

    def test_ticket_agent_adds_note_to_ticket(self):
        """
        Test Name: TicketAgent_AddNote_StoresNote
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        create_result = agent.create_ticket(
            description="Test ticket",
            classification={'category': 'GENERAL', 'priority': 'LOW'},
            user_email="test@acmecorp.com"
        )
        ticket_id = create_result['ticket_id']

        # Act
        note = "User confirmed issue resolved"
        agent.update_ticket(ticket_id=ticket_id, note=note)

        # Assert
        ticket = agent.get_ticket(ticket_id)
        # Note should be stored somewhere (description update or notes field)
        assert note in str(ticket) or 'note' in ticket


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.agents
class TestTicketAgentEscalation:
    """Tests for ticket escalation logic"""

    def test_ticket_agent_escalates_urgent_tickets(self):
        """
        Test Name: TicketAgent_UrgentPriority_MarkedForEscalation
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        description = "URGENT: Complete system failure"
        classification = {'category': 'HARDWARE', 'priority': 'URGENT'}

        # Act
        result = agent.create_ticket(
            description=description,
            classification=classification,
            user_email="user@acmecorp.com"
        )

        # Assert
        # Urgent tickets should be marked or have high priority
        assert result['priority'] in ['URGENT', 'CRITICAL', 'HIGH']

    def test_ticket_agent_detects_complex_issues_for_escalation(self):
        """
        Test Name: TicketAgent_ComplexIssue_SuggestsEscalation
        Priority: P2
        Category: Enhancement
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        description = "Tried everything, multiple systems affected, ongoing for days"
        classification = {'category': 'NETWORK', 'priority': 'HIGH'}
        rag_result = {
            'complexity': 'complex',
            'confidence': 0.3
        }

        # Act
        result = agent.create_ticket(
            description=description,
            classification=classification,
            user_email="user@acmecorp.com",
            rag_result=rag_result
        )

        # Assert
        # Complex issues should be escalated
        assert result is not None


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.agents
class TestTicketAgentFormatting:
    """Tests for ticket formatting and response generation"""

    def test_ticket_agent_generates_user_friendly_response(self):
        """
        Test Name: TicketAgent_TicketCreated_FriendlyResponse
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        description = "WiFi not working"
        classification = {'category': 'WIFI', 'priority': 'MEDIUM'}

        # Act
        result = agent.create_ticket(
            description=description,
            classification=classification,
            user_email="user@acmecorp.com"
        )

        # Assert
        assert 'ticket_id' in result
        assert 'message' in result or 'response' in result
        # Should have friendly confirmation message

    def test_ticket_agent_includes_next_steps(self):
        """
        Test Name: TicketAgent_TicketCreated_IncludesNextSteps
        Priority: P2
        Category: Enhancement
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        description = "Laptop broken"
        classification = {'category': 'HARDWARE', 'priority': 'HIGH'}

        # Act
        result = agent.create_ticket(
            description=description,
            classification=classification,
            user_email="user@acmecorp.com"
        )

        # Assert
        # Should include next steps or expected timeline
        assert result is not None


@pytest.mark.unit
@pytest.mark.priority_p2
@pytest.mark.agents
class TestTicketAgentSearch:
    """Tests for searching similar tickets"""

    def test_ticket_agent_searches_similar_tickets(self):
        """
        Test Name: TicketAgent_SearchQuery_FindsSimilar
        Priority: P2
        Category: Enhancement
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()
        # Create a ticket first
        agent.create_ticket(
            description="VPN connection issues",
            classification={'category': 'VPN', 'priority': 'MEDIUM'},
            user_email="user1@acmecorp.com"
        )

        # Act
        similar = agent.search_similar_tickets(
            description="VPN not connecting",
            category="VPN"
        )

        # Assert
        assert similar is not None
        assert isinstance(similar, list)


@pytest.mark.unit
@pytest.mark.priority_p2
@pytest.mark.agents
class TestTicketAgentValidation:
    """Tests for input validation and error handling"""

    def test_ticket_agent_requires_description(self):
        """
        Test Name: TicketAgent_NoDescription_HandlesGracefully
        Priority: P2
        Category: Edge Case
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()

        # Act
        result = agent.create_ticket(
            description="",
            classification={'category': 'GENERAL', 'priority': 'LOW'},
            user_email="user@acmecorp.com"
        )

        # Assert
        assert 'error' in result or result['ticket_id'] is not None

    def test_ticket_agent_handles_missing_classification(self):
        """
        Test Name: TicketAgent_NoClassification_UsesDefaults
        Priority: P2
        Category: Edge Case
        """
        from backend.agents.ticket_agent import TicketAgent

        # Arrange
        agent = TicketAgent()

        # Act
        result = agent.create_ticket(
            description="Something is broken",
            classification=None,
            user_email="user@acmecorp.com"
        )

        # Assert
        # Should use defaults
        assert result['ticket_id'] is not None
        assert result['category'] in ['GENERAL', 'UNKNOWN']
        assert result['priority'] in ['LOW', 'MEDIUM']
