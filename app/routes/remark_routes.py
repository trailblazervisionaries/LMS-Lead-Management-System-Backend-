from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, UploadFile, File
from app.config.database import get_db
from app.services.lead_service import LeadService
from app.schemas.Lead_schemas import (
    LeadResponseModel,
    LeadStatusUpdate,
    LeadHistoryAndRemarks
)
from sqlalchemy.ext.asyncio import AsyncSession as Session
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/assistant/followups/{date}", response_model=list[dict])
async def get_assistant_followups(request: Request, date: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "assistant":
        raise HTTPException(status_code=403, detail="Only assistants can read followups")
    followups = await LeadService.get_todays_followups(db, date, assistant_id=request.state.user.user_id)
    return [
        {column.name: getattr(item, column.name) for column in item.__table__.columns}
        for item in followups
    ]


@router.post("/assistant/leads/{lead_id}/update", response_model=LeadResponseModel)
async def update_lead_status(lead_id: str, data: LeadStatusUpdate, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code=403, detail="Only assistants or admins can update lead status")
    result = await LeadService.update_lead(db, lead_id, request.state.user.user_id, role, data)
    return result

@router.get("/assistant/leads/{lead_id}/fetch", response_model=LeadHistoryAndRemarks)
async def get_lead_stats_and_remarks(request: Request, lead_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code=403, detail="Only assistants or admins can update lead status")
    result = await LeadService.get_lead_history_and_remarks(db, lead_id)
    return LeadHistoryAndRemarks.model_validate(result)
