import os
import base64
import httpx
from datetime import datetime, time, timedelta
from fastapi import HTTPException, status
from dotenv import load_dotenv
from app.models.meeting_model import MeetingData
from app.schemas.meeting_schemas import MeetingCreateResponse, MeetingCreateRequest, MeetingUpdateRequest
from app.templates.send_template_mail import MailTemplatesService
from app.backgroundTasks.MonitorAsync import MonitorAsync
from app.models.audit_model import AuditLogs
from sqlalchemy import select, func, case
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
    async def create_zoom_meeting(db, assistant_id: str, payload: MeetingCreateRequest, admin_id):
        """
        Creates a scheduled Zoom meeting link using the Zoom Granular Scopes API.
        """
        access_token = await MeetingService.get_zoom_access_token()
        
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

                saved_data = await MeetingData.save_meeting_detials(db, assistant_id, payload.lead_id, data, admin_id)
                await AuditLogs.add_audit_log(
                    db = db,
                    entity_name = "Meeting",
                    entity_id = saved_data.id,
                    log_type = "Add",
                    prev_data = None,
                    new_data =  saved_data.to_dict(),
                    added_by = assistant_id,
                    admin_id = admin_id
                )
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
    async def update_zoom_meeting(db, assistant_id: str, meeting_id: int, payload: MeetingUpdateRequest, admin_id):
            """
            Updates details of an existing Zoom meeting and triggers an update email.
            """
            access_token = await MeetingService.get_zoom_access_token()

            zoom_url = f"https://zoom.us{meeting_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

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
                    await AuditLogs.add_audit_log(
                        db = db,
                        entity_name = "Meeting",
                        entity_id = updated_data.id,
                        log_type = "Update",
                        prev_data = None,
                        new_data =  updated_data.to_dict(),
                        added_by = assistant_id,
                        admin_id = admin_id
                    )
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
    async def cancel_zoom_meeting(db, meeting_id: int, recipient_email: str, topic: str, user_id, admin_id):
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
                    await AuditLogs.add_audit_log(
                        db = db,
                        entity_name = "Meeting",
                        entity_id = deleted_data.id,
                        log_type = "Deleted",
                        prev_data = deleted_data.to_dict(),
                        new_data =  {"user_id": user_id, "meeting_id": meeting_id, "detials":"meeting data deleted successfully"},
                        added_by = user_id,
                        admin_id = admin_id
                    )
                    return {200, f"meeting with meeting_id : {meeting_id} is deleted Successfully."}
                except httpx.HTTPStatusError as exc:
                    raise HTTPException(
                        status_code=exc.response.status_code, detail=f"Zoom Deletion Error: {exc.response.text}"
                    )
                
        

    async def get_meet_data_by_lead_id_assistant_id(db, lead_id, assistant_id):
        stmt = (select(MeetingData).where(MeetingData.lead_id == lead_id, MeetingData.added_by == assistant_id))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
        
        

    async def get_analytics_for_admin_or_assistant(
        db, 
        start_date: str, 
        end_date: str, 
        admin_id: str = None, 
        assistant_id: str = None
    ):
        try:
            start_parsed_date = datetime.strptime(start_date, "%d%m%Y").date()
            end_parsed_date = datetime.strptime(end_date, "%d%m%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Expected 'ddmmyyyy' string (e.g., 20052026).")

        from_date = datetime.combine(start_parsed_date, time.min)
        end_date_time = datetime.combine(end_parsed_date, time.max)

        completed_case = case((MeetingData.is_completed == True, 1))
        uncompleted_case = case((MeetingData.is_completed == False, 1))

        query = db.query(
            func.count(MeetingData.id).label("total_meeting"),
            func.count(completed_case).label("total_completed"),
            func.count(uncompleted_case).label("total_uncompleted")
        ).filter(
            MeetingData.start_time >= from_date,
            MeetingData.start_time <= end_date_time
        )

        if admin_id:
            query = query.filter(MeetingData.admin_id == admin_id)
        if assistant_id:
            query = query.filter(MeetingData.added_by == assistant_id)

        result = query.first()

        return {
            "total_meeting": result.total_meeting or 0,
            "total_completed": result.total_completed or 0,
            "total_uncompleted": result.total_uncompleted or 0
        }

