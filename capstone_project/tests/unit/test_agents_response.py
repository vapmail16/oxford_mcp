"""
Unit tests for Response Agent
RED PHASE - These tests will fail until we implement response_agent.py

Test Priority: P0-P1 (Critical for user-facing responses)
Category: Unit, Agents
"""

import pytest
from typing import Dict, Any


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestResponseAgentFormatting:
    """Tests for response formatting"""

    def test_response_agent_formats_rag_only_response(self):
        """
        Test Name: ResponseAgent_RAGOnly_FormatsCorrectly
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        rag_result = {
            'answer': "To reset your password: 1. Go to portal...",
            'confidence': 0.85,
            'sources': ['password_reset_sop.md'],
            'needs_ticket': False
        }

        # Act
        result = agent.format_response(rag_result=rag_result)

        # Assert
        assert 'response' in result
        assert len(result['response']) > 0
        assert 'password' in result['response'].lower()

    def test_response_agent_formats_rag_plus_ticket_response(self):
        """
        Test Name: ResponseAgent_RAGPlusTicket_CombinesBoth
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        rag_result = {
            'answer': "Try these VPN fixes...",
            'confidence': 0.45,
            'needs_ticket': True
        }
        ticket_result = {
            'ticket_id': 1234,
            'status': 'OPEN',
            'title': 'VPN Connection Issue'
        }

        # Act
        result = agent.format_response(
            rag_result=rag_result,
            ticket_result=ticket_result
        )

        # Assert
        assert 'response' in result
        assert '1234' in result['response']  # Ticket ID mentioned
        assert 'VPN' in result['response']

    def test_response_agent_formats_ticket_only_response(self):
        """
        Test Name: ResponseAgent_TicketOnly_FormatsCorrectly
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        ticket_result = {
            'ticket_id': 5678,
            'status': 'OPEN',
            'title': 'Laptop Hardware Failure',
            'message': "I've created a support ticket..."
        }

        # Act
        result = agent.format_response(ticket_result=ticket_result)

        # Assert
        assert 'response' in result
        assert '5678' in result['response']


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestResponseAgentSources:
    """Tests for source attribution"""

    def test_response_agent_includes_sources(self):
        """
        Test Name: ResponseAgent_WithSources_IncludesThem
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        rag_result = {
            'answer': "VPN setup instructions...",
            'confidence': 0.9,
            'sources': ['vpn_setup_guide.md', 'network_policies.md']
        }

        # Act
        result = agent.format_response(rag_result=rag_result)

        # Assert
        assert 'sources' in result
        assert len(result['sources']) > 0
        assert 'vpn_setup_guide.md' in result['sources']

    def test_response_agent_no_sources_when_ticket_only(self):
        """
        Test Name: ResponseAgent_TicketOnly_NoSources
        Priority: P1
        Category: Edge Case
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        ticket_result = {
            'ticket_id': 9999,
            'status': 'OPEN'
        }

        # Act
        result = agent.format_response(ticket_result=ticket_result)

        # Assert
        assert 'sources' in result
        assert len(result['sources']) == 0


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.agents
class TestResponseAgentNextSteps:
    """Tests for next steps suggestions"""

    def test_response_agent_includes_next_steps(self):
        """
        Test Name: ResponseAgent_FormatsResponse_IncludesNextSteps
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        rag_result = {
            'answer': "Password reset steps...",
            'confidence': 0.8
        }

        # Act
        result = agent.format_response(rag_result=rag_result)

        # Assert
        assert 'next_steps' in result or 'follow' in result['response'].lower()

    def test_response_agent_next_steps_for_ticket(self):
        """
        Test Name: ResponseAgent_TicketCreated_IncludesNextSteps
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        ticket_result = {
            'ticket_id': 1111,
            'status': 'OPEN',
            'priority': 'HIGH'
        }

        # Act
        result = agent.format_response(ticket_result=ticket_result)

        # Assert
        # Should mention what happens next
        assert 'team' in result['response'].lower() or 'contact' in result['response'].lower()


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.agents
class TestResponseAgentQuality:
    """Tests for response quality checks"""

    def test_response_agent_professional_tone(self):
        """
        Test Name: ResponseAgent_Response_ProfessionalTone
        Priority: P1
        Category: Quality
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        rag_result = {
            'answer': "Reset password by going to portal",
            'confidence': 0.75
        }

        # Act
        result = agent.format_response(rag_result=rag_result)

        # Assert
        # Should be friendly but professional
        response_lower = result['response'].lower()
        # Should have helpful phrases
        assert any(word in response_lower for word in ['help', 'assist', 'support', 'can'])

    def test_response_agent_actionable_response(self):
        """
        Test Name: ResponseAgent_Response_Actionable
        Priority: P2
        Category: Quality
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        rag_result = {
            'answer': "1. Open VPN client 2. Enter credentials 3. Connect",
            'confidence': 0.9
        }

        # Act
        result = agent.format_response(rag_result=rag_result)

        # Assert
        assert result['response'] is not None
        assert len(result['response']) > 20  # Substantial response


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.agents
class TestResponseAgentClassification:
    """Tests for classification metadata usage"""

    def test_response_agent_uses_classification_metadata(self):
        """
        Test Name: ResponseAgent_WithClassification_UsesMetadata
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        classification = {
            'intent': 'QUESTION',
            'category': 'VPN',
            'priority': 'HIGH'
        }
        rag_result = {
            'answer': "VPN troubleshooting steps...",
            'confidence': 0.7
        }

        # Act
        result = agent.format_response(
            rag_result=rag_result,
            classification=classification
        )

        # Assert
        assert result is not None
        assert 'response' in result


@pytest.mark.unit
@pytest.mark.priority_p2
@pytest.mark.agents
class TestResponseAgentGreeting:
    """Tests for greeting responses"""

    def test_response_agent_handles_greeting(self):
        """
        Test Name: ResponseAgent_Greeting_FriendlyResponse
        Priority: P2
        Category: Happy Path
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        classification = {
            'intent': 'GREETING'
        }

        # Act
        result = agent.format_greeting_response(classification)

        # Assert
        assert 'response' in result
        assert len(result['response']) > 0
        response_lower = result['response'].lower()
        assert any(word in response_lower for word in ['hello', 'hi', 'help'])


@pytest.mark.unit
@pytest.mark.priority_p2
@pytest.mark.agents
class TestResponseAgentError:
    """Tests for error handling"""

    def test_response_agent_handles_empty_input(self):
        """
        Test Name: ResponseAgent_EmptyInput_HandlesGracefully
        Priority: P2
        Category: Edge Case
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()

        # Act
        result = agent.format_response()

        # Assert
        assert 'response' in result or 'error' in result

    def test_response_agent_handles_low_confidence_no_ticket(self):
        """
        Test Name: ResponseAgent_LowConfidenceNoTicket_SuggestsHelp
        Priority: P2
        Category: Edge Case
        """
        from backend.agents.response_agent import ResponseAgent

        # Arrange
        agent = ResponseAgent()
        rag_result = {
            'answer': "I couldn't find information...",
            'confidence': 0.3,
            'needs_ticket': False  # Somehow no ticket created
        }

        # Act
        result = agent.format_response(rag_result=rag_result)

        # Assert
        assert 'response' in result
        # Should offer to create ticket
        assert any(word in result['response'].lower() for word in ['ticket', 'help', 'assist'])
