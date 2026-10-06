"""Analytics router — powers the Executive Dashboard (WF-03).

Endpoints:
  * /kpis              CSAT, avg resolution, open tickets, churn-risk count
  * /tickets-by-category   bar-chart data
  * /sentiment-trend       sentiment distribution
  * /churn-risk            at-risk customers (recomputes churn scores) [FR-008]

Restricted to manager / executive / admin (RBAC, FR-007).
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.core.security import require_roles, CurrentUser
from app.core.config import get_settings
from app.ml.engine import churn
from app.schemas import KpiOut, CategoryCount, SentimentPoint, ChurnCustomer

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
settings = get_settings()
VIEW = ("manager", "executive", "admin")


def _resolution_hours(t: models.Ticket) -> float | None:
    if t.resolved_at and t.created_at:
        return (t.resolved_at - t.created_at).total_seconds() / 3600.0
    return None


def _compute_churn(db: Session) -> list[ChurnCustomer]:
    """Recompute churn scores for every customer and persist a ChurnScore row."""
    out: list[ChurnCustomer] = []
    customers = db.query(models.Customer).all()
    for c in customers:
        tickets = c.tickets
        open_tickets = sum(1 for t in tickets if t.status != "closed")
        neg = 0
        total_sent = 0
        res_hours = []
        for t in tickets:
            for s in t.sentiments:
                total_sent += 1
                if s.label == "negative":
                    neg += 1
            rh = _resolution_hours(t)
            if rh is not None:
                res_hours.append(rh)
        neg_ratio = (neg / total_sent) if total_sent else 0.0
        avg_res = (sum(res_hours) / len(res_hours)) if res_hours else 12.0
        risk = churn.score(open_tickets, neg_ratio, avg_res, c.tenure_months, c.segment)
        db.add(models.ChurnScore(customer_id=c.customer_id, risk_score=risk))
        out.append(ChurnCustomer(customer_id=c.customer_id, name=c.name,
                                 segment=c.segment, risk_score=risk))
    db.commit()
    out.sort(key=lambda x: x.risk_score, reverse=True)
    return out


@router.get("/kpis", response_model=KpiOut)
def kpis(db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles(*VIEW))):
    tickets = db.query(models.Ticket).all()
    # CSAT proxy: share of non-negative latest sentiment across tickets
    pos = neg = 0
    res_hours = []
    open_count = 0
    for t in tickets:
        if t.status != "closed":
            open_count += 1
        if t.sentiments:
            last = sorted(t.sentiments, key=lambda s: s.created_at)[-1]
            if last.label == "negative":
                neg += 1
            else:
                pos += 1
        rh = _resolution_hours(t)
        if rh is not None:
            res_hours.append(rh)
    csat = round(100.0 * pos / (pos + neg), 1) if (pos + neg) else 0.0
    avg_res = round(sum(res_hours) / len(res_hours), 1) if res_hours else 0.0
    churn_rows = _compute_churn(db)
    at_risk = sum(1 for c in churn_rows if c.risk_score >= settings.churn_high_risk_threshold)
    return KpiOut(csat=csat, avg_resolution_hours=avg_res,
                  open_tickets=open_count, churn_risk_customers=at_risk)


@router.get("/tickets-by-category", response_model=list[CategoryCount])
def tickets_by_category(db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles(*VIEW))):
    rows = (db.query(models.Category.name, func.count(models.Ticket.ticket_id))
            .join(models.Ticket, models.Ticket.category_id == models.Category.category_id)
            .group_by(models.Category.name)
            .order_by(func.count(models.Ticket.ticket_id).desc()).all())
    return [CategoryCount(category=name, count=count) for name, count in rows]


@router.get("/sentiment-trend", response_model=list[SentimentPoint])
def sentiment_trend(db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles(*VIEW))):
    rows = (db.query(models.Sentiment.label, func.count(models.Sentiment.sentiment_id))
            .group_by(models.Sentiment.label).all())
    order = {"positive": 0, "neutral": 1, "negative": 2}
    data = [SentimentPoint(label=lbl, count=cnt) for lbl, cnt in rows]
    data.sort(key=lambda p: order.get(p.label, 9))
    return data


@router.get("/churn-risk", response_model=list[ChurnCustomer])
def churn_risk(db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles(*VIEW))):
    return _compute_churn(db)
