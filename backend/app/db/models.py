"""ORM models — a direct implementation of the capstone ERD (Deliverable 09).

Entities & relationships from the ERD:
    ROLE        1..* AGENT
    CUSTOMER    1..* TICKET
    CUSTOMER    1..* CHURN_SCORE
    CATEGORY    1..* TICKET
    AGENT       1..* TICKET           (nullable — unassigned tickets allowed)
    TICKET      1..* MESSAGE
    TICKET      1..* SENTIMENT
    KB_ARTICLE  1..* RAG_CHUNK
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text, func
)
from sqlalchemy.orm import relationship, mapped_column, Mapped
from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Role(Base):
    __tablename__ = "role"
    role_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)  # admin, agent, manager, executive, customer

    agents: Mapped[list["Agent"]] = relationship(back_populates="role")


class Agent(Base):
    """Internal users — agents, managers, executives, administrators.

    Customers authenticate as well but are modelled separately (see Customer)
    because the ERD treats them as a distinct entity.
    """
    __tablename__ = "agent"
    agent_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("role.role_id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    role: Mapped["Role"] = relationship(back_populates="agents")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="agent")


class Customer(Base):
    __tablename__ = "customer"
    customer_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    segment: Mapped[str] = mapped_column(String(40), default="Standard")  # Standard / Premium / Wealth
    tenure_months: Mapped[int] = mapped_column(Integer, default=12)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")
    churn_scores: Mapped[list["ChurnScore"]] = relationship(back_populates="customer")


class Category(Base):
    __tablename__ = "category"
    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="category")


class Ticket(Base):
    __tablename__ = "ticket"
    ticket_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customer.customer_id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.category_id"), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agent.agent_id"), nullable=True)

    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open / in_progress / escalated / closed
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    category: Mapped["Category"] = relationship(back_populates="tickets")
    agent: Mapped["Agent"] = relationship(back_populates="tickets")
    messages: Mapped[list["Message"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")
    sentiments: Mapped[list["Sentiment"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "message"
    message_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("ticket.ticket_id"))
    sender_type: Mapped[str] = mapped_column(String(20))  # customer / agent / assistant
    sender_name: Mapped[str] = mapped_column(String(120), default="")
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    ticket: Mapped["Ticket"] = relationship(back_populates="messages")


class Sentiment(Base):
    __tablename__ = "sentiment"
    sentiment_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("ticket.ticket_id"))
    label: Mapped[str] = mapped_column(String(20))  # positive / neutral / negative
    score: Mapped[float] = mapped_column(Float)      # -1.0 .. 1.0
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    ticket: Mapped["Ticket"] = relationship(back_populates="sentiments")


class ChurnScore(Base):
    __tablename__ = "churn_score"
    score_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customer.customer_id"))
    risk_score: Mapped[float] = mapped_column(Float)  # 0..1 probability of churn
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    customer: Mapped["Customer"] = relationship(back_populates="churn_scores")


class KBArticle(Base):
    __tablename__ = "kb_article"
    article_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    chunks: Mapped[list["RAGChunk"]] = relationship(back_populates="article", cascade="all, delete-orphan")


class RAGChunk(Base):
    __tablename__ = "rag_chunk"
    chunk_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    article_id: Mapped[str] = mapped_column(ForeignKey("kb_article.article_id"))
    content: Mapped[str] = mapped_column(Text)

    article: Mapped["KBArticle"] = relationship(back_populates="chunks")
