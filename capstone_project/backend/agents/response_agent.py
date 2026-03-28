"""
Response Agent - Final Response Formatting and Quality Assurance
Implemented following TDD - all tests in test_agents_response.py should pass
"""

import os
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class ResponseAgent:
    """
    Response Agent formats and validates final responses.

    Responsibilities:
    - Combine outputs from multiple agents
    - Format user-friendly responses
    - Include source attribution
    - Add next steps
    - Ensure professional tone
    - Quality assurance checks
    """

    def __init__(self, model: str = None):
        """Initialize response agent with LLM"""
        self.llm = ChatOpenAI(
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7
        )

        # Response formatting prompt
        self.formatting_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are formatting IT support responses for end users.

RULES:
- Be professional but friendly
- Use clear, simple language
- Include specific actions when available
- Be encouraging and helpful
- Keep responses concise

Format the response naturally and helpfully."""),
            ("human", "{content}")
        ])

    def format_response(
        self,
        rag_result: Optional[Dict[str, Any]] = None,
        ticket_result: Optional[Dict[str, Any]] = None,
        action_result: Optional[Dict[str, Any]] = None,
        classification: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format final response combining all agent outputs.

        Args:
            rag_result: Optional RAG agent output
            ticket_result: Optional ticket agent output
            action_result: Optional action agent output
            classification: Optional triage classification

        Returns:
            Dict with formatted response, sources, next_steps
        """
        # Handle empty input
        if not rag_result and not ticket_result and not action_result:
            return {
                'response': "I'm here to help! How can I assist you with your IT issue today?",
                'sources': [],
                'next_steps': []
            }

        # Build response components
        response_parts = []
        sources = []
        next_steps = []

        # Add RAG answer if available
        if rag_result:
            answer = rag_result.get('answer', '')
            if answer:
                response_parts.append(answer)

            # Add sources
            rag_sources = rag_result.get('sources', [])
            if rag_sources:
                sources.extend(rag_sources)

        # Add ticket information if created
        if ticket_result:
            ticket_id = ticket_result.get('ticket_id')
            if ticket_id:
                ticket_message = ticket_result.get('message', '')
                if ticket_message:
                    response_parts.append(f"\n\n{ticket_message}")
                    # Always surface the ticket id when callers pass a short message
                    if str(ticket_id) not in ticket_message:
                        response_parts.append(f"\n\n**Ticket #{ticket_id}**")
                else:
                    # Generate ticket message
                    priority = ticket_result.get('priority', 'MEDIUM')
                    title = ticket_result.get('title', 'Support Request')

                    ticket_msg = f"""I've created a support ticket for you:

**Ticket #{ticket_id}**: {title}
**Priority**: {priority}

Our IT team will review this shortly and contact you with updates."""

                    response_parts.append(f"\n\n{ticket_msg}")

                # Add next steps for ticket
                next_steps.append("Wait for IT team to contact you")
                next_steps.append("Check your email for updates")

        # Add action result if available
        if action_result:
            action_msg = action_result.get('message', '')
            if action_msg:
                response_parts.append(f"\n\n{action_msg}")

        # Combine all parts
        if response_parts:
            combined_response = ''.join(response_parts)
        else:
            combined_response = "I'm working on your request. Is there anything specific I can help clarify?"

        # Add helpful closing
        if not ticket_result:
            combined_response += "\n\nIs there anything else I can help you with?"

        return {
            'response': combined_response.strip(),
            'sources': sources,
            'next_steps': next_steps if next_steps else self._generate_next_steps(rag_result, ticket_result)
        }

    def format_greeting_response(
        self,
        classification: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format a friendly greeting response.

        Args:
            classification: Optional triage classification

        Returns:
            Dict with greeting response
        """
        greeting = """Hello! I'm the Oxford University IT Support Agent. I can help you with:

• VPN connection issues
• Password resets
• WiFi troubleshooting
• Laptop setup
• Software installation
• And more IT support needs

How can I assist you today?"""

        return {
            'response': greeting,
            'sources': [],
            'next_steps': ["Describe your IT issue"]
        }

    def _generate_next_steps(
        self,
        rag_result: Optional[Dict[str, Any]] = None,
        ticket_result: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate suggested next steps.

        Args:
            rag_result: RAG agent output
            ticket_result: Ticket agent output

        Returns:
            List of next step suggestions
        """
        steps = []

        if rag_result:
            confidence = rag_result.get('confidence', 0.0)

            if confidence > 0.7:
                steps.append("Try the suggested solution")
                steps.append("Let me know if you need clarification")
            elif confidence > 0.4:
                steps.append("Try these steps and report back")
                steps.append("Request a ticket if the issue persists")
            else:
                steps.append("A support ticket may be helpful")

        if ticket_result:
            steps.append("Monitor your email for updates")
            steps.append("Reference your ticket number in follow-ups")

        if not steps:
            steps.append("Let me know if you have any questions")

        return steps

    def validate_response_quality(
        self,
        response: str
    ) -> Dict[str, Any]:
        """
        Validate response quality.

        Args:
            response: Generated response

        Returns:
            Dict with quality metrics
        """
        quality_checks = {
            'has_content': len(response) > 20,
            'professional_tone': self._check_professional_tone(response),
            'actionable': self._check_actionable(response),
            'length_appropriate': 50 < len(response) < 2000
        }

        return {
            'passes_quality': all(quality_checks.values()),
            'checks': quality_checks
        }

    def _check_professional_tone(self, response: str) -> bool:
        """Check if response has professional tone"""
        # Simple heuristic: check for helpful phrases
        helpful_indicators = [
            'help', 'assist', 'support', 'guide', 'show',
            'can', 'will', 'here', 'steps', 'follow'
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in helpful_indicators)

    def _check_actionable(self, response: str) -> bool:
        """Check if response is actionable"""
        # Check for action words or numbered steps
        action_indicators = [
            '1.', '2.', 'first', 'next', 'then', 'click',
            'open', 'go to', 'enter', 'select', 'ticket'
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in action_indicators)

    def format_error_response(
        self,
        error: str,
        classification: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format an error response.

        Args:
            error: Error message
            classification: Optional classification

        Returns:
            Dict with error response
        """
        response = f"""I encountered an issue while processing your request:

{error}

Please try rephrasing your question, or I can create a support ticket for you.

Would you like me to create a ticket?"""

        return {
            'response': response,
            'sources': [],
            'next_steps': ["Rephrase your question", "Request a support ticket"],
            'error': error
        }


if __name__ == "__main__":
    """Test response agent"""
    agent = ResponseAgent()

    print("=" * 60)
    print("Response Agent Test")
    print("=" * 60)

    # Test 1: RAG only
    rag_result = {
        'answer': "To reset your password:\n1. Go to portal.acme.com\n2. Click 'Forgot Password'\n3. Enter your email",
        'confidence': 0.85,
        'sources': ['password_reset_sop.md'],
        'needs_ticket': False
    }

    result1 = agent.format_response(rag_result=rag_result)
    print("\n✓ Test 1: RAG Only Response")
    print(f"Response length: {len(result1['response'])}")
    print(f"Sources: {result1['sources']}")
    print(f"Next steps: {len(result1['next_steps'])}")

    # Test 2: RAG + Ticket
    rag_result2 = {
        'answer': "Try these VPN troubleshooting steps: 1. Restart VPN client 2. Check network connection",
        'confidence': 0.45,
        'needs_ticket': True
    }

    ticket_result = {
        'ticket_id': 1234,
        'status': 'OPEN',
        'title': 'VPN Connection Issue',
        'priority': 'HIGH'
    }

    result2 = agent.format_response(rag_result=rag_result2, ticket_result=ticket_result)
    print("\n✓ Test 2: RAG + Ticket Response")
    print(f"Includes ticket ID: {'1234' in result2['response']}")
    print(f"Next steps: {result2['next_steps']}")

    # Test 3: Greeting
    result3 = agent.format_greeting_response()
    print("\n✓ Test 3: Greeting Response")
    print(f"Response length: {len(result3['response'])}")

    # Test 4: Quality validation
    quality = agent.validate_response_quality(result1['response'])
    print("\n✓ Test 4: Quality Validation")
    print(f"Passes quality: {quality['passes_quality']}")
    print(f"Checks: {quality['checks']}")
