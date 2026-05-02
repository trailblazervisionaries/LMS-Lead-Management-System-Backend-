from pydantic import BaseModel
from typing import Any, List, Optional
from datetime import datetime


class LeadCreate(BaseModel):
    template_id: str
    collected_from: Optional[str] = "website"
    submitted_data: dict[str, Any]

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
