from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, UploadFile, File
from app.config.database import get_db
from app.services.lead_service import LeadService
from app.schemas.Lead_schemas import (
    LeadResponseModel,
    LeadStatusUpdate,
    LeadHistoryAndRemarks,
    UpdateRemark,
    LeadRemarkResponse
)
from sqlalchemy.ext.asyncio import AsyncSession as Session
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/assistant/followups/{start_date}/{end_date}", response_model=list[dict])
async def get_assistant_followups(request: Request, start_date: str, end_date: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code=403, detail="Only assistants can read followups")
    followups = await LeadService.get_todays_followups(db, start_date, end_date, assistant_id=request.state.user.user_id)
    return [
        {column.name: getattr(item, column.name) for column in item.__table__.columns}
        for item in followups
    ]


@router.post("/assistant/leads/{lead_id}/add", response_model=LeadHistoryAndRemarks)
async def add_new_remark_and_status(lead_id: str, data: LeadStatusUpdate, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code=403, detail="Only assistants or admins can add lead status")
    result = await LeadService.add_new_remark_and_status(db, lead_id, request.state.user.user_id, role, data)
    return LeadHistoryAndRemarks.model_validate(result)


@router.get("/assistant/leads/{lead_id}/fetch", response_model=LeadHistoryAndRemarks)
async def get_lead_stats_and_remarks(request: Request, lead_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code=403, detail="Only assistants or admins can get lead status and remarks")
    result = await LeadService.get_lead_history_and_remarks(db, lead_id)
    return LeadHistoryAndRemarks.model_validate(result)


@router.put("/assistant/{lead_id}/update/{remark_id}", response_model = LeadRemarkResponse)
async def update_the_remarks_data(request: Request,  data: UpdateRemark, lead_id: str, remark_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant","admin"}:
        raise HTTPException(status_code=403, detials="Only assistants or admins can update lead remarks")
    result = await LeadService.update_the_remarks_data(db, lead_id, remark_id, data)
    return LeadRemarkResponse.model_validate(result)


@router.put("/assistant/{lead_id}/mark/{remark_id}", response_model = LeadRemarkResponse)
async def mark_remarks_data_completed_(request: Request, lead_id: str, remark_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant","admin"}:
        raise HTTPException(status_code=403, detials="Only assistants or admins can update lead remarks")
    result = await LeadService.mark_remarks_data_completed(db, lead_id, remark_id)
    return LeadRemarkResponse.model_validate(result)


@router.delete("/assistant/delete/{lead_id}/mark/{remark_id}", response_model = LeadRemarkResponse)
async def mark_remarks_data_deleted_(request: Request, lead_id: str, remark_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant","admin"}:
        raise HTTPException(status_code=403, detials="Only assistants or admins can deleted lead remarks")
    result = await LeadService.mark_delete_remark_data(db, lead_id, remark_id)
    return LeadRemarkResponse.model_validate(result)






