"""Authentication & RBAC.

Implements FR-001 (login/auth) and FR-007 (role-based access control) and the
Security Architecture Review controls: JWT bearer tokens + least-privilege
role checks on every protected route.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import bcrypt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.db import models

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(raw: str) -> str:
    # bcrypt operates on the first 72 bytes; truncate defensively.
    return bcrypt.hashpw(raw.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str, kind: str) -> str:
    """kind = 'agent' | 'customer' so we know which table to resolve."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": subject, "role": role, "kind": kind, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class CurrentUser:
    def __init__(self, id: str, name: str, email: str, role: str, kind: str):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.kind = kind


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> CurrentUser:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        subject: str = payload.get("sub")
        kind: str = payload.get("kind")
        if subject is None or kind is None:
            raise cred_exc
    except JWTError:
        raise cred_exc

    if kind == "customer":
        cust = db.query(models.Customer).filter(models.Customer.customer_id == subject).first()
        if not cust:
            raise cred_exc
        return CurrentUser(cust.customer_id, cust.name, cust.email, "customer", "customer")

    agent = db.query(models.Agent).filter(models.Agent.agent_id == subject).first()
    if not agent or not agent.is_active:
        raise cred_exc
    return CurrentUser(agent.agent_id, agent.name, agent.email, agent.role.name, "agent")


def require_roles(*roles: str):
    """Dependency factory enforcing least-privilege access (FR-007)."""
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted to access this resource",
            )
        return user
    return checker
