"""Tickets router.

Powers two wireframe screens:
  * WF-01 Customer Support Portal  — create/list/track own tickets, chat
  * WF-02 Agent Workspace          — queue, ticket detail, reply, status, sentiment

On ticket creation the platform automatically:
  * classifies the ticket (FR-004)
  * scores sentiment (FR-005)
  * records a Sentiment row (ERD)
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.core.security import get_current_user, require_roles, CurrentUser
from app.ml.engine import classifier, sentiment
from app.schemas import (
    TicketCreate, TicketOut, TicketDetail, MessageOut, MessageCreate
)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

STAFF = ("agent", "manager", "admin")


def _latest_sentiment(ticket: models.Ticket) -> str | None:
    if not ticket.sentiments:
        return None
    return sorted(ticket.sentiments, key=lambda s: s.created_at)[-1].label


def _to_out(t: models.Ticket) -> TicketOut:
    return TicketOut(
        ticket_id=t.ticket_id,
        subject=t.subject,
        body=t.body,
        status=t.status,
        priority=t.priority,
        category=t.category.name if t.category else None,
        classification_confidence=t.classification_confidence,
        customer_name=t.customer.name if t.customer else None,
        agent_name=t.agent.name if t.agent else None,
        sentiment=_latest_sentiment(t),
        created_at=t.created_at,
    )


def _get_or_create_category(db: Session, name: str) -> models.Category:
    cat = db.query(models.Category).filter(models.Category.name == name).first()
    if not cat:
        cat = models.Category(name=name)
        db.add(cat)
        db.flush()
    return cat


# --------------------------------------------------------------------------
# Customer portal (WF-01)
# --------------------------------------------------------------------------
@router.post("", response_model=TicketDetail, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(get_current_user)):
    if user.kind != "customer":
        raise HTTPException(status_code=403, detail="Only customers can open tickets")

    text = f"{payload.subject}. {payload.body}"
    label, confidence = classifier.predict(text)
    sent_label, sent_score = sentiment.score(text)
    category = _get_or_create_category(db, label)

    ticket = models.Ticket(
        customer_id=user.id,
        category_id=category.category_id,
        subject=payload.subject,
        body=payload.body,
        status="open",
        priority="high" if sent_label == "negative" else "medium",
        classification_confidence=round(confidence, 3),
    )
    db.add(ticket)
    db.flush()
    db.add(models.Message(ticket_id=ticket.ticket_id, sender_type="customer",
                          sender_name=user.name, body=payload.body))
    db.add(models.Sentiment(ticket_id=ticket.ticket_id, label=sent_label, score=sent_score))
    db.commit()
    db.refresh(ticket)
    return _detail(ticket)


@router.get("/mine", response_model=list[TicketOut])
def my_tickets(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    if user.kind != "customer":
        raise HTTPException(status_code=403, detail="Customers only")
    rows = (db.query(models.Ticket)
            .filter(models.Ticket.customer_id == user.id)
            .order_by(models.Ticket.created_at.desc()).all())
    return [_to_out(t) for t in rows]


# --------------------------------------------------------------------------
# Agent workspace (WF-02)
# --------------------------------------------------------------------------
@router.get("/queue", response_model=list[TicketOut])
def queue(status: str | None = None, db: Session = Depends(get_db),
          user: CurrentUser = Depends(require_roles(*STAFF))):
    q = db.query(models.Ticket)
    if status:
        q = q.filter(models.Ticket.status == status)
    rows = q.order_by(models.Ticket.created_at.desc()).all()
    return [_to_out(t) for t in rows]


def _detail(t: models.Ticket) -> TicketDetail:
    base = _to_out(t)
    msgs = [MessageOut.model_validate(m) for m in sorted(t.messages, key=lambda m: m.created_at)]
    return TicketDetail(**base.model_dump(), messages=msgs)


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: str, db: Session = Depends(get_db),
               user: CurrentUser = Depends(get_current_user)):
    t = db.query(models.Ticket).filter(models.Ticket.ticket_id == ticket_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    # customers may only see their own ticket (least privilege)
    if user.kind == "customer" and t.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _detail(t)


@router.post("/{ticket_id}/messages", response_model=TicketDetail)
def add_message(ticket_id: str, payload: MessageCreate, db: Session = Depends(get_db),
                user: CurrentUser = Depends(get_current_user)):
    t = db.query(models.Ticket).filter(models.Ticket.ticket_id == ticket_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if user.kind == "customer" and t.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    sender = "customer" if user.kind == "customer" else "agent"
    db.add(models.Message(ticket_id=ticket_id, sender_type=sender,
                          sender_name=user.name, body=payload.body))
    # re-score sentiment on customer messages
    if sender == "customer":
        lbl, sc = sentiment.score(payload.body)
        db.add(models.Sentiment(ticket_id=ticket_id, label=lbl, score=sc))
    # assign agent on first staff reply
    if sender == "agent" and t.agent_id is None:
        t.agent_id = user.id
        t.status = "in_progress"
    db.commit()
    db.refresh(t)
    return _detail(t)


@router.patch("/{ticket_id}/status", response_model=TicketOut)
def set_status(ticket_id: str, status: str, db: Session = Depends(get_db),
               user: CurrentUser = Depends(require_roles(*STAFF))):
    if status not in {"open", "in_progress", "escalated", "closed"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    t = db.query(models.Ticket).filter(models.Ticket.ticket_id == ticket_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    t.status = status
    if status == "closed" and t.resolved_at is None:
        t.resolved_at = datetime.now(timezone.utc)
    if t.agent_id is None:
        t.agent_id = user.id
    db.commit()
    db.refresh(t)
    return _to_out(t)
