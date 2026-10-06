"""SQLAlchemy engine + session.

DATABASE_URL drives the backend:
  - sqlite:///./capstone.db          (default, local dev)
  - postgresql+psycopg://user:pw@host:5432/db   (production, AWS RDS)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings

settings = get_settings()

if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # Fail a connection attempt after 5s instead of hanging for minutes, so the
    # start-up retry loop (app/seed.py) can report and retry promptly.
    connect_args = {"connect_timeout": 5}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
