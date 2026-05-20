from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, UploadFile, File
from app.config.database import get_db
from app.services.lead_service import LeadService
from app.schemas.Lead_schemas import (
    LeadCreate,
    LeadResponseModel,
    LeadStatusUpdate,
    LeadPaginationResponse,
    LeadAssignResponse,
    NewAssignment
)
from sqlalchemy.ext.asyncio import AsyncSession as Session
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/add", response_model=LeadResponseModel)
async def submit_lead(data: LeadCreate = Depends(LeadCreate.as_form), db: Session = Depends(get_db)):
    result = await LeadService.add_new_lead(db, data)
    return result

@router.post("/upload/{template_id}/{admin_id}")
async def upload_excel_leads(
    template_id: str,
    admin_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    return await LeadService.upload_leads(
        db=db, 
        template_id=template_id, 
        admin_id=admin_id, 
        file=file
    )


@router.get("/admin/leads", response_model=LeadPaginationResponse)
async def list_admin_leads(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view leads")
    result = await LeadService.get_leads_for_admin(db, request.state.user.user_id, page, size)
    return result

#  for the automatic assignment of lead to the assistant ========
@router.post("/admin/assign-unassigned", response_model=LeadAssignResponse)
async def assign_unassigned_leads(request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can assign leads")
    result = await LeadService.assign_unassigned_leads(db, request.state.user.user_id)
    return result


# For the assign the lead to the specific assistant or change the previous assigned assistant ==========
@router.post("/admin/force-assign", response_model=dict)
async def assign_unassigned_leads_(request: Request, data = NewAssignment, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can assign leads")
    result = await LeadService.assign_unassigned_leads_to_specific_user(db, request.state.user.user_id, data)
    return result



@router.post("/assistant/leads/{lead_id}/update", response_model=LeadResponseModel)
async def update_lead_status(lead_id: str, data: LeadStatusUpdate, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code=403, detail="Only assistants or admins can update lead status")
    result = await LeadService.update_lead(db, lead_id, request.state.user.user_id, role, data)
    return result


@router.get("/assistant/leads", response_model=LeadPaginationResponse)
async def list_assistant_leads(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    role = request.state.user.role
    if role != "assistant":
        raise HTTPException(status_code=403, detail="Only assistants can list assigned leads")
    return await LeadService.get_leads_for_assistant(db, request.state.user.user_id, page, size)


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


@router.get("/lead/{lead_id}/history", response_model=list[dict])
async def get_lead_history(lead_id: str, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code=403, detail="Only assistants or admins can view lead history")
    history = await LeadService.get_lead_history(db, lead_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return history


@router.delete("/assistant/{lead_d}")
async def delete_lead_data(lead_id: str, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code=403, detail="Only admin or Assistant can delete the lead")
    result = await LeadService.delete_lead_permanentaly(db, lead_id)
    return result


@router.delete("assistant/mark-del/{lead_id}")
async def mark_delete_lead_data(lead_id: str, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code = 403, detail = "Only admin, assistant can access this route ok")
    result = await LeadService.lead_mark_deleted(db, lead_id)
    return result






