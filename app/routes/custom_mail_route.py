from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.config.database import get_db
from app.services.custom_mailService import CustomMailService
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.schemas.User_schemas import ComposeEmailRequest
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
        
    return CustomMailService.send_custom_email_(data.email_to, data.body)


