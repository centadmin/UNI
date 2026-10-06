# AI-Powered Intelligent Customer Support & Business Analytics Platform

**Client:** ABC Financial Services Ltd. **·** **Delivered by:** Centium Technologies
**Capstone reference implementation** built from the project ERD, wireframes, and Solution Architecture Document.

A full-stack platform that lets customers raise and self-serve support tickets, gives agents an AI-assisted workspace, and gives managers/executives live analytics — including ML ticket classification, sentiment analysis, churn prediction, and a Generative-AI (RAG) knowledge assistant.

---

## What it does (mapped to the wireframes)

| Screen | Who | Capability |
|---|---|---|
| **WF-01 Customer Support Portal** | Customers | Raise tickets (auto-classified + prioritised), track status, chat with the AI assistant |
| **WF-02 Agent Workspace** | Agents / Managers | Triage queue with category, priority & sentiment; reply; AI **suggested reply**; status workflow |
| **WF-03 Executive Dashboard** | Managers / Executives | CSAT, avg resolution, open tickets, tickets-by-category, sentiment mix, **churn-risk** table |
| **WF-04 Admin Console** | Administrators | User & role management (create / enable / disable) |

## AI / ML capability (from the ML Model & GenAI Design documents)

| Capability | Technique | Requirement |
|---|---|---|
| Ticket classification | TF-IDF + Logistic Regression (multi-class) | FR-004 |
| Sentiment analysis | Lexicon-based polarity scoring | FR-005 |
| Churn prediction | Transparent logistic-style model over interpretable features | FR-008 |
| Knowledge assistant | RAG retrieval (TF-IDF similarity over KB chunks) with escalation guardrail | FR-003 |

> The models run **fully offline** — no external LLM key is required to run the project. In production the RAG retrieval step feeds an LLM for generation (see `docs/ARCHITECTURE.md`); here the top-ranked, citation-bearing knowledge chunk is returned directly, so the flow is identical minus the generation call.

---

## Tech stack

- **Backend:** Python 3.12 (provisioned automatically by `start.sh`), FastAPI, SQLAlchemy 2, scikit-learn, JWT auth (python-jose), bcrypt
- **Frontend:** React 18, Vite, React Router, Recharts — built once and served by the backend
- **Database:** SQLite for demos and Codespaces (zero setup); PostgreSQL in production via `DATABASE_URL`
- **CI:** GitHub Actions — backend tests plus a full start-and-test of the app on every push

---

## Quick start

The whole platform runs as **one program on one port (8000)**: the website,
the API (`/api/...`) and the API docs (`/docs`). One command sets everything up.

### GitHub Codespaces (recommended — nothing to install)

1. On this repository's page: **Code → Codespaces → Create codespace on main**.
2. In the terminal, run:

   ```bash
   bash start.sh
   ```

3. The first run installs everything (about 1 minute; it downloads its own Python 3.12, whatever version the Codespace has). When it is ready it prints a green box with the address to open, e.g.
   `https://<your-codespace>-8000.app.github.dev`. Click it (or **Ports** tab → port **8000** → globe icon).
4. Log in with a demo account (below). Stop with **Ctrl + C**.

### Your own computer (Linux, macOS, or Windows with WSL)

Needs **Node.js 18+** and any **Python 3** (`start.sh` downloads its own Python 3.12 and the packages, once, into `~/.abc-support/`). From the project folder:

```bash
bash start.sh          # then open http://localhost:8000
```

| Task | Command |
|---|---|
| Start | `bash start.sh` |
| Stop | **Ctrl + C** |
| Reset to fresh demo data | `bash start.sh --reset` |
| End-to-end check (app must be running; adds one test ticket and user) | `python3 scripts/smoke_test.py` |

The database is a file in `backend/data/` (not committed). A random login-token
secret is generated there on first run. To use PostgreSQL instead, set
`DATABASE_URL` before starting, e.g.
`DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db bash start.sh`.

### Developer mode (live reload)

```bash
# terminal 1 — API with auto-reload on :8000
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && uvicorn app.main:app --reload
# terminal 2 — website with hot reload on :5173 (proxies /api to :8000)
cd frontend && npm install && npm run dev
```

### Demo accounts (seeded automatically)

| Role | Email | Password | Opens on |
|---|---|---|---|
| Customer | `rahul@example.com` | `customer123` | Support Portal |
| Agent | `agent@abcfin.com` | `agent123` | Agent Workspace |
| Manager | `manager@abcfin.com` | `manager123` | Executive Dashboard (+ Agent Workspace) |
| Executive | `exec@abcfin.com` | `exec123` | Executive Dashboard |
| Admin | `admin@abcfin.com` | `admin123` | Admin Console (+ all staff screens) |

---

## Tests

```bash
cd backend
DATABASE_URL="sqlite:///./ci.db" python -m pytest -q
```

Covers auth, ticket classification & sentiment, the RAG assistant, the agent
workflow, executive analytics, and the RBAC rules.

**GitHub Actions** (`.github/workflows/ci.yml`) runs on every push to `main`:
the backend tests, then **"Start the app and test it end to end"** — it runs
`bash start.sh` exactly as you would and executes `scripts/smoke_test.py`
(29 checks: website, all five logins, the ticket lifecycle, AI assistant,
dashboards, admin, role restrictions).

> **Before sharing publicly:** the demo accounts use published passwords. Keep
> the repository and Codespaces ports private, or remove the demo users in
> `backend/app/seed.py`.

---

## Repository layout

```
├── start.sh                 one command: install (first run) + start on port 8000
├── backend/                 FastAPI service (also serves the built website)
│   ├── app/
│   │   ├── core/            config + security (JWT, RBAC, hashing)
│   │   ├── db/              SQLAlchemy engine + ORM models (the ERD)
│   │   ├── ml/              classifier, sentiment, churn, RAG assistant
│   │   ├── routers/         auth, tickets, assistant, analytics, admin
│   │   ├── schemas.py       Pydantic request/response models
│   │   ├── seed.py          demo data + knowledge-base indexing
│   │   └── main.py          app entrypoint (API + website)
│   ├── tests/               pytest suite
│   └── requirements.txt
├── frontend/                React + Vite SPA (built into frontend/dist)
│   ├── src/
│   │   ├── pages/           CustomerPortal, AgentWorkspace, ExecutiveDashboard, AdminConsole
│   │   ├── components/      Shell (sidebar + topbar)
│   │   ├── lib/api.js       API client
│   │   └── main.jsx         routing + auth context
│   └── package.json
├── scripts/smoke_test.py    end-to-end check
├── docs/                    ARCHITECTURE.md, DEPLOYMENT.md, DATA_MODEL.md
├── .github/workflows/ci.yml tests + end-to-end run on every push
└── .env.example             reference settings
```

See **`docs/DEPLOYMENT.md`** for production deployment (AWS) and **`docs/ARCHITECTURE.md`** for the system design.
