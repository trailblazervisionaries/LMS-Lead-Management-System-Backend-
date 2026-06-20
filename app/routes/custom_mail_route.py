from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.config.database import get_db
from app.services.custom_mailService import CustomMailService
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.schemas.User_schemas import ComposeEmailRequest, ComposeBulkEmailRequest, ComposeBulkEmailToUsers
import logging 
logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/email/compose")
async def compose_and_send_email(
    request: Request, 
    data: ComposeEmailRequest
):
    if request.state.user.role not in ["admin", "assistant"]:
        raise HTTPException(403, "Unauthorized to send custom emails")
        
    return await CustomMailService.send_custom_email_(data.email_to, data.subject, data.body)


@router.post("/bulk-email")
async def compose_bulk_and_send_email(
    request: Request, 
    data: ComposeBulkEmailRequest
):
    if request.state.user.role not in ["admin", "assistant"]:
        raise HTTPException(403, "Unauthorized to send custom emails")
        
    return await CustomMailService.send_bulk_custom_email_(data.email_to, data.subject, data.body)


@router.post("/bulk/each-lead-users/{admin_id}")
async def compose_bulk_and_send_email_to_users(
    request: Request, 
    admin_id: str,
    data: ComposeBulkEmailToUsers,
    db: Session = Depends(get_db)
):
    if request.state.user.role not in ["admin", "assistant"]:
        raise HTTPException(403, "Unauthorized to send custom emails")
        
    return await CustomMailService.send_bulk_custom_email_to_all_users(db, admin_id, data.subject, data.body)


