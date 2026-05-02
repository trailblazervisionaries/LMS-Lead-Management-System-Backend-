from pydantic import BaseModel
from typing import Any, List, Optional
from datetime import datetime


class FormTemplateCreate(BaseModel):
    schema_definition: List[dict]

    class Config:
        from_attributes = True


class FormTemplateUpdate(BaseModel):
    collected_from: Optional[str] = None
    schema_definition: Optional[List[dict]] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True


class FormTemplateResponse(BaseModel):
    id: str
    admin_id: str
    collected_from: str
    schema_definition: List[dict]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FormSnippetResponse(BaseModel):
    template_id: str
    snippet: str

    class Config:
        from_attributes = True
