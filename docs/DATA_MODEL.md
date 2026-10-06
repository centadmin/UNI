# Data Model

Implementation of the capstone **ERD (Deliverable 09)**. Tables map 1:1 to ORM
classes in `backend/app/db/models.py`.

## Entities

### role
| Column | Type | Notes |
|---|---|---|
| role_id | int PK | |
| name | str unique | admin / agent / manager / executive / customer |

### agent  *(internal users)*
| Column | Type | Notes |
|---|---|---|
| agent_id | uuid PK | |
| name | str | |
| email | str unique | login identity |
| password_hash | str | bcrypt |
| role_id | FK → role | |
| is_active | bool | disabled users cannot log in |
| created_at | datetime | |

### customer
| Column | Type | Notes |
|---|---|---|
| customer_id | uuid PK | |
| name | str | |
| email | str unique | login identity |
| password_hash | str | bcrypt |
| segment | str | Standard / Premium / Wealth |
| tenure_months | int | used by churn model |
| created_at | datetime | |

### category
| Column | Type | Notes |
|---|---|---|
| category_id | int PK | |
| name | str unique | Billing, Account Access, Cards, Transfers, Loans, General |

### ticket
| Column | Type | Notes |
|---|---|---|
| ticket_id | uuid PK | |
| customer_id | FK → customer | |
| category_id | FK → category, nullable | set by classifier |
| agent_id | FK → agent, nullable | assigned on first agent reply |
| subject | str | |
| body | text | |
| status | str | open / in_progress / escalated / closed |
| priority | str | low / medium / high (high if sentiment negative) |
| classification_confidence | float | classifier output |
| created_at / resolved_at | datetime | resolution time = resolved − created |

### message
| Column | Type | Notes |
|---|---|---|
| message_id | uuid PK | |
| ticket_id | FK → ticket | |
| sender_type | str | customer / agent / assistant |
| sender_name | str | |
| body | text | |
| created_at | datetime | |

### sentiment
| Column | Type | Notes |
|---|---|---|
| sentiment_id | uuid PK | |
| ticket_id | FK → ticket | |
| label | str | positive / neutral / negative |
| score | float | −1.0 .. 1.0 |
| created_at | datetime | |

### churn_score
| Column | Type | Notes |
|---|---|---|
| score_id | uuid PK | |
| customer_id | FK → customer | |
| risk_score | float | 0..1 churn probability |
| computed_at | datetime | history of recomputations |

### kb_article  /  rag_chunk
| Column | Type | Notes |
|---|---|---|
| article_id | uuid PK | knowledge base article |
| title / body | str / text | |
| chunk_id | uuid PK | retrievable unit |
| article_id | FK → kb_article | |
| content | text | indexed for RAG retrieval |

## Relationships

| Parent | Child | Cardinality |
|---|---|---|
| role | agent | 1 : many |
| customer | ticket | 1 : many |
| customer | churn_score | 1 : many |
| category | ticket | 1 : many |
| agent | ticket | 1 : many (nullable) |
| ticket | message | 1 : many |
| ticket | sentiment | 1 : many |
| kb_article | rag_chunk | 1 : many |

## Migrations

The reference build uses `Base.metadata.create_all()` at startup for simplicity.
For production, introduce **Alembic** migrations:

```bash
cd backend
pip install alembic
alembic init migrations
# set sqlalchemy.url from env, then:
alembic revision --autogenerate -m "init"
alembic upgrade head
```
