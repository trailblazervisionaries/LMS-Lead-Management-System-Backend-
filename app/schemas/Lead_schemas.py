from pydantic import BaseModel
from typing import Any, List, Optional
from datetime import datetime
from fastapi import Form, Depends
import json



class LeadCreate(BaseModel):
    template_id: str
    collected_from: Optional[str] = "website"
    submitted_data: dict[str, Any]

    @classmethod
    def as_form(
        cls,
        template_id: str = Form(...),
        collected_from: Optional[str] = Form("website"),
        submitted_data: str = Form(...)
    ):
        return cls(
            template_id=template_id,
            collected_from=collected_from,
            submitted_data=json.loads(submitted_data)
        )
    class Config:
        from_attributes = True


class LeadResponseModel(BaseModel):
    id: str
    template_id: str
    admin_id: str
    submitted_data: dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadStatusUpdate(BaseModel):
    status: Optional[str] = None
    remarks: Optional[str] = None
    next_follow_up_date: Optional[datetime] = None
    is_completed: Optional[bool] = None

    class Config:
        from_attributes = True


class LeadHistoryItem(BaseModel):
    id: str
    lead_id: str
    status: str
    changed_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LeadRemarkItem(BaseModel):
    id: str
    for_lead: str
    remarks: Optional[str] = None
    next_follow_up_date: Optional[datetime] = None
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LeadPaginationResponse(BaseModel):
    items: List[LeadResponseModel]
    total_count: int
    page: int
    size: int
    total_pages: int

    class Config:
        from_attributes = True


class LeadAssignResponse(BaseModel):
    leads_assigned: int
    assistants_involved: int

    class Config:
        from_attributes = True


class NewAssignment(BaseModel):
    assistant_id: str
    lead_id: str

    