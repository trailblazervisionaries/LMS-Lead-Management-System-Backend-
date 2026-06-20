from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, UploadFile, File
from app.config.database import get_db
from app.services.lead_service import LeadService
from app.schemas.Lead_schemas import (
    LeadCreate,
    LeadResponseModel,
    LeadStatusUpdate,
    UpdateLead,
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


@router.put("/update/lead-response/{lead_id}", response_model=LeadResponseModel)
async def update_lead_response(request: Request, data: UpdateLead, lead_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(403, "You don not have any such authority to make changes.")
    result = await LeadService.update_lead_response_data(db, lead_id, request.state.user.user_id, data)
    return LeadResponseModel.model_validate(result)

@router.get("/fetch/{lead_id}", response_model = LeadResponseModel)
async def fetch_lead_by_lead_id(request: Request, lead_id: str, db: Session = Depends(get_db)):
    lead = await LeadService.get_lead_by_id(db, lead_id)
    return LeadResponseModel.model_validate(lead)


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
async def assign_unassigned_leads_(request: Request, data: NewAssignment, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can assign leads")
    result = await LeadService.assign_unassigned_leads_to_specific_user(db, request.state.user.user_id, data)
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



@router.get("/lead/{lead_id}/history", response_model=list[dict])
async def get_lead_history(lead_id: str, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code=403, detail="Only assistants or admins can view lead history")
    history = await LeadService.get_lead_history(db, lead_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return history


@router.delete("/assistant/{lead_id}")
async def delete_lead_data(lead_id: str, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code=403, detail="Only admin or Assistant can delete the lead")
    result = await LeadService.delete_lead_permanentaly(db, lead_id, request.state.user.user_id)
    return result


@router.delete("/assistant/mark-del/{lead_id}")
async def mark_delete_lead_data(lead_id: str, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in {"assistant", "admin"}:
        raise HTTPException(status_code = 403, detail = "Only admin, assistant can access this route ok")
    result = await LeadService.lead_mark_deleted(db, lead_id)
    return result


@router.get("/lead-counters")
async def get_dashboard_counters(request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user.user_id
    role = request.state.user.role

    if role == "admin":
        # Admins view aggregate analytics for all leads they manage
        stats = await LeadService.get_lead_status_analytics(db, admin_id=user_id)
    elif role == "assistant":
        # Assistants view strictly what is assigned to them
        stats = await LeadService.get_lead_status_analytics(db, assistant_id=user_id)
    else:
        raise HTTPException(status_code=403, detail="Unauthorized role access profile")
    return stats



