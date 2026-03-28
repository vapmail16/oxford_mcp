"""
Ticket Agent - Support Ticket Management
Implemented following TDD - all tests in test_agents_ticket.py should pass
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class TicketAgent:
    """
    Ticket Agent creates and manages support tickets.

    Responsibilities:
    - Create tickets from issue descriptions
    - Extract concise titles from descriptions
    - Set appropriate priority levels
    - Update ticket status
    - Search for similar tickets
    - Format user-friendly responses
    """

    # Valid ticket statuses
    VALID_STATUSES = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']

    # Priority mapping
    PRIORITY_MAP = {
        'LOW': 'LOW',
        'MEDIUM': 'MEDIUM',
        'HIGH': 'HIGH',
        'URGENT': 'CRITICAL'
    }

    def __init__(self, model: str = None):
        """Initialize ticket agent with LLM and database"""
        self.llm = ChatOpenAI(
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3  # Lower temperature for consistent title extraction
        )

        # Title extraction prompt
        self.title_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are extracting a concise ticket title from a description.

RULES:
- Title should be 5-10 words maximum
- Include the key issue and category
- Be specific but concise
- No punctuation at end
- Actionable and clear

Examples:
Description: "My laptop won't turn on at all, tried everything"
Title: "Laptop Not Turning On"

Description: "VPN error 422 when connecting from home"
Title: "VPN Error 422 Connection Issue"

Return ONLY the title, nothing else."""),
            ("human", "Description: {description}\nTitle:")
        ])

    def _get_db_session(self):
        """Get database session"""
        from backend.database.models import SessionLocal
        return SessionLocal()

    def extract_title(self, description: str) -> str:
        """
        Extract a concise title from issue description.

        Args:
            description: Full issue description

        Returns:
            Concise title (5-10 words)
        """
        if not description or len(description.strip()) == 0:
            return "Support Request"

        try:
            chain = self.title_prompt | self.llm
            response = chain.invoke({"description": description})
            title = response.content.strip()

            # Ensure it's not too long
            if len(title) > 100:
                title = title[:97] + "..."

            return title

        except Exception as e:
            print(f"Title extraction failed: {e}, using fallback")
            # Fallback: use first 50 chars of description
            return description[:50].strip() + ("..." if len(description) > 50 else "")

    def create_ticket(
        self,
        description: str,
        classification: Optional[Dict[str, Any]] = None,
        user_email: str = "unknown@oxforduniversity.com",
        rag_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a support ticket.

        Args:
            description: Issue description
            classification: Optional triage classification
            user_email: User's email
            rag_result: Optional RAG agent result

        Returns:
            Dict with ticket_id, status, title, priority, category, message
        """
        # Handle empty description
        if not description or len(description.strip()) == 0:
            return {
                'error': 'Description is required',
                'ticket_id': None
            }

        # Use defaults if no classification
        if not classification:
            classification = {
                'category': 'GENERAL',
                'priority': 'MEDIUM'
            }

        # Extract title
        title = self.extract_title(description)

        # Map priority
        priority = classification.get('priority', 'MEDIUM')
        mapped_priority = self.PRIORITY_MAP.get(priority, 'MEDIUM')

        # Get category
        category = classification.get('category', 'GENERAL')

        # Map category to database enum values
        category_map = {
            'VPN': 'NETWORK',
            'PASSWORD': 'PASSWORD',
            'WIFI': 'NETWORK',
            'LAPTOP': 'HARDWARE',
            'SOFTWARE': 'SOFTWARE',
            'EMAIL': 'SOFTWARE',
            'HARDWARE': 'HARDWARE',
            'GENERAL': 'UNKNOWN'
        }
        db_category = category_map.get(category, 'UNKNOWN')

        # Create ticket in database
        db = self._get_db_session()
        try:
            from backend.database.crud import create_ticket as db_create_ticket

            ticket = db_create_ticket(
                db=db,
                title=title,
                description=description,
                category=db_category,
                priority=mapped_priority,
                user_email=user_email
            )

            # Generate user-friendly message
            message = self._generate_confirmation_message(
                ticket_id=ticket.id,
                title=title,
                priority=mapped_priority,
                category=category
            )

            return {
                'ticket_id': ticket.id,
                'status': ticket.status.value if hasattr(ticket.status, 'value') else ticket.status,
                'title': ticket.title,
                'priority': ticket.priority.value if hasattr(ticket.priority, 'value') else ticket.priority,
                'category': category,  # Return original triage category, not DB enum
                'message': message,
                'response': message  # Alias for compatibility
            }

        except Exception as e:
            print(f"Ticket creation failed: {e}")
            return {
                'error': f'Failed to create ticket: {str(e)}',
                'ticket_id': None
            }
        finally:
            db.close()

    def get_ticket(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a ticket by ID.

        Args:
            ticket_id: Ticket ID

        Returns:
            Ticket details or None
        """
        db = self._get_db_session()
        try:
            from backend.database.crud import get_ticket as db_get_ticket

            ticket = db_get_ticket(db=db, ticket_id=ticket_id)

            if not ticket:
                return None

            return {
                'id': ticket.id,
                'title': ticket.title,
                'description': ticket.description,
                'status': ticket.status.value if hasattr(ticket.status, 'value') else ticket.status,
                'priority': ticket.priority.value if hasattr(ticket.priority, 'value') else ticket.priority,
                'category': ticket.category.value if hasattr(ticket.category, 'value') else ticket.category,
                'user_email': ticket.user_email,
                'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None
            }

        except Exception as e:
            print(f"Ticket retrieval failed: {e}")
            return {'error': str(e)}
        finally:
            db.close()

    def update_ticket(
        self,
        ticket_id: int,
        status: Optional[str] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a ticket's status or add a note.

        Args:
            ticket_id: Ticket ID
            status: New status (OPEN, IN_PROGRESS, RESOLVED, CLOSED)
            note: Optional note to append to description

        Returns:
            Success status
        """
        db = self._get_db_session()
        try:
            from backend.database.crud import get_ticket as db_get_ticket, update_ticket_status

            ticket = db_get_ticket(db=db, ticket_id=ticket_id)

            if not ticket:
                return {'success': False, 'error': 'Ticket not found'}

            # Update status if provided
            if status and status in self.VALID_STATUSES:
                update_ticket_status(db=db, ticket_id=ticket_id, status=status)

            # Append note to description if provided
            if note:
                new_description = f"{ticket.description}\n\n--- Update ---\n{note}"
                # Update description (would need CRUD function, for now just update status)
                ticket.description = new_description
                db.commit()

            return {'success': True}

        except Exception as e:
            print(f"Ticket update failed: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def search_similar_tickets(
        self,
        description: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar tickets.

        Args:
            description: Issue description
            category: Optional category filter

        Returns:
            List of similar tickets
        """
        db = self._get_db_session()
        try:
            from backend.database.crud import get_all_tickets

            # Get all tickets (in production, this would use vector search or full-text search)
            tickets = get_all_tickets(db=db, limit=10)

            # Simple filtering by category
            if category:
                tickets = [t for t in tickets if t.category == category]

            # Convert to dict
            similar = []
            for ticket in tickets:
                similar.append({
                    'id': ticket.id,
                    'title': ticket.title,
                    'category': ticket.category.value if hasattr(ticket.category, 'value') else ticket.category,
                    'status': ticket.status.value if hasattr(ticket.status, 'value') else ticket.status
                })

            return similar

        except Exception as e:
            print(f"Similar ticket search failed: {e}")
            return []
        finally:
            db.close()

    def _generate_confirmation_message(
        self,
        ticket_id: int,
        title: str,
        priority: str,
        category: str
    ) -> str:
        """
        Generate user-friendly confirmation message.

        Args:
            ticket_id: Ticket ID
            title: Ticket title
            priority: Priority level
            category: Issue category

        Returns:
            Confirmation message
        """
        priority_messages = {
            'CRITICAL': "This is marked as CRITICAL priority and will be addressed immediately.",
            'HIGH': "This has been marked as HIGH priority.",
            'MEDIUM': "This has been logged with MEDIUM priority.",
            'LOW': "This has been logged and will be addressed soon."
        }

        priority_msg = priority_messages.get(priority, "")

        message = f"""I've created a support ticket for you:

**Ticket #{ticket_id}**: {title}
**Category**: {category}
**Priority**: {priority}

{priority_msg}

**Next Steps**:
- Our IT team will review your ticket shortly
- You'll receive email updates at your registered address
- Expected response time: {"< 1 hour" if priority in ["CRITICAL", "HIGH"] else "< 4 hours"}

Is there anything else I can help you with?"""

        return message


if __name__ == "__main__":
    """Test ticket agent"""
    agent = TicketAgent()

    # Test ticket creation
    print("=" * 60)
    print("Ticket Agent Test")
    print("=" * 60)

    result1 = agent.create_ticket(
        description="My laptop won't turn on at all",
        classification={'category': 'HARDWARE', 'priority': 'HIGH'},
        user_email="test@oxforduniversity.com"
    )

    print(f"\n✓ Created ticket #{result1['ticket_id']}")
    print(f"  Title: {result1['title']}")
    print(f"  Priority: {result1['priority']}")
    print(f"  Status: {result1['status']}")

    # Test ticket retrieval
    ticket = agent.get_ticket(result1['ticket_id'])
    print(f"\n✓ Retrieved ticket #{ticket['id']}")
    print(f"  Status: {ticket['status']}")

    # Test ticket update
    update = agent.update_ticket(result1['ticket_id'], status="IN_PROGRESS", note="Working on it")
    print(f"\n✓ Updated ticket: {update['success']}")
