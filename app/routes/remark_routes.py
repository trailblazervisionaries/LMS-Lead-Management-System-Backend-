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

# add remark for followups and some other things
