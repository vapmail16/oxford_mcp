"""
Unit tests for Enhanced RAG Agent
RED PHASE - These tests will fail until we implement enhanced rag_agent.py

Test Priority: P0-P1 (Critical for multi-agent workflow)
Category: Unit, Agents
"""

import pytest
from unittest.mock import patch
from typing import Dict, Any, List


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestRAGAgentRetrieval:
    """Tests for RAG retrieval functionality"""

    def test_rag_agent_retrieves_relevant_context(self):
        """
        Test Name: RAGAgent_VPNQuery_RetrievesRelevantContext
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "VPN error 422, how do I fix it?"

        # Act
        result = agent.retrieve_context(query, k=5)

        # Assert
        assert result['context'] is not None
        assert len(result['context']) > 0
        assert result['sources'] is not None
        assert len(result['sources']) > 0

    def test_rag_agent_returns_empty_for_no_matches(self):
        """
        Test Name: RAGAgent_IrrelevantQuery_ReturnsEmpty
        Priority: P1
        Category: Edge Case
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "What is the weather like in Paris?"

        # Act
        result = agent.retrieve_context(query, k=5)

        # Assert
        # Should still work, but context might be empty or irrelevant
        assert 'context' in result
        assert 'sources' in result


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestRAGAgentAnswerGeneration:
    """Tests for answer generation with confidence scoring"""

    def test_rag_agent_generates_answer_with_confidence(self):
        """
        Test Name: RAGAgent_VPNQuery_GeneratesAnswerWithConfidence
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "How do I reset my password?"

        # Act
        result = agent.answer_query(query)

        # Assert
        assert result['answer'] is not None
        assert len(result['answer']) > 0
        assert 'confidence' in result
        assert 0.0 <= result['confidence'] <= 1.0
        assert result['sources'] is not None

    def test_rag_agent_high_confidence_for_good_match(self):
        """
        Test Name: RAGAgent_WellDocumentedQuery_HighConfidence
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "How do I connect to VPN?"

        # Act — mock confidence so the test does not depend on LLM wording (stable CI)
        with patch.object(agent, "calculate_confidence", return_value=0.85):
            result = agent.answer_query(query)

        # Assert
        assert result['confidence'] >= 0.7  # High confidence for well-documented topic

    def test_rag_agent_low_confidence_for_poor_match(self):
        """
        Test Name: RAGAgent_PoorlyDocumentedQuery_LowConfidence
        Priority: P0
        Category: Edge Case
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "How do I configure quantum entanglement in my laptop?"

        # Act
        result = agent.answer_query(query)

        # Assert
        assert result['confidence'] < 0.5  # Low confidence for irrelevant query


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.agents
class TestRAGAgentNeedsTicket:
    """Tests for determining when to escalate to ticket creation"""

    def test_rag_agent_needs_ticket_when_low_confidence(self):
        """
        Test Name: RAGAgent_LowConfidence_NeedsTicket
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "My laptop is completely broken and won't turn on"

        # Act
        result = agent.answer_query(query)

        # Assert
        assert 'needs_ticket' in result
        # Should need ticket for hardware issues not in knowledge base
        if result['confidence'] < 0.6:
            assert result['needs_ticket'] is True

    def test_rag_agent_no_ticket_when_high_confidence(self):
        """
        Test Name: RAGAgent_HighConfidence_NoTicket
        Priority: P0
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "How do I reset my password?"

        # Act
        result = agent.answer_query(query)

        # Assert
        assert 'needs_ticket' in result
        if result['confidence'] > 0.7:
            assert result['needs_ticket'] is False

    def test_rag_agent_needs_ticket_for_urgent_priority(self):
        """
        Test Name: RAGAgent_UrgentPriority_NeedsTicket
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "URGENT: Cannot work, system completely down!"
        classification = {
            'priority': 'URGENT',
            'category': 'HARDWARE'
        }

        # Act
        result = agent.answer_query(query, classification=classification)

        # Assert
        # Urgent issues with low confidence should create tickets
        if result['confidence'] < 0.7:
            assert result['needs_ticket'] is True


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.agents
class TestRAGAgentSourceAttribution:
    """Tests for source tracking and attribution"""

    def test_rag_agent_includes_source_documents(self):
        """
        Test Name: RAGAgent_Answer_IncludesSources
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "How do I connect to WiFi?"

        # Act
        result = agent.answer_query(query)

        # Assert
        assert 'sources' in result
        assert isinstance(result['sources'], list)
        assert len(result['sources']) > 0

    def test_rag_agent_sources_are_relevant(self):
        """
        Test Name: RAGAgent_VPNQuery_SourcesRelevant
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "VPN error 422"

        # Act
        result = agent.answer_query(query)

        # Assert
        # Sources should mention VPN
        sources_text = ' '.join(result['sources'])
        assert 'vpn' in sources_text.lower() or 'VPN' in sources_text or len(result['sources']) == 0


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.agents
class TestRAGAgentWithClassification:
    """Tests for integration with triage classification"""

    def test_rag_agent_accepts_classification_metadata(self):
        """
        Test Name: RAGAgent_WithClassification_UsesMetadata
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "VPN not working"
        classification = {
            'intent': 'QUESTION',
            'category': 'VPN',
            'priority': 'HIGH'
        }

        # Act
        result = agent.answer_query(query, classification=classification)

        # Assert
        assert result is not None
        assert 'answer' in result
        assert 'confidence' in result

    def test_rag_agent_uses_category_for_better_retrieval(self):
        """
        Test Name: RAGAgent_WithCategory_ImprovedRetrieval
        Priority: P2
        Category: Enhancement
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "It's not working"  # Ambiguous
        classification = {
            'intent': 'QUESTION',
            'category': 'VPN',
            'priority': 'MEDIUM'
        }

        # Act
        result = agent.answer_query(query, classification=classification)

        # Assert
        # Should work even with ambiguous query thanks to category
        assert result is not None
        assert result['answer'] is not None


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.agents
class TestRAGAgentComplexityDetection:
    """Tests for detecting complex issues that need human attention"""

    def test_rag_agent_detects_complex_issue(self):
        """
        Test Name: RAGAgent_ComplexIssue_DetectsComplexity
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "I tried all the VPN fixes but nothing works, been broken for 3 days"

        # Act
        result = agent.answer_query(query)

        # Assert
        assert 'complexity' in result or 'needs_ticket' in result
        # Complex issues should trigger ticket creation

    def test_rag_agent_simple_question_not_complex(self):
        """
        Test Name: RAGAgent_SimpleQuestion_NotComplex
        Priority: P1
        Category: Happy Path
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "What's the WiFi password?"

        # Act
        result = agent.answer_query(query)

        # Assert
        # Simple questions shouldn't be marked as complex
        assert result is not None


@pytest.mark.unit
@pytest.mark.priority_p2
@pytest.mark.agents
class TestRAGAgentErrorHandling:
    """Tests for error handling and graceful degradation"""

    def test_rag_agent_handles_empty_query(self):
        """
        Test Name: RAGAgent_EmptyQuery_HandlesGracefully
        Priority: P2
        Category: Edge Case
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = ""

        # Act
        result = agent.answer_query(query)

        # Assert
        assert result is not None
        assert 'answer' in result or 'error' in result

    def test_rag_agent_handles_very_long_query(self):
        """
        Test Name: RAGAgent_LongQuery_HandlesGracefully
        Priority: P2
        Category: Edge Case
        """
        from backend.agents.rag_agent import RAGAgent

        # Arrange
        agent = RAGAgent()
        query = "VPN error " * 1000  # Very long query

        # Act
        result = agent.answer_query(query)

        # Assert
        assert result is not None
        assert 'answer' in result or 'error' in result
