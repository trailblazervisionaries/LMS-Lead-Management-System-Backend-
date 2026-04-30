from fastapi import Request, Response, HTTPException, status
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy.exc import IntegrityError
from app.core.utils_functions import generate_id, generate_alphanumeric_password
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.core.auth import create_auth_token
from dotenv import load_dotenv
from app.models.user_model import Users
from app.core.hash import hash_password, verify_password
from app.models.address_model import Address
# from app.templates.send_template_mail import MailTemplatesService
# from app.backgroundTasks.MonitorAsync import MonitorAsync
from app.schemas.User_schemas import UserCreate, UserUpdate
import traceback
import os
import logging

load_dotenv()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"


class AssistantService:
    
    async def create_assistant(cls, db, admin_id, data: UserCreate):
        assistant = Users.get_by_email(cls, db, data.email)
        if assistant:
            raise HTTPException(500, "Email Already in database please try with another one or contact the team")
        try:
            temp_password = generate_alphanumeric_password()
            hashed_password = hash_password(temp_password)
            new_assistant = Users(
                user_id = generate_id(data.name),
                name = data.name,
                role = data.role,
                email = data.email,
                password= hashed_password,
                admin_id = admin_id
            )

            new_assistant.address = Address(
                user_id=new_assistant.user_id,  
                address_line_1=data.address_line_1,
                address_line_2=data.address_line_2,
                city=data.city,
                province=data.province,
                country=data.country,
                postal_code=data.postal_code,
            )

            db.add(new_assistant)
            await db.commit()
            logger.info("AssistantService: New user assistant is added successfully")
            await db.refresh(new_assistant, ["address"])
            # MonitorAsync.deferred(
            #     MailTemplatesService.send_credentials_template,
            #     new_assistant.email,
            #     new_assistant.fname,
            #     "assistant",
            #     temp_password,
            # )
            return new_assistant
        
        except IntegrityError as e:
            await db.rollback()
            logger.error("AdminService: IntegrityError creating admin: %s ", e) 
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integrity error while creating admin"
            )   
 
        except Exception as e:
            await db.rollback()
            logger.exception("Unexpected error creating admin")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )       
        


    @classmethod
    async def update_assistant(cls, db, user_id: str, data: UserUpdate, request: Request):
        assistant = await Users.get_by_id(cls, db, user_id)

        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AssistantService: Assistant not found"
            )

        try:
            if hasattr(data, "email") and data.email is not None:
                assistant.email = data.email

            if hasattr(data, "role") and data.role is not None:
                assistant.role = data.role
            
            if hasattr(data, "name") and data.name is not None:
                assistant.name = data.name

            admin_data = data.model_dump(
                exclude_unset=True,
                exclude={"address", "email", "role", "name"}
            )

            for field, value in admin_data.items():
                setattr(assistant, field, value)

            if data.address:
                address_data = data.address.model_dump(exclude_unset=True)

                if assistant.address:
                    for field, value in address_data.items():
                        setattr(assistant.address, field, value)
                else:
                    assistant.address = Address(
                        user_id=assistant.user_id,
                        **address_data
                    )

            await db.commit()
            await db.refresh(assistant, ["address"])
            logger.info("AssistantService: assistant data updated successfully")
            return assistant

        except Exception:
            await db.rollback()
            logger.error("AssistantService: Error updating assistant detials")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating assistant details"
            )
        

    @classmethod
    async def get_my_info(cls, db, user_id):
        return await Users.get_my_info(cls, db, user_id)


    @classmethod
    async def get_all_paginated(cls, db: Session, user_id: str, page: int, size: int):
        count_stmt = select(func.count()).select_from(Users).filter(Users.admin_id == user_id, Users.is_deleted == False, Users.is_active == True)
        total_count = await db.scalar(count_stmt) or 0
        
        # 2. Get the paginated items
        offset = (page - 1) * size
        query_stmt = (
            select(Users)
            .options(selectinload(Users.address)) 
            .where(Users.admin_id == user_id, Users.is_deleted == False, Users.is_active == True)
            .offset(offset)
            .limit(size)
        )
        result = await db.execute(query_stmt)
        assistants = result.scalars().all()
        
        return assistants, total_count

