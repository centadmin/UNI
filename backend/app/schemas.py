"""Pydantic schemas for request validation and response serialisation."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ---- auth ----
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str


# ---- tickets ----
class TicketCreate(BaseModel):
    subject: str
    body: str


class MessageOut(BaseModel):
    message_id: str
    sender_type: str
    sender_name: str
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


class TicketOut(BaseModel):
    ticket_id: str
    subject: str
    body: str
    status: str
    priority: str
    category: Optional[str] = None
    classification_confidence: float
    customer_name: Optional[str] = None
    agent_name: Optional[str] = None
    sentiment: Optional[str] = None
    created_at: datetime


class TicketDetail(TicketOut):
    messages: list[MessageOut] = []


class MessageCreate(BaseModel):
    body: str


# ---- assistant (RAG) ----
class AssistantQuery(BaseModel):
    query: str


class AssistantReply(BaseModel):
    escalate: bool
    answer: Optional[str] = None
    source: Optional[dict] = None
    confidence: float


# ---- admin ----
class AgentCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # agent / manager / executive / admin


class AgentOut(BaseModel):
    agent_id: str
    name: str
    email: str
    role: str
    is_active: bool


# ---- analytics ----
class KpiOut(BaseModel):
    csat: float
    avg_resolution_hours: float
    open_tickets: int
    churn_risk_customers: int


class CategoryCount(BaseModel):
    category: str
    count: int


class SentimentPoint(BaseModel):
    label: str
    count: int


class ChurnCustomer(BaseModel):
    customer_id: str
    name: str
    segment: str
    risk_score: float


UserOut.model_rebuild()
LoginResponse.model_rebuild()
