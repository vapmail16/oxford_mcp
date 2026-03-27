"""
Database package for IT Support Agent.
Provides models and CRUD operations.
"""

from .models import (
    Base,
    Ticket,
    Message,
    TicketStatus,
    TicketPriority,
    IssueCategory,
    SessionLocal,
    engine,
    init_db
)

from .crud import (
    create_ticket,
    get_ticket,
    get_all_tickets,
    update_ticket_status,
    create_message,
    get_messages_by_session,
    get_conversation_history
)

__all__ = [
    'Base',
    'Ticket',
    'Message',
    'TicketStatus',
    'TicketPriority',
    'IssueCategory',
    'SessionLocal',
    'engine',
    'init_db',
    'create_ticket',
    'get_ticket',
    'get_all_tickets',
    'update_ticket_status',
    'create_message',
    'get_messages_by_session',
    'get_conversation_history'
]
