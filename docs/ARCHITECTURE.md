# Architecture

This reference build implements the capstone **Solution Architecture Document (SAD)**: a React single-page app talking to a FastAPI service layer, backed by PostgreSQL and a knowledge/vector store, with AI/ML capabilities exposed as internal services.

## 1. High-level system

```
                         ┌──────────────────────────────────────────────┐
                         │                Browser (SPA)                 │
                         │  React + Vite + Recharts                     │
                         │  WF-01 Portal · WF-02 Workspace ·            │
                         │  WF-03 Dashboard · WF-04 Admin               │
                         └───────────────┬──────────────────────────────┘
                                         │ HTTPS (JWT bearer)
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │                     FastAPI service layer                       │
        │                                                                │
        │  auth ─ tickets ─ assistant ─ analytics ─ admin  (routers)      │
        │                                                                │
        │  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────┐  │
        │  │  AuthN/AuthZ  │  │   ML engine   │  │  RAG knowledge       │  │
        │  │  JWT + RBAC   │  │  classify /   │  │  assistant           │  │
        │  │               │  │  sentiment /  │  │  (retrieval + cite)  │  │
        │  │               │  │  churn        │  │                      │  │
        │  └──────────────┘  └───────────────┘  └─────────────────────┘  │
        └───────────────┬───────────────────────────┬────────────────────┘
                        │ SQLAlchemy                 │ vector / KB index
                        ▼                            ▼
                ┌───────────────┐            ┌────────────────────┐
                │  PostgreSQL    │            │  Knowledge base +   │
                │  (AWS RDS)     │            │  RAG chunks         │
                └───────────────┘            └────────────────────┘
```

## 2. Backend layering

- **Routers** (`app/routers/`) — one module per wireframe surface. Thin; they validate input, enforce RBAC, and delegate.
- **Core** (`app/core/`) — `config.py` (env-driven settings) and `security.py` (password hashing, JWT issue/verify, `require_roles()` dependency).
- **Data** (`app/db/`) — `session.py` (engine/session) and `models.py`, a 1:1 mapping of the ERD entities.
- **ML** (`app/ml/`) — `engine.py` holds four singletons (`classifier`, `sentiment`, `churn`, `assistant`) trained/indexed once at startup; `training_data.py` holds the seed corpus and lexicon.

## 3. Data model (the ERD)

Entities and relationships implemented exactly as in Deliverable 09:

```
ROLE ──1:*── AGENT ──1:*── TICKET ──*:1── CATEGORY
                              │  ▲ *:1
                              │  └────────── CUSTOMER ──1:*── CHURN_SCORE
                              ├──1:*── MESSAGE
                              └──1:*── SENTIMENT
KB_ARTICLE ──1:*── RAG_CHUNK
```

- `Ticket.agent_id` is nullable (unassigned tickets sit in the queue until an agent replies).
- `Ticket.category_id` is set by the classifier at creation time.
- Each customer message creates a `Sentiment` row; the latest one drives ticket priority and dashboard sentiment.
- `ChurnScore` rows are recomputed and persisted whenever analytics are requested, giving an auditable history.

Full field-level detail is in `docs/DATA_MODEL.md`.

## 4. AI/ML design

### Ticket classification (FR-004)
TF-IDF (1–2 grams) → multinomial Logistic Regression over six categories (Billing, Account Access, Cards, Transfers, Loans, General). Returns label + confidence; confidence is stored on the ticket.

### Sentiment (FR-005)
Lexicon polarity scoring normalised to −1..1; mapped to positive / neutral / negative. A negative score raises ticket priority to **high**.

### Churn prediction (FR-008)
Transparent logistic-style function over interpretable features — open-ticket count, negative-sentiment ratio, average resolution time, tenure, and customer segment. Chosen for explainability (Responsible-AI requirement); coefficients are documented in code.

### RAG knowledge assistant (FR-003)
The GenAI Design Document flow is: **embed query → similarity search over KB chunks → assemble grounded answer + citation**. This build performs the retrieval with TF-IDF cosine similarity and returns the best chunk with its source article. Below a confidence floor it **escalates to a human** instead of guessing (governance guardrail). In production the retrieved context is passed to an LLM for natural-language generation; the contract returned to the UI is unchanged.

## 5. Security (Security Architecture Review)

- **AuthN:** email/password → bcrypt verification → short-lived JWT.
- **AuthZ:** every protected route declares allowed roles via `require_roles(...)`; customers can only read their own tickets.
- **Transport:** TLS terminated at the load balancer / CloudFront in production.
- **Secrets:** `JWT_SECRET`, DB credentials injected via environment (AWS Secrets Manager / SSM in production) — never committed.
- **Least privilege:** distinct roles (customer, agent, manager, executive, admin) with disjoint capabilities.

## 6. Environments

| Concern | Local dev | Production |
|---|---|---|
| Database | SQLite file | PostgreSQL (AWS RDS) |
| Frontend | Built by `start.sh`, served by FastAPI on `:8000` (or Vite dev server `:5173`) | Static build on S3 + CloudFront |
| API | uvicorn `--reload` | uvicorn workers behind ALB, on ECS/EKS |
| Secrets | `.env` | AWS Secrets Manager / SSM Parameter Store |

See `docs/DEPLOYMENT.md` for the deployment runbook.
