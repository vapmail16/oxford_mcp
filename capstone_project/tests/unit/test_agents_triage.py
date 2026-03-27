"""
Unit tests for Triage Agent
RED PHASE - These tests will fail until we implement triage.py

Test Priority: P0-P1 (Critical for agent routing)
Category: Unit, Agents
"""

import pytest
from typing import Dict, Any


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestTriageIntentClassification:
    """Tests for intent classification"""

    def test_triage_vpn_question_classifies_as_question(self):
        """
        Test Name: Triage_VPNQuery_ClassifiesAsQuestion
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "I'm getting VPN error 422, how do I fix it?"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['intent'] == 'QUESTION'
        assert result['category'] == 'VPN'

    def test_triage_ticket_request_classifies_as_ticket_create(self):
        """
        Test Name: Triage_TicketRequest_ClassifiesAsTicketCreate
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "I need help, please create a ticket for VPN issues"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['intent'] == 'TICKET_CREATE'

    def test_triage_action_request_classifies_as_action(self):
        """
        Test Name: Triage_ActionRequest_ClassifiesAsAction
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "Can you check if the VPN server is up?"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['intent'] == 'ACTION_REQUEST'

    def test_triage_greeting_classifies_as_greeting(self):
        """
        Test Name: Triage_Greeting_ClassifiesAsGreeting
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "Hello, I need some help"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['intent'] in ['GREETING', 'QUESTION']


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestTriageCategoryExtraction:
    """Tests for category extraction"""

    def test_triage_extracts_vpn_category(self):
        """
        Test Name: Triage_VPNQuery_ExtractsVPNCategory
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "VPN connection keeps dropping"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['category'] == 'VPN'

    def test_triage_extracts_password_category(self):
        """
        Test Name: Triage_PasswordQuery_ExtractsPasswordCategory
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "I forgot my password and need to reset it"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['category'] == 'PASSWORD'

    def test_triage_extracts_wifi_category(self):
        """
        Test Name: Triage_WiFiQuery_ExtractsWiFiCategory
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "WiFi is very slow in conference room B"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['category'] == 'WIFI'

    def test_triage_unknown_category_defaults_to_general(self):
        """
        Test Name: Triage_UnknownQuery_DefaultsToGeneral
        Priority: P1
        Category: Edge Case
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "Random question about office chairs"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['category'] in ['GENERAL', 'UNKNOWN', 'OTHER']


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.agents
class TestTriagePriorityDetection:
    """Tests for priority determination"""

    def test_triage_urgent_keywords_set_high_priority(self):
        """
        Test Name: Triage_UrgentKeywords_SetsHighPriority
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "URGENT: VPN is down, can't work!"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['priority'] in ['HIGH', 'URGENT']

    def test_triage_normal_query_sets_medium_priority(self):
        """
        Test Name: Triage_NormalQuery_SetsMediumPriority
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "How do I connect to WiFi?"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['priority'] in ['MEDIUM', 'LOW']

    def test_triage_question_mark_indicates_question(self):
        """
        Test Name: Triage_QuestionMark_IndicatesQuestion
        Priority: P2
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "How does VPN setup work?"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['intent'] == 'QUESTION'


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestTriageRouting:
    """Tests for agent routing decisions"""

    def test_triage_question_routes_to_rag(self):
        """
        Test Name: Triage_Question_RoutesToRAG
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "How do I reset my password?"

        # Act
        result = agent.classify_intent(query)
        route = agent.get_routing_decision(result)

        # Assert
        assert route == 'rag'

    def test_triage_ticket_request_routes_to_ticket(self):
        """
        Test Name: Triage_TicketRequest_RoutesToTicket
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "Please create a support ticket"

        # Act
        result = agent.classify_intent(query)
        route = agent.get_routing_decision(result)

        # Assert
        assert route == 'ticket'

    def test_triage_action_request_routes_to_action(self):
        """
        Test Name: Triage_ActionRequest_RoutesToAction
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "Check if VPN server is running"

        # Act
        result = agent.classify_intent(query)
        route = agent.get_routing_decision(result)

        # Assert
        assert route == 'action'


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.agents
class TestTriageWithContext:
    """Tests for triage with conversation context"""

    def test_triage_uses_conversation_context(self):
        """
        Test Name: Triage_WithContext_UsesHistory
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        history = [
            {"role": "user", "content": "I'm having VPN issues"},
            {"role": "assistant", "content": "Let me help with that..."}
        ]
        query = "It's still not working"

        # Act
        result = agent.classify_intent(query, conversation_history=history)

        # Assert
        # Should understand "it" refers to VPN from context
        assert result['category'] == 'VPN'

    def test_triage_standalone_query_works_without_context(self):
        """
        Test Name: Triage_NoContext_WorksStandalone
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.triage import TriageAgent

        # Arrange
        agent = TriageAgent()
        query = "VPN error 422"

        # Act
        result = agent.classify_intent(query)

        # Assert
        assert result['intent'] == 'QUESTION'
        assert result['category'] == 'VPN'
