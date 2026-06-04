import os
import base64
import httpx
from datetime import datetime
from fastapi import HTTPException, status
from dotenv import load_dotenv
from app.models.meeting_model import MeetingData
from app.schemas.meeting_schemas import MeetingCreateResponse, MeetingCreateRequest, MeetingUpdateRequest
from app.templates.send_template_mail import MailTemplatesService
from app.backgroundTasks.MonitorAsync import MonitorAsync
load_dotenv()
import logging 
logger = logging.getLogger(__name__)

ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")


class MeetingService:

    @staticmethod
    async def get_zoom_access_token() -> str:
        """
        Requests a short-lived bearer token from Zoom using Server-to-Server credentials.
        """
        logger.info("MeetingService: Trying to fetch the Zoom access token.")
        api_credentials = f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(api_credentials.encode()).decode()
        
        url = "https://zoom.us/oauth/token"
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = "grant_type=account_credentials&account_id=" + ZOOM_ACCOUNT_ID
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, content=data)
                response.raise_for_status()
                logger.info("MeetingService: Zoom meeting access token fetched successfully")
                return response.json()["access_token"]
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Your local server cannot reach zoom.us. Please check your system DNS or internet connection."
                )
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Zoom Authentication rejected credentials: {exc.response.text}"
                )


    @staticmethod
    async def create_zoom_meeting(db, assistant_id: str, payload: MeetingCreateRequest):
        """
        Creates a scheduled Zoom meeting link using the Zoom Granular Scopes API.
        """
        access_token = await MeetingService.get_zoom_access_token()
        
        # FIX: Use correct Zoom API endpoint for creating meetings
        zoom_url = "https://api.zoom.us/v2/users/me/meetings"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        meeting_data = {
            "topic": payload.topic,
            "type": 2, 
            "start_time": payload.start_time,
            "duration": payload.duration_minutes,
            "settings": {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": True,
                "waiting_room": True  
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(zoom_url, json=meeting_data, headers=headers)
                response.raise_for_status()
                logger.info("Meetingdata: New meeting created and link generated successfully.")
                data = response.json()

                saved_data = await MeetingData.save_meeting_detials(db, assistant_id, payload.lead_id, data)
                if not saved_data:
                    raise HTTPException(500, "There might be some issues in saving the meeting data in db.")
                logger.info("MeetingService: new meeting data is saved successfully into the database.")
                MonitorAsync.deferred(
                    MailTemplatesService.send_meeting_invite,
                    payload.recipient_email,
                    data["id"],
                    data["topic"],
                    data["start_time"],
                    data["duration"],
                    data["join_url"]
                )
                logger.info("MeetingService: meeting link is sent to the queue so joining link sent to the end user.")
                return MeetingCreateResponse(
                    meeting_id=data["id"],
                    public_join_url=data["join_url"],       
                    host_start_url=data["start_url"],     
                    topic=data["topic"],
                    start_time=data["start_time"],
                    email_status="Queued for delivery"
                )
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Your local server cannot reach api.zoom.us. Please check your system DNS or internet connection."
                )
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"Zoom API Error: {exc.response.text}"
                )
            
    @staticmethod
    async def update_zoom_meeting(db, assistant_id: str, meeting_id: int, payload: MeetingUpdateRequest):
            """
            Updates details of an existing Zoom meeting and triggers an update email.
            """
            access_token = await MeetingService.get_zoom_access_token()
            # Zoom API endpoint requires the /v2/meetings/ path
            zoom_url = f"https://zoom.us{meeting_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Build update payload dynamically based on what fields were passed
            update_data = {}
            if payload.topic is not None:
                update_data["topic"] = payload.topic
            if payload.start_time is not None:
                update_data["start_time"] = payload.start_time
            if payload.duration_minutes is not None:
                update_data["duration"] = payload.duration_minutes
            logger.info("MeetingService: Updated_data json prepared to make patch into the already created zoom meeting.")
            if not update_data:
                raise HTTPException(status_code=400, detail="No fields provided to update.")

            async with httpx.AsyncClient() as client:
                try:
                    patch_response = await client.patch(zoom_url, json=update_data, headers=headers)
                    patch_response.raise_for_status()
                    logger.info("MeetingService: meeting data updation completed successfully.")
                    # from Zoom to get the valid system configurations and runtime join_url strings.
                    get_response = await client.get(zoom_url, headers=headers)
                    get_response.raise_for_status()
                    data = get_response.json()

                    updated_data = await MeetingData.update_meeting_detials(db, assistant_id, payload.lead_id, data)
                    if not updated_data:
                        raise HTTPException(500, "There might be some issues in updating the meeting data in db.")
                    logger.info("MeetingData: Meeting data successfully updated inside the database.")
                    MonitorAsync.deferred(
                        MailTemplatesService.send_updated_meeting_invite,
                        payload.recipient_email,
                        data["id"],
                        data["topic"],
                        data["start_time"],
                        data["duration"],
                        data["join_url"]
                    )
                    logger.info("MeetingService: all the updated meeting info sent to the queue for the auto email sending.")
                    return MeetingCreateResponse(
                        meeting_id=data["id"],
                        public_join_url=data["join_url"],       
                        host_start_url=data["start_url"],     
                        topic=data["topic"],
                        start_time=data["start_time"],
                        email_status="Queued for delivery"
                    )
                except httpx.HTTPStatusError as exc:
                    raise HTTPException(
                        status_code=exc.response.status_code, detail=f"Zoom Update Error: {exc.response.text}"
                    )

                
    @staticmethod
    async def cancel_zoom_meeting(db, meeting_id: int, recipient_email: str, topic: str):
            """
            Deletes an existing Zoom meeting using its unique ID.
            """
            access_token = await MeetingService.get_zoom_access_token()
            zoom_url = f"https://zoom.us{meeting_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.delete(zoom_url, headers=headers)
                    response.raise_for_status()
                    
                    deleted_data = await MeetingData.delete_meeting_details(db, meeting_id)
                    if not deleted_data:
                        raise HTTPException(500, "There might be some issues in deleting the meeting data in db.")
                    MonitorAsync.deferred(
                        MailTemplatesService.send_cancel_meeting_info,
                        recipient_email,
                        meeting_id,
                        topic
                    )
                    return {200, f"meeting with meeting_id : {meeting_id} is deleted Successfully."}
                except httpx.HTTPStatusError as exc:
                    raise HTTPException(
                        status_code=exc.response.status_code, detail=f"Zoom Deletion Error: {exc.response.text}"
                    )
                
        





