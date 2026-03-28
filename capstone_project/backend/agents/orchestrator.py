"""
LangGraph Orchestrator - Multi-Agent Coordination
Implements the state machine for coordinating all agents
"""

import os
from typing import Dict, List, Optional, Any, TypedDict
from datetime import datetime

# Import all agents
from backend.agents.triage import TriageAgent
from backend.agents.rag_agent import RAGAgent
from backend.agents.ticket_agent import TicketAgent
from backend.agents.response_agent import ResponseAgent
from backend.agents.action_agent import ActionAgent


class AgentState(TypedDict, total=False):
    """
    Shared state across all agents in the workflow.
    This gets passed between agents and updated at each step.
    """
    # Input
    user_message: str
    session_id: str
    user_email: str

    # Triage outputs
    intent: str
    category: str
    priority: str
    confidence: float

    # RAG outputs
    rag_answer: str
    rag_confidence: float
    sources: List[str]
    needs_ticket: bool
    complexity: str

    # Ticket outputs
    ticket_id: Optional[int]
    ticket_status: Optional[str]
    ticket_title: Optional[str]

    # Action outputs (for future MCP integration)
    action_result: Optional[Dict[str, Any]]

    # Final response
    final_response: str
    next_steps: List[str]

    # Metadata
    agent_path: List[str]  # Track which agents were called
    errors: List[str]


class Orchestrator:
    """
    Orchestrator coordinates all agents in the multi-agent workflow.

    Workflow:
    1. Triage Agent → Classify intent and route
    2. RAG Agent → Answer questions (if QUESTION intent)
    3. Ticket Agent → Create tickets (if needed)
    4. Action Agent → Execute actions (if ACTION_REQUEST intent)
    5. Response Agent → Format final response

    This uses a simplified state machine approach (not full LangGraph yet).
    Full LangGraph integration would use StateGraph, conditional edges, etc.
    """

    def __init__(self):
        """Initialize orchestrator with all agents"""
        self.triage_agent = TriageAgent()
        self.rag_agent = RAGAgent()
        self.ticket_agent = TicketAgent()
        self.action_agent = ActionAgent()
        self.response_agent = ResponseAgent()

    def process_query(
        self,
        message: str,
        user_email: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a user query through the multi-agent workflow.

        Args:
            message: User's message
            user_email: User's email address
            session_id: Optional session ID for conversation continuity
            conversation_history: Optional conversation history

        Returns:
            Dict with final response and metadata
        """
        # Initialize state
        state: AgentState = {
            'user_message': message,
            'user_email': user_email,
            'session_id': session_id or f"session-{datetime.utcnow().timestamp()}",
            'agent_path': [],
            'errors': []
        }

        try:
            # Step 1: Triage - Classify intent and route
            state = self._run_triage(state, conversation_history)

            # Step 2: Route based on intent
            intent = state.get('intent', 'QUESTION')

            if intent == 'GREETING':
                # Direct response for greetings
                state = self._handle_greeting(state)

            elif intent == 'QUESTION':
                # RAG workflow
                state = self._run_rag(state)

                # Check if ticket needed based on RAG confidence
                if state.get('needs_ticket', False):
                    state = self._run_ticket_agent(state)

            elif intent == 'TICKET_CREATE':
                # Direct ticket creation
                state = self._run_ticket_agent(state)

            elif intent == 'ACTION_REQUEST':
                # Action workflow (placeholder for MCP integration)
                state = self._handle_action_request(state)

            else:
                # Unknown intent - treat as question
                state = self._run_rag(state)

            # Step 3: Format final response
            state = self._run_response_agent(state)

            # Return result
            return {
                'response': state.get('final_response', 'I apologize, but I encountered an issue processing your request.'),
                'session_id': state['session_id'],
                'sources': state.get('sources', []),
                'next_steps': state.get('next_steps', []),
                'agent_path': state['agent_path'],
                'ticket_id': state.get('ticket_id'),
                'intent': state.get('intent'),
                'category': state.get('category'),
                'priority': state.get('priority')
            }

        except Exception as e:
            # Error handling
            error_msg = f"Orchestration error: {str(e)}"
            state['errors'].append(error_msg)

            return {
                'response': "I apologize, but I encountered an error processing your request. Would you like me to create a support ticket for you?",
                'session_id': state.get('session_id', ''),
                'error': error_msg,
                'agent_path': state.get('agent_path', [])
            }

    def _run_triage(
        self,
        state: AgentState,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AgentState:
        """Run triage agent"""
        state['agent_path'].append('triage')

        try:
            classification = self.triage_agent.classify_intent(
                query=state['user_message'],
                conversation_history=conversation_history
            )

            state['intent'] = classification['intent']
            state['category'] = classification['category']
            state['priority'] = classification['priority']
            state['confidence'] = classification.get('confidence', 0.0)

        except Exception as e:
            state['errors'].append(f"Triage error: {str(e)}")
            # Default fallback
            state['intent'] = 'QUESTION'
            state['category'] = 'GENERAL'
            state['priority'] = 'MEDIUM'

        return state

    def _run_rag(self, state: AgentState) -> AgentState:
        """Run RAG agent"""
        state['agent_path'].append('rag')

        try:
            classification = {
                'intent': state.get('intent'),
                'category': state.get('category'),
                'priority': state.get('priority')
            }

            rag_result = self.rag_agent.answer_query(
                query=state['user_message'],
                classification=classification
            )

            state['rag_answer'] = rag_result['answer']
            state['rag_confidence'] = rag_result['confidence']
            state['sources'] = rag_result['sources']
            state['needs_ticket'] = rag_result['needs_ticket']
            state['complexity'] = rag_result.get('complexity', 'simple')

        except Exception as e:
            state['errors'].append(f"RAG error: {str(e)}")
            state['rag_answer'] = "I couldn't find relevant information in the knowledge base."
            state['rag_confidence'] = 0.0
            state['sources'] = []
            state['needs_ticket'] = True  # Error → create ticket

        return state

    def _run_ticket_agent(self, state: AgentState) -> AgentState:
        """Run ticket agent"""
        state['agent_path'].append('ticket')

        try:
            classification = {
                'category': state.get('category', 'GENERAL'),
                'priority': state.get('priority', 'MEDIUM')
            }

            rag_result = {
                'confidence': state.get('rag_confidence', 0.0),
                'complexity': state.get('complexity', 'moderate')
            }

            ticket_result = self.ticket_agent.create_ticket(
                description=state['user_message'],
                classification=classification,
                user_email=state['user_email'],
                rag_result=rag_result
            )

            state['ticket_id'] = ticket_result.get('ticket_id')
            state['ticket_status'] = ticket_result.get('status')
            state['ticket_title'] = ticket_result.get('title')

        except Exception as e:
            state['errors'].append(f"Ticket error: {str(e)}")
            state['ticket_id'] = None

        return state

    def _run_response_agent(self, state: AgentState) -> AgentState:
        """Run response agent"""
        state['agent_path'].append('response')

        try:
            # Prepare inputs for response agent
            rag_result = None
            if 'rag_answer' in state:
                rag_result = {
                    'answer': state['rag_answer'],
                    'confidence': state['rag_confidence'],
                    'sources': state.get('sources', []),
                    'needs_ticket': state.get('needs_ticket', False)
                }

            ticket_result = None
            if state.get('ticket_id'):
                ticket_result = {
                    'ticket_id': state['ticket_id'],
                    'status': state.get('ticket_status'),
                    'title': state.get('ticket_title')
                }

            classification = {
                'intent': state.get('intent'),
                'category': state.get('category'),
                'priority': state.get('priority')
            }

            response = self.response_agent.format_response(
                rag_result=rag_result,
                ticket_result=ticket_result,
                classification=classification
            )

            state['final_response'] = response['response']
            state['next_steps'] = response.get('next_steps', [])

            # Update sources if not already set
            if 'sources' not in state:
                state['sources'] = response.get('sources', [])

        except Exception as e:
            state['errors'].append(f"Response error: {str(e)}")
            state['final_response'] = "I apologize, but I encountered an error formatting the response."

        return state

    def _handle_greeting(self, state: AgentState) -> AgentState:
        """Handle greeting intent"""
        state['agent_path'].append('greeting')

        try:
            classification = {
                'intent': 'GREETING'
            }

            response = self.response_agent.format_greeting_response(classification)

            state['final_response'] = response['response']
            state['next_steps'] = response.get('next_steps', [])
            state['sources'] = []

        except Exception as e:
            state['errors'].append(f"Greeting error: {str(e)}")
            state['final_response'] = "Hello! How can I help you today?"

        return state

    def _handle_action_request(self, state: AgentState) -> AgentState:
        """Handle action request intent (MCP integration)"""
        state['agent_path'].append('action')

        try:
            classification = {
                'intent': state.get('intent'),
                'category': state.get('category'),
                'priority': state.get('priority')
            }

            action_result = self.action_agent.execute_action(
                request=state['user_message'],
                user_email=state['user_email'],
                classification=classification
            )

            state['action_result'] = action_result

            # If action failed, create a ticket
            if not action_result.get('success'):
                state = self._run_ticket_agent(state)

        except Exception as e:
            state['errors'].append(f"Action error: {str(e)}")
            state['action_result'] = {
                'success': False,
                'message': "Action execution failed. Creating a support ticket instead."
            }
            # Fallback to ticket creation
            state = self._run_ticket_agent(state)

        return state


if __name__ == "__main__":
    """Test orchestrator"""
    orchestrator = Orchestrator()

    print("=" * 60)
    print("Orchestrator Test")
    print("=" * 60)

    # Test 1: Simple question
    result1 = orchestrator.process_query(
        message="How do I reset my password?",
        user_email="test@oxforduniversity.com"
    )

    print("\n✓ Test 1: Simple Question")
    print(f"Intent: {result1['intent']}")
    print(f"Agent Path: {' → '.join(result1['agent_path'])}")
    print(f"Response: {result1['response'][:100]}...")
    print(f"Sources: {len(result1['sources'])} documents")

    # Test 2: Complex issue (should create ticket)
    result2 = orchestrator.process_query(
        message="My laptop won't turn on at all",
        user_email="test@oxforduniversity.com"
    )

    print("\n✓ Test 2: Complex Issue")
    print(f"Intent: {result2['intent']}")
    print(f"Agent Path: {' → '.join(result2['agent_path'])}")
    print(f"Ticket Created: {result2.get('ticket_id') is not None}")
    if result2.get('ticket_id'):
        print(f"Ticket ID: {result2['ticket_id']}")

    # Test 3: Greeting
    result3 = orchestrator.process_query(
        message="Hello",
        user_email="test@oxforduniversity.com"
    )

    print("\n✓ Test 3: Greeting")
    print(f"Intent: {result3['intent']}")
    print(f"Agent Path: {' → '.join(result3['agent_path'])}")
    print(f"Response: {result3['response'][:80]}...")

    print("\n" + "=" * 60)
    print("Orchestrator working successfully!")
    print("=" * 60)
