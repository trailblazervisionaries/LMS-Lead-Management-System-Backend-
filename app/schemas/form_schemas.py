from pydantic import BaseModel
from typing import Any, List, Optional
from datetime import datetime


class FormTemplateCreate(BaseModel):
    schema_definition: dict

    class Config:
        from_attributes = True


class FormTemplateUpdate(BaseModel):
    schema_definition: Optional[dict] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True


class FormTemplateResponse(BaseModel):
    id: str
    admin_id: str
    schema_definition: Optional[dict]
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
