from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.document import Document
from app.db.models.feedback import Feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])

FEEDBACK_MODEL_CONFIG = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)
WorkflowType = Literal["ask", "memo", "extract_kpis", "extract_risks", "timeline", "agent"]
FeedbackValue = Literal["positive", "negative"]


class FeedbackCreateRequest(BaseModel):
    workflow_type: WorkflowType
    document_id: int = Field(ge=1)
    target_id: int | None = Field(default=None, ge=1)
    target_reference: str | None = Field(default=None, min_length=1, max_length=255)
    feedback_value: FeedbackValue
    reason: str | None = Field(default=None, min_length=1, max_length=1200)
    reviewer_note: str | None = Field(default=None, min_length=1, max_length=2000)

    model_config = FEEDBACK_MODEL_CONFIG

    @model_validator(mode="after")
    def validate_reason_for_negative_feedback(self) -> "FeedbackCreateRequest":
        if self.feedback_value == "negative" and self.reason is None:
            raise ValueError("reason is required when feedback_value is negative.")
        return self


class FeedbackResponse(BaseModel):
    id: int
    workflow_type: WorkflowType
    document_id: int
    target_id: int | None
    target_reference: str | None
    feedback_value: FeedbackValue
    reason: str | None
    reviewer_note: str | None
    created_at: datetime

    model_config = FEEDBACK_MODEL_CONFIG


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    payload: FeedbackCreateRequest,
    db: Session = Depends(get_db),
) -> Feedback:
    document = db.get(Document, payload.document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    feedback = Feedback(
        workflow_type=payload.workflow_type,
        document_id=payload.document_id,
        target_id=payload.target_id,
        target_reference=payload.target_reference,
        feedback_value=payload.feedback_value,
        reason=payload.reason,
        reviewer_note=payload.reviewer_note,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return feedback


@router.get("", response_model=list[FeedbackResponse])
async def list_feedback(
    workflow_type: WorkflowType | None = Query(default=None),
    document_id: int | None = Query(default=None, ge=1),
    feedback_value: FeedbackValue | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[Feedback]:
    query = db.query(Feedback)

    if workflow_type is not None:
        query = query.filter(Feedback.workflow_type == workflow_type)
    if document_id is not None:
        query = query.filter(Feedback.document_id == document_id)
    if feedback_value is not None:
        query = query.filter(Feedback.feedback_value == feedback_value)

    return (
        query.order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .limit(limit)
        .all()
    )
