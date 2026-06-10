from fastapi import APIRouter, Depends, Request, HTTPException
from app.config.database import get_db
from app.services.meeting_service import MeetingService
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.schemas.meeting_schemas import MeetingCreateRequest, MeetingCreateResponse, MeetingUpdateRequest, MeetingDeleteRequest, MeetingResponse
import logging 
logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create-meeting", response_model = MeetingCreateResponse)
async def create_new_meeting(request: Request, data: MeetingCreateRequest, db: Session = Depends(get_db)):
    assistant_id = request.state.user.user_id
    role = request.state.user.role
    if role != "assistant":
        raise HTTPException(403, "Sorry :( , You are not authorised to create the meeting.")
    return MeetingService.create_zoom_meeting(db, assistant_id, data, request.state.user.admin_id)


@router.patch("/update-meeting/{meeting_id}", response_model = MeetingCreateResponse)
async def update_meeting(request: Request, meeting_id: str, data: MeetingUpdateRequest, db: Session = Depends(get_db)):
    assistant_id = request.state.user.user_id
    role = request.state.user.role
    if role != "assistant":
        raise HTTPException(403, "Sorry :( , You are not authorised to update the meeting.")
    return MeetingService.update_zoom_meeting(db, assistant_id, meeting_id, data, request.state.user.admin_id)


@router.delete("/delete-meeting/{meeting_id}")
async def delete_meetings(request: Request, meeting_id: str, data: MeetingDeleteRequest, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "assistant":
        raise HTTPException(403, "Sorry :( , You are not authorised to delete the meeting.")
    return MeetingService.cancel_zoom_meeting(db, meeting_id, data.recipient_email, data.topic, request.state.user.admin_id)


@router.get("/get-meeting/{lead_id}", response_model = MeetingResponse)
async def get_meeting(request: Request, lead_id: str, db: Session = Depends(get_db)):
    assistant_id = request.state.user.user_id
    role = request.state.user.role
    if role != "assistant":
        raise HTTPException(403, "Sorry :( , You are not authorised to get the response")
    meet = MeetingService.get_meet_data_by_lead_id_assistant_id(db, lead_id, assistant_id)
    return MeetingResponse.model_validate(meet)





