"""FastAPI routes for teaching pipeline demo — isolated from /chat."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.teaching.api_basics import api_basics_router
from backend.teaching.deps import get_teaching_db, get_teaching_llm
from backend.teaching.pipeline import run_teaching_pipeline
from langchain_openai import ChatOpenAI

router = APIRouter(prefix="/teaching", tags=["teaching"])

router.include_router(api_basics_router)


class TeachingTraceRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_email: str = Field(default="demo@oxforduniversity.com")

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("message cannot be blank")
        return s


class TeachingTraceResponse(BaseModel):
    run_id: str
    session_id: str
    assistant_response: str
    steps: list


@router.post("/pipeline/trace", response_model=TeachingTraceResponse)
def post_teaching_trace(
    body: TeachingTraceRequest,
    db: Session = Depends(get_teaching_db),
    llm: ChatOpenAI = Depends(get_teaching_llm),
):
    """
    Run full teaching pipeline and return step-by-step trace for UI (Next / Run all).
    """
    try:
        return run_teaching_pipeline(
            message=body.message,
            user_email=body.user_email,
            db=db,
            llm=llm,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
