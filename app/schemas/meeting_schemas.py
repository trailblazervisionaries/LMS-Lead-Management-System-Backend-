from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class MeetingCreateRequest(BaseModel):
    lead_id : str = Field(..., description = "lead id for the meeting.")
    topic: str = Field(default="Automated Consultation", description="Topic of the meeting")
    start_time: str = Field(..., description="ISO 8601 format string, e.g., '2026-06-15T14:30:00Z'")
    duration_minutes: int = Field(default=30, description="Duration of the meeting in minutes")
    recipient_email: EmailStr = Field(..., description="The user's email address to receive the link")



class MeetingUpdateRequest(BaseModel):
    topic: Optional[str] = Field(None, description="New topic of the meeting")
    start_time: Optional[str] = Field(None, description="New ISO 8601 format string time")
    duration_minutes: Optional[int] = Field(None, description="New duration in minutes")



class MeetingDeleteRequest(BaseModel):
    topic: Optional[str] = Field(None, description="topic of the meeting")
    recipient_email: EmailStr = Field(..., description="The user's email address to receive the cancle message.")



class MeetingCreateResponse(BaseModel):
    meeting_id: str
    public_join_url: str
    host_start_url: str
    topic: str
    start_time: str
    email_status: str | None = None

    class Config:
        from_attributes = True


class MeetingResponse(BaseModel):
    id: str
    lead_id: str
    meeting_id: str
    public_join_url: str
    host_start_url: str
    duration: int
    topic: str
    start_time: str
    created_at: datetime
    added_by: str

    class Config:
        from_attributes = True



