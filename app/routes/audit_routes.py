from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query, Form
from app.config.database import get_db
from app.services.audit_service import AuditService
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.schemas.audit_schema import AuditResponse, ListAuditResponse, DeleteAuditRecordsRequest, UniqueAuditTypesResponse
from datetime import datetime
from typing import Optional
import logging
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/get-logs/{admin_id}", response_model=ListAuditResponse)
async def get_all_logs(
        admin_id: str, 
        request: Request,
        assistant_id: Optional[str] = Form(None),
        start_date: Optional[str] = Form(None),
        end_date: Optional[str] = Form(None), 
        page: int = Query(default = 1, ge=1),
        size: int = Query(default = 20, ge = 1, le = 100),
        db: Session = Depends(get_db)
    ):

    role = request.state.user.role
    if role not in ["admin","assistant"]:
        raise HTTPException(403, "You do not have permission to perform this operation")
    parsed_start = None
    parsed_end = None
    
    if start_date:
        parsed_start = datetime.strptime(start_date, "%d%m%Y")
    if end_date:
        parsed_end = datetime.strptime(end_date, "%d%m%Y").replace(hour=23, minute=59, second=59)

    skip = (max(1, page) - 1) * size
    logs, total_count = await AuditService.get_all_logs_by_date_range(db, admin_id, parsed_start, parsed_end, assistant_id, skip=skip, limit=size)
    return {
        "items": logs,
        "total_count": total_count,
        "page": page,
        "size": size
    }


@router.delete("/delete-logs/{admin_id}")
async def delete_audit_logs(admin_id: str, request: Request, data: DeleteAuditRecordsRequest ,db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(403, "you are not authorise to perform this operation.")
    parsed_start = None
    parsed_end = None
    
    if data.start_date:
        parsed_start = datetime.strptime(data.start_date, "%d%m%Y")
    if data.end_date:
        parsed_end = datetime.strptime(data.end_date, "%d%m%Y").replace(hour=23, minute=59, second=59)
    deleted_count = await AuditService.delete_audit_records(db, admin_id, parsed_start, parsed_end)
    return deleted_count


@router.get("/get-all-type/{admin_id}", response_model = UniqueAuditTypesResponse)
async def get_all_unique_type(request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role not in ["admin", "assistant"]:
        raise HTTPException(403, "You are not authorise to perform this operation")
    unique_types = await AuditService.get_all_unique_audit_types(db)
    return {
        "audit_types": unique_types
    }



@router.get("/audit-logs-type/{admin_id}", response_model=ListAuditResponse)
async def get_audit_logs(
    request:Request,
    admin_id: str,
    entity_type: str = Form(...),
    db: Session = Depends(get_db),
    assistant_id : Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Items per page")
):
    role = request.state.user.role
    if role not in ["admin","assistant"]:
        raise HTTPException(403, "you are not authorise to perform this operation")
    parsed_start = None
    parsed_end = None
    
    if start_date:
        parsed_start = datetime.strptime(start_date, "%d%m%Y")
    if end_date:
        parsed_end = datetime.strptime(end_date, "%d%m%Y").replace(hour=23, minute=59, second=59)
    skip = (max(1, page) - 1) * size
    # print(entity_type)
    logs, total_count = await AuditService.get_all_logs_by_date_range_and_entiry_type(
        db, 
        admin_id,
        assistant_id,
        entity_type = entity_type,
        skip=skip, 
        limit=size, 
        start_date=parsed_start, 
        end_date=parsed_end
    )
    
    return {
        "items": logs,
        "total_count": total_count,
        "page": page,
        "size": size
    }

