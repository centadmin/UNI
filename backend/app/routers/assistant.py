"""GenAI knowledge assistant (FR-003).

Implements the RAG retrieval flow from the GenAI Design Document. Used by:
  * WF-01 Customer Portal — customer self-service chatbot
  * WF-02 Agent Workspace — "suggested reply" panel

Returns a grounded answer with a source citation, or escalates when no KB
content is relevant enough (guardrail).
"""
from fastapi import APIRouter, Depends
from app.core.security import get_current_user, CurrentUser
from app.ml.engine import assistant
from app.schemas import AssistantQuery, AssistantReply

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/ask", response_model=AssistantReply)
def ask(payload: AssistantQuery, user: CurrentUser = Depends(get_current_user)):
    result = assistant.answer(payload.query)
    return AssistantReply(**result)
