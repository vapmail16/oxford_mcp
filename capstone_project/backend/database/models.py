"""
Database models for IT Support Agent.
Implemented following TDD - all tests in test_database_models.py should pass.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
import os

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./support_agent.db")

# For testing, use in-memory database
if os.getenv("TESTING") == "True":
    DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class TicketStatus(str, enum.Enum):
    """Ticket lifecycle states"""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketPriority(str, enum.Enum):
    """Ticket priority levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IssueCategory(str, enum.Enum):
    """Issue classification categories"""
    PASSWORD = "PASSWORD"
    NETWORK = "NETWORK"
    SOFTWARE = "SOFTWARE"
    HARDWARE = "HARDWARE"
    ACCESS = "ACCESS"
    UNKNOWN = "UNKNOWN"


class Ticket(Base):
    """
    Support ticket model.
    Tracks IT support issues from creation to resolution.
    """
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    category = Column(Enum(IssueCategory), default=IssueCategory.UNKNOWN, nullable=False)
    user_email = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True, index=True)

    def __repr__(self):
        return f"<Ticket {self.id}: {self.title} [{self.status.value}]>"


class Message(Base):
    """
    Conversation message model.
    Stores chat history between users and the IT support agent.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    msg_metadata = Column(Text, nullable=True)  # JSON string for sources, ticket_id, etc.

    def __repr__(self):
        return f"<Message {self.id}: {self.role} in {self.session_id}>"


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
