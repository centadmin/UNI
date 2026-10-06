"""Smoke + integration tests for the API.

Run with:  DATABASE_URL="sqlite:///./ci.db" python -m pytest -q
Covers the critical paths behind each wireframe screen and the RBAC rules from
the Security Architecture Review.
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_api.db")

import pytest
from fastapi.testclient import TestClient

# Fresh DB per test session
if os.path.exists("./test_api.db"):
    os.remove("./test_api.db")

from app.main import app  # noqa: E402
from app.seed import init_and_seed  # noqa: E402

# TestClient does not run the FastAPI lifespan by default, so create tables,
# train the models and seed demo data explicitly before the suite runs.
init_and_seed()

client = TestClient(app)


def token(email, pw):
    r = client.post("/api/auth/login", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(email, pw):
    return {"Authorization": f"Bearer {token(email, pw)}"}


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_invalid():
    r = client.post("/api/auth/login", data={"username": "nope@x.com", "password": "x"})
    assert r.status_code == 401


def test_customer_create_ticket_is_classified_and_scored():
    r = client.post(
        "/api/tickets",
        headers=auth("rahul@example.com", "customer123"),
        json={"subject": "Card declined", "body": "My debit card was declined and I am frustrated."},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["category"] is not None           # FR-004 classification
    assert data["sentiment"] in {"negative", "neutral", "positive"}  # FR-005
    assert data["priority"] == "high"             # negative -> high priority


def test_assistant_answers_known_and_escalates_unknown():
    h = auth("rahul@example.com", "customer123")
    known = client.post("/api/assistant/ask", headers=h, json={"query": "reset my password"}).json()
    assert known["escalate"] is False and known["source"] is not None
    unknown = client.post("/api/assistant/ask", headers=h, json={"query": "weather on mars"}).json()
    assert unknown["escalate"] is True


def test_agent_queue_and_reply_assigns_ticket():
    h = auth("agent@abcfin.com", "agent123")
    queue = client.get("/api/tickets/queue", headers=h).json()
    assert len(queue) > 0
    tid = queue[0]["ticket_id"]
    r = client.post(f"/api/tickets/{tid}/messages", headers=h, json={"body": "We are looking into it."})
    assert r.status_code == 200
    assert r.json()["agent_name"] is not None


def test_rbac_customer_cannot_view_analytics():
    h = auth("rahul@example.com", "customer123")
    assert client.get("/api/analytics/kpis", headers=h).status_code == 403


def test_rbac_agent_cannot_access_admin():
    h = auth("agent@abcfin.com", "agent123")
    assert client.get("/api/admin/users", headers=h).status_code == 403


def test_executive_analytics_available():
    h = auth("exec@abcfin.com", "exec123")
    kpis = client.get("/api/analytics/kpis", headers=h).json()
    assert set(kpis) == {"csat", "avg_resolution_hours", "open_tickets", "churn_risk_customers"}
    churn = client.get("/api/analytics/churn-risk", headers=h).json()
    assert isinstance(churn, list) and len(churn) >= 1


def test_admin_can_create_user():
    h = auth("admin@abcfin.com", "admin123")
    r = client.post("/api/admin/users", headers=h,
                    json={"name": "Test Agent", "email": "test.agent@abcfin.com",
                          "password": "secret123", "role": "agent"})
    assert r.status_code in (201, 409)  # 409 if a previous run already created it
