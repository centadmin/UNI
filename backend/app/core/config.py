"""Application configuration.

Reads settings from environment variables so the same image runs locally
(SQLite) or in production (PostgreSQL on AWS RDS).
"""
from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = "ABC Financial — AI Customer Support & Analytics Platform"
    env: str = os.getenv("APP_ENV", "development")

    # Default to a local SQLite file so the project runs with zero setup.
    # In production set DATABASE_URL to the PostgreSQL DSN (see .env.example).
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./capstone.db")

    # Auth
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "480"))

    # ML / eligibility thresholds (from the SRS / capstone documentation)
    classifier_min_confidence: float = 0.0
    churn_high_risk_threshold: float = float(os.getenv("CHURN_HIGH_RISK_THRESHOLD", "0.60"))

    # CORS
    cors_origins: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")


@lru_cache
def get_settings() -> Settings:
    return Settings()
