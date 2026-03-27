"""
CRUD operations for IT Support Agent database.
Implemented following TDD - all tests in test_database_crud.py should pass.
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import json

from .models import Ticket, Message, TicketStatus, TicketPriority, IssueCategory


# ============================================================================
# TICKET CRUD OPERATIONS
# ============================================================================

def create_ticket(
    db: Session,
    title: str,
    description: str,
    priority: str,
    category: str,
    user_email: str,
    session_id: Optional[str] = None
) -> Ticket:
    """
    Create a new support ticket.

    Args:
        db: Database session
        title: Ticket title
        description: Detailed description
        priority: Priority level (LOW, MEDIUM, HIGH, CRITICAL)
        category: Issue category (PASSWORD, NETWORK, SOFTWARE, HARDWARE, ACCESS, UNKNOWN)
        user_email: User's email address
        session_id: Optional conversation session ID

    Returns:
        Created ticket with ID
    """
    ticket = Ticket(
        title=title,
        description=description,
        priority=TicketPriority[priority.upper()],
        category=IssueCategory[category.upper()],
        user_email=user_email,
        session_id=session_id,
        status=TicketStatus.OPEN
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket(db: Session, ticket_id: int) -> Optional[Ticket]:
    """
    Retrieve a ticket by ID.

    Args:
        db: Database session
        ticket_id: Ticket ID

    Returns:
        Ticket if found, None otherwise
    """
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()


def get_all_tickets(
    db: Session,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
) -> List[Ticket]:
    """
    Retrieve all tickets with optional filtering.

    Args:
        db: Database session
        status: Optional status filter (OPEN, IN_PROGRESS, RESOLVED, CLOSED)
        category: Optional category filter
        limit: Maximum number of tickets to return

    Returns:
        List of tickets
    """
    query = db.query(Ticket)

    if status:
        query = query.filter(Ticket.status == TicketStatus[status.upper()])
    if category:
        query = query.filter(Ticket.category == IssueCategory[category.upper()])

    return query.order_by(Ticket.created_at.desc()).limit(limit).all()


def update_ticket_status(
    db: Session,
    ticket_id: int,
    status: str,
    note: Optional[str] = None
) -> Optional[Ticket]:
    """
    Update ticket status and optionally add a note.

    Args:
        db: Database session
        ticket_id: Ticket ID
        status: New status (OPEN, IN_PROGRESS, RESOLVED, CLOSED)
        note: Optional note to append to ticket notes

    Returns:
        Updated ticket if found, None otherwise
    """
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        return None

    ticket.status = TicketStatus[status.upper()]
    ticket.updated_at = datetime.utcnow()

    if note:
        existing_notes = ticket.notes or ""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ticket.notes = f"{existing_notes}\n[{timestamp}] {note}".strip()

    db.commit()
    db.refresh(ticket)
    return ticket


# ============================================================================
# MESSAGE CRUD OPERATIONS
# ============================================================================

def create_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None
) -> Message:
    """
    Create a new chat message.

    Args:
        db: Database session
        session_id: Conversation session ID
        role: Message role ('user' or 'assistant')
        content: Message content
        metadata: Optional metadata (sources, ticket_id, etc.)

    Returns:
        Created message with ID
    """
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        msg_metadata=json.dumps(metadata) if metadata else None
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_messages_by_session(
    db: Session,
    session_id: str,
    limit: int = 50
) -> List[Message]:
    """
    Retrieve all messages for a session in chronological order.

    Args:
        db: Database session
        session_id: Conversation session ID
        limit: Maximum number of messages to return

    Returns:
        List of messages in chronological order
    """
    return db.query(Message)\
        .filter(Message.session_id == session_id)\
        .order_by(Message.created_at.asc())\
        .limit(limit)\
        .all()


def get_conversation_history(
    db: Session,
    session_id: str,
    window_size: int = 10
) -> List[dict]:
    """
    Get conversation history formatted for LLM context.

    Args:
        db: Database session
        session_id: Conversation session ID
        window_size: Number of recent messages to return

    Returns:
        List of messages as dicts with 'role' and 'content'
    """
    messages = db.query(Message)\
        .filter(Message.session_id == session_id)\
        .order_by(Message.created_at.desc())\
        .limit(window_size)\
        .all()

    # Reverse to get chronological order
    messages = list(reversed(messages))

    return [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]
