from pydantic import BaseModel
from typing import Any, List, Optional
from datetime import datetime, date

class AuditResponse(BaseModel):
    id : str
    entity_name : str
    entity_id : str
    log_type : str
    prev_data : Optional[dict] = None
    new_data : Optional[dict] = None
    added_by : str
    admin_id : str
    created_at : datetime

    class Config:
        from_attributes = True

class ListAuditResponse(BaseModel):
    items: list[AuditResponse]
    total_count: int
    page: int
    size: int

    class Config:
        from_attributes = True

class UniqueAuditTypesResponse(BaseModel):
    audit_types: List[str]

    class Config:
        from_attributes = True

class DeleteAuditRecordsRequest(BaseModel):
    start_date: date
    end_date: date







