"""Auth router — login (FR-001) for both internal users and customers."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.core import security
from app.schemas import LoginResponse, UserOut
from app.core.security import get_current_user, CurrentUser

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form.username.strip().lower()

    # Try internal user (agent/manager/executive/admin) first, then customer.
    agent = db.query(models.Agent).filter(models.Agent.email == email).first()
    if agent and security.verify_password(form.password, agent.password_hash):
        if not agent.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")
        token = security.create_access_token(agent.agent_id, agent.role.name, "agent")
        return LoginResponse(
            access_token=token,
            user=UserOut(id=agent.agent_id, name=agent.name, email=agent.email, role=agent.role.name),
        )

    customer = db.query(models.Customer).filter(models.Customer.email == email).first()
    if customer and security.verify_password(form.password, customer.password_hash):
        token = security.create_access_token(customer.customer_id, "customer", "customer")
        return LoginResponse(
            access_token=token,
            user=UserOut(id=customer.customer_id, name=customer.name, email=customer.email, role="customer"),
        )

    raise HTTPException(status_code=401, detail="Invalid email or password")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(get_current_user)):
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role)
