"""Admin router — powers the Admin Console (WF-04).

User & role management, restricted to administrators (FR-007).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.core import security
from app.core.security import require_roles, CurrentUser
from app.schemas import AgentCreate, AgentOut

router = APIRouter(prefix="/api/admin", tags=["admin"])
VALID_ROLES = {"agent", "manager", "executive", "admin"}


def _to_out(a: models.Agent) -> AgentOut:
    return AgentOut(agent_id=a.agent_id, name=a.name, email=a.email,
                    role=a.role.name, is_active=a.is_active)


@router.get("/users", response_model=list[AgentOut])
def list_users(db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles("admin"))):
    return [_to_out(a) for a in db.query(models.Agent).order_by(models.Agent.created_at).all()]


@router.post("/users", response_model=AgentOut, status_code=201)
def create_user(payload: AgentCreate, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_roles("admin"))):
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    if db.query(models.Agent).filter(models.Agent.email == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already exists")
    role = db.query(models.Role).filter(models.Role.name == payload.role).first()
    agent = models.Agent(
        name=payload.name, email=payload.email.lower(),
        password_hash=security.hash_password(payload.password),
        role_id=role.role_id, is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _to_out(agent)


@router.patch("/users/{agent_id}/toggle", response_model=AgentOut)
def toggle_user(agent_id: str, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_roles("admin"))):
    a = db.query(models.Agent).filter(models.Agent.agent_id == agent_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="User not found")
    if a.agent_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    a.is_active = not a.is_active
    db.commit()
    db.refresh(a)
    return _to_out(a)
