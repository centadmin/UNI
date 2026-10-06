# Deployment Guide

AI-Powered Intelligent Customer Support & Business Analytics Platform
ABC Financial Services Ltd. — Centium Technologies

This runbook covers three deployment paths:

1. **Local development** (no containers)
2. **Single server / GitHub Codespaces** (`bash start.sh`)
3. **AWS production** (aligned with the Solution Architecture Document)

---

## 0. Prerequisites

| Tool | Version |
|---|---|
| Python | any Python 3 to bootstrap; `start.sh` installs Python 3.12 itself (via uv) |
| Node.js | 18+ (tested on 22) |
| PostgreSQL | 16 — production only (managed via RDS); demos use SQLite |

Clone the repository and copy the environment template:

```bash
cp .env.example .env
# edit JWT_SECRET (long random string), DB credentials, CORS_ORIGINS
```

### Required environment variables

| Variable | Purpose | Example |
|---|---|---|
| `APP_ENV` | environment name | `production` |
| `DATABASE_URL` | DB connection string | `postgresql+psycopg://user:pw@host:5432/db` |
| `JWT_SECRET` | token signing secret | (32+ random chars) |
| `ACCESS_TOKEN_MINUTES` | token lifetime | `480` |
| `CORS_ORIGINS` | allowed UI origins (CSV) | `https://app.abcfin.com` |
| `CHURN_HIGH_RISK_THRESHOLD` | churn alert cutoff | `0.60` |

> If `DATABASE_URL` is unset the backend uses a local SQLite file — convenient for dev, **not** for production.

---

## 1. Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # API on :8000, Swagger at /docs

# Frontend (second terminal)
cd frontend
npm install
npm run dev                            # UI on :5173, proxies /api -> :8000
```

On first start the backend creates the schema, trains the ML models, seeds demo
data, and indexes the knowledge base. Verify:

```bash
curl http://localhost:8000/api/health   # {"status":"ok",...}
```

---

## 2. Single server / GitHub Codespaces

One command installs dependencies (first run only), builds the website and
starts **one** process on port **8000** that serves the website, the API
(`/api/...`) and the API docs (`/docs`):

```bash
bash start.sh            # start
bash start.sh --reset    # start with fresh demo data
```

Data lives in `backend/data/` (SQLite file + generated JWT secret; git-ignored).
To use PostgreSQL, set `DATABASE_URL` (and `JWT_SECRET`) in the environment
before running `start.sh`. Put a TLS-terminating reverse proxy or load
balancer in front of port 8000 for anything beyond a demo.

---

## 3. AWS production

Target architecture (from the SAD):

```
Route 53 ─► CloudFront ─► S3 (static React build)            [frontend]
                       └► ALB ─► ECS Fargate (FastAPI tasks)  [backend]
                                   │
                                   ├─► RDS PostgreSQL (Multi-AZ)
                                   ├─► Secrets Manager (JWT, DB creds)
                                   └─► CloudWatch (logs, metrics, alarms)
ECR holds the backend (and optional frontend) container images.
```

### 3.1 Provision infrastructure

1. **VPC** with public + private subnets across 2 AZs.
2. **RDS PostgreSQL 16** (Multi-AZ) in private subnets; note the endpoint.
3. **Secrets Manager** entries: `DATABASE_URL`, `JWT_SECRET`.
4. **ECR** repository for the backend image.
5. **ECS Fargate** cluster + service behind an **Application Load Balancer** (HTTPS via ACM certificate).
6. **S3 bucket** + **CloudFront** distribution for the frontend.

### 3.2 Build & push the backend image

The repository ships no Dockerfile (demos run with `start.sh`). For ECS, add a
`backend/Dockerfile` along these lines, then build and push:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
aws ecr get-login-password --region <region> \
  | docker login --username AWS --password-stdin <acct>.dkr.ecr.<region>.amazonaws.com

docker build -t abc-backend ./backend
docker tag abc-backend:latest <acct>.dkr.ecr.<region>.amazonaws.com/abc-backend:latest
docker push <acct>.dkr.ecr.<region>.amazonaws.com/abc-backend:latest
```

### 3.3 Backend ECS task definition (key points)

- **Image:** the ECR URI above.
- **Port:** 8000, registered with the ALB target group.
- **Env / secrets:** inject `DATABASE_URL` and `JWT_SECRET` from Secrets Manager; set `APP_ENV=production`, `CORS_ORIGINS=https://<your-domain>`.
- **Health check:** ALB target group → `GET /api/health` (200).
- **Autoscaling:** target tracking on CPU ~60%.

### 3.4 Database migrations

This build auto-creates tables on first boot. For controlled production
releases, switch to **Alembic** (see `docs/DATA_MODEL.md`) and run
`alembic upgrade head` as a one-off ECS task during each deploy. Disable the
auto-seed in production by seeding real data once, manually:

```bash
# one-off task / bastion
python -m app.seed        # idempotent; safe to run once to load roles + KB
```

> For production, review `app/seed.py` and load **real** staff accounts and the
> real knowledge base rather than the demo fixtures. Rotate all demo passwords.

### 3.5 Frontend deploy (S3 + CloudFront)

```bash
cd frontend
VITE_API_BASE="https://api.abcfin.com" npm run build
aws s3 sync dist/ s3://<frontend-bucket> --delete
aws cloudfront create-invalidation --distribution-id <id> --paths "/*"
```

Configure CloudFront to return `index.html` for 403/404 so client-side routing
(React Router) works.

### 3.6 Observability & operations

- **Logs:** ECS → CloudWatch Logs; set retention (e.g. 30 days).
- **Metrics/alarms:** ALB 5xx rate, ECS CPU/memory, RDS connections/storage.
- **Backups:** RDS automated backups + periodic snapshots; test restore (DR drill).
- **Scaling:** ECS service autoscaling; RDS read replica if analytics load grows.

---

## 4. CI/CD

`.github/workflows/ci.yml` runs on every push/PR:

1. **Backend tests** — install deps, run `pytest` (SQLite).
2. **Start the app and test it end to end** — runs `bash start.sh` exactly as a
   user would, then `scripts/smoke_test.py` (29 checks) against port 8000.

Extend the pipeline for CD by adding a deploy job that pushes the backend image
to ECR and triggers an ECS service update (and syncs the frontend build to S3)
on pushes to `main`.

---

## 5. Production hardening checklist

- [ ] `JWT_SECRET` set from Secrets Manager (not the default)
- [ ] All demo accounts removed / passwords rotated
- [ ] `CORS_ORIGINS` restricted to the real UI domain
- [ ] HTTPS enforced end-to-end (ACM + ALB + CloudFront)
- [ ] RDS in private subnets, Multi-AZ, automated backups on
- [ ] Alembic migrations replacing `create_all()`
- [ ] CloudWatch alarms wired to on-call
- [ ] Container image scanning enabled in ECR
- [ ] Least-privilege IAM roles for ECS tasks
- [ ] Real knowledge base loaded and indexed
