"""
Triage Agent - Intent Classification and Routing
Implemented following TDD - all tests in test_agents_triage.py should pass
"""

import os
import re
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class TriageAgent:
    """
    Triage Agent classifies user intent and routes to appropriate specialist agent.

    Responsibilities:
    - Classify intent (QUESTION, TICKET_CREATE, ACTION_REQUEST, GREETING)
    - Extract category (VPN, PASSWORD, WIFI, LAPTOP, GENERAL)
    - Determine priority (LOW, MEDIUM, HIGH, URGENT)
    - Provide routing decision
    """

    # Intent categories
    INTENTS = {
        'GREETING': ['hello', 'hi', 'hey', 'good morning', 'good afternoon'],  # Check greetings first
        'TICKET_CREATE': ['create ticket', 'open ticket', 'escalate'],  # Explicit ticket requests only
        'ACTION_REQUEST': ['check', 'verify', 'test', 'can you check', 'can you verify'],
        'QUESTION': ['how', 'what', 'why', 'when', 'where', '?', 'explain', 'help me', 'need help']
    }

    # Issue categories
    CATEGORIES = {
        'VPN': ['vpn', 'anyconnect', 'cisco', 'remote access', 'error 422', 'error 412'],
        'PASSWORD': ['password', 'reset password', 'forgot password', 'locked out', 'credentials'],
        'WIFI': ['wifi', 'wi-fi', 'wireless', 'connection slow', 'network'],
        'LAPTOP': ['laptop', 'computer', 'pc', 'mac', 'setup', 'new device'],
        'SOFTWARE': ['install', 'software', 'application', 'program', 'office'],
        'EMAIL': ['email', 'outlook', 'mail', 'inbox'],
        'HARDWARE': ['printer', 'monitor', 'keyboard', 'mouse', 'hardware']
    }

    # Priority keywords
    PRIORITY_HIGH = ['urgent', 'asap', 'critical', 'down', 'broken', 'not working', 'can\'t work']
    PRIORITY_LOW = ['when you can', 'no rush', 'whenever', 'curious']

    def __init__(self, model: str = None):
        """Initialize triage agent with LLM"""
        self.llm = ChatOpenAI(
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3  # Lower temperature for more consistent classification
        )

        # Create classification prompt
        self.classification_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a triage agent for IT support. Classify the user's query.

Categories:
- QUESTION: User asking how to do something, reporting an error, or requesting information (default for most queries)
- TICKET_CREATE: User EXPLICITLY requesting ticket creation with EXACT phrases like "create ticket", "open ticket", "escalate"
- ACTION_REQUEST: User asking to check/verify/test something with phrases like "can you check", "verify", "test"
- GREETING: Simple greeting like "hello", "hi", "hey" - even if followed by "I need help"

Issue Categories:
- VPN: VPN connection, Cisco AnyConnect, remote access
- PASSWORD: Password reset, locked accounts, credentials
- WIFI: WiFi, wireless, network connectivity
- LAPTOP: Laptop setup, new computer, hardware
- SOFTWARE: Software installation, applications
- EMAIL: Email, Outlook issues
- HARDWARE: Printers, monitors, peripherals
- GENERAL: Other IT issues

Priority:
- URGENT: Cannot work, critical system down
- HIGH: Affecting productivity
- MEDIUM: Normal requests
- LOW: Non-urgent questions

Respond ONLY with JSON:
{{
  "intent": "QUESTION|TICKET_CREATE|ACTION_REQUEST|GREETING",
  "category": "VPN|PASSWORD|WIFI|LAPTOP|SOFTWARE|EMAIL|HARDWARE|GENERAL",
  "priority": "LOW|MEDIUM|HIGH|URGENT",
  "confidence": 0.0-1.0
}}"""),
            ("human", "{query}")
        ])

    def classify_intent(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Classify user intent and extract metadata.

        Args:
            query: User message
            conversation_history: Optional conversation context

        Returns:
            Dict with intent, category, priority, confidence
        """
        # Build context-aware query
        if conversation_history:
            # Add recent context to query
            context = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in conversation_history[-3:]  # Last 3 messages
            ])
            full_query = f"Context:\n{context}\n\nCurrent query: {query}"
        else:
            full_query = query

        # Use LLM for classification
        try:
            chain = self.classification_prompt | self.llm
            response = chain.invoke({"query": full_query})

            # Parse JSON response
            import json
            # Extract JSON from response
            content = response.content
            # Find JSON block
            if '{' in content and '}' in content:
                json_start = content.index('{')
                json_end = content.rindex('}') + 1
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
            else:
                # Fallback to rule-based
                result = self._rule_based_classification(query)

        except Exception as e:
            print(f"LLM classification failed: {e}, using rule-based fallback")
            result = self._rule_based_classification(query)

        return result

    def _rule_based_classification(self, query: str) -> Dict[str, Any]:
        """
        Fallback rule-based classification.

        Args:
            query: User message

        Returns:
            Dict with intent, category, priority
        """
        query_lower = query.lower()

        # Classify intent
        intent = 'QUESTION'  # Default
        for intent_type, keywords in self.INTENTS.items():
            if any(keyword in query_lower for keyword in keywords):
                intent = intent_type
                break

        # Extract category
        category = 'GENERAL'  # Default
        for cat, keywords in self.CATEGORIES.items():
            if any(keyword in query_lower for keyword in keywords):
                category = cat
                break

        # Determine priority
        if any(keyword in query_lower for keyword in self.PRIORITY_HIGH):
            priority = 'HIGH' if 'urgent' in query_lower else 'URGENT'
        elif any(keyword in query_lower for keyword in self.PRIORITY_LOW):
            priority = 'LOW'
        else:
            priority = 'MEDIUM'

        # Adjust based on intent
        if intent == 'TICKET_CREATE':
            # Ticket requests get elevated priority
            if priority == 'LOW':
                priority = 'MEDIUM'
            elif priority == 'MEDIUM':
                priority = 'HIGH'

        return {
            'intent': intent,
            'category': category,
            'priority': priority,
            'confidence': 0.8  # Rule-based confidence
        }

    def get_routing_decision(self, classification: Dict[str, Any]) -> str:
        """
        Determine which agent to route to based on classification.

        Args:
            classification: Result from classify_intent()

        Returns:
            Agent name ('rag', 'ticket', 'action', 'end')
        """
        intent = classification['intent']

        routing_map = {
            'QUESTION': 'rag',
            'TICKET_CREATE': 'ticket',
            'ACTION_REQUEST': 'action',
            'GREETING': 'end'  # Handle greetings directly, no agent needed
        }

        return routing_map.get(intent, 'rag')  # Default to RAG for questions

    def format_response_for_greeting(self, query: str) -> str:
        """
        Generate a friendly greeting response.

        Args:
            query: User greeting

        Returns:
            Greeting response
        """
        return """Hello! I'm the Oxford University IT Support Agent. I can help you with:

• VPN connection issues
• Password resets
• WiFi troubleshooting
• Laptop setup
• Software installation
• And more IT support needs

How can I assist you today?"""

    def should_escalate_to_ticket(
        self,
        classification: Dict[str, Any],
        rag_confidence: Optional[float] = None
    ) -> bool:
        """
        Determine if query should create a ticket.

        Args:
            classification: Triage classification
            rag_confidence: Optional confidence from RAG agent

        Returns:
            True if should create ticket
        """
        # Explicit ticket request
        if classification['intent'] == 'TICKET_CREATE':
            return True

        # High/urgent priority and low RAG confidence
        if classification['priority'] in ['HIGH', 'URGENT']:
            if rag_confidence and rag_confidence < 0.6:
                return True

        return False


if __name__ == "__main__":
    """Test triage agent"""
    agent = TriageAgent()

    test_queries = [
        "VPN error 422, how do I fix it?",
        "Please create a ticket for my broken laptop",
        "Can you check if the email server is working?",
        "Hello, I need some help",
        "WiFi is very slow",
        "URGENT: Can't access VPN, can't work!"
    ]

    print("=" * 60)
    print("Triage Agent Test")
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = agent.classify_intent(query)
        route = agent.get_routing_decision(result)
        print(f"  Intent: {result['intent']}")
        print(f"  Category: {result['category']}")
        print(f"  Priority: {result['priority']}")
        print(f"  Route: {route}")
        print(f"  Confidence: {result['confidence']}")
