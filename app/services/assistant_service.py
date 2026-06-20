from fastapi import Request, Response, HTTPException, status
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy.exc import IntegrityError
from app.core.utils_functions import generate_id, generate_alphanumeric_password
from sqlalchemy import select, func, update
from datetime import datetime, timedelta
from app.core.auth import create_auth_token
from dotenv import load_dotenv
from app.models.user_model import Users
from app.core.hash import hash_password, verify_password
from app.models.address_model import Address
from app.models.audit_model import AuditLogs
from app.templates.send_template_mail import MailTemplatesService
from app.backgroundTasks.MonitorAsync import MonitorAsync
from app.schemas.User_schemas import UserCreate, UserUpdate
import traceback
import os
import logging

load_dotenv()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"


class AssistantService:
    @classmethod
    async def create_assistant(cls, db, admin_id, data: UserCreate):
        assistant = await Users.get_by_email(db, data.email)
        if assistant:
            raise HTTPException(500, "Email Already in database please try with another one or contact the team")
        try:
            # temp_password = generate_alphanumeric_password()
            temp_password = "qwerty123"
            hashed_password = hash_password(temp_password)
            logger.info("AssistantService: Assistant passed hashed successfully.")
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
            await AuditLogs.add_audit_log(
                db =db,
                entity_name="Assistant",
                entity_id = new_assistant.user_id,
                log_type = "ADD",
                prev_data = None,
                new_data = new_assistant.to_dict(),
                added_by = admin_id,
                admin_id = admin_id
            )
            MonitorAsync.deferred(
                MailTemplatesService.send_credentials_template,
                new_assistant.email,
                new_assistant.name,
                "assistant",
                temp_password,
            )
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
        assistant = await Users.get_by_id_with_address(db, user_id)
        old_data_snapshot = assistant.to_dict()
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="AssistantService: Assistant not found"
            )

        try:
            user_fields = {"name", "email"}
            address_fields = {
                "address_line_1", "address_line_2", "city", 
                "province", "country", "postal_code"
            }

            update_dict = data.model_dump(exclude_unset=True)

            for field in user_fields:
                if field in update_dict:
                    setattr(assistant, field, update_dict[field])

            address_update_data = {k: v for k, v in update_dict.items() if k in address_fields}
            
            if address_update_data:
                if not assistant.address:
                    assistant.address = Address(user_id=assistant.user_id)
                
                for field, value in address_update_data.items():
                    setattr(assistant.address, field, value)

            await AuditLogs.add_audit_log(
                db = db,
                entity_name="Assistant",
                entity_id = user_id,
                log_type = "Update",
                prev_data = old_data_snapshot,
                new_data = data.model_dump(mode="json"),
                added_by = user_id,
                admin_id = assistant.admin_id
            )

            await db.commit()
            await db.refresh(assistant, ["address"])
            
            logger.info("AssistantService: Assistant updated successfully")
            return assistant

        except Exception as e:
            await db.rollback()
            logger.error(f"AssistantService: Error updating assistant details: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Error updating assistant details"
            )


    @classmethod
    async def get_my_info(cls, db, user_id):
        return await Users.get_by_id_with_address(db, user_id)


    @classmethod
    async def get_all_paginated(cls, db: Session, user_id: str, page: int, size: int):
        count_stmt = select(func.count()).select_from(Users).filter(Users.admin_id == user_id, Users.is_deleted == False)
        total_count = await db.scalar(count_stmt) or 0

        offset = (page - 1) * size
        query_stmt = (
            select(Users)
            .options(selectinload(Users.address)) 
            .where(Users.admin_id == user_id, Users.is_deleted == False)
            .offset(offset)
            .limit(size)
        )
        result = await db.execute(query_stmt)
        assistants = result.scalars().all()
        logger.info("AssistantService: all assistant with pagination returned successfully.")
        return assistants, total_count


    @classmethod
    async def delete_assistant_account_by_id(cls, db, assistant_id):
        assistant = await Users.get_by_id(db, assistant_id)
        if not assistant:
            raise HTTPException(401, "Assistant Not Found or already deleted.")
        assistant.is_deleted = True
        assistant.is_active = False
        await db.commit()
        await db.refresh(assistant)
        logger.info("AssistantService: Assistant account deleted successfully.")
        return {
            "message": "Assistant is deleted and deactivated successfully."
        }


    # @classmethod
    # async def assign_new_admin_to_assistants(cls, db, old_admin_id, new_admin_id):
    #     stmt = (
    #         update(Users)
    #         .where(Users.admin_id == old_admin_id, Users.is_deleted == False)
    #         .values(admin_id=new_admin_id)
    #     )
    #     result = await db.execute(stmt)
    #     logger.info("AssistantService: Assign new admin inplace of old admin to all assistant.")
    #     if result.rowcount == 0:
    #         return {"message": "No assistants found for this admin."}
    #     await db.commit()
    #     return {
    #         "message": f"Admin ID updated for {result.rowcount} assistant(s)."
    #     }


    @classmethod
    async def mark_account_activated(cls, db, assistant_id):
        assistant = await Users.by_id(db, assistant_id)
        if not assistant:
            raise HTTPException(401, "Assistant Not Found.")
        assistant.is_active = True
        await db.commit()
        await db.refresh(assistant)
        await AuditLogs.add_audit_log(
                db = db,
                entity_name="Assistant",
                entity_id = assistant.user_id,
                log_type = "Update",
                prev_data = {"is_active": assistant.is_active},
                new_data = {"is_active": True},
                added_by = assistant.user_id,
                admin_id = assistant.admin_id
            )
        logger.info("AssistantService: Assistant account activated Successfully.")
        return {
            "message": "Assistant account activated successfully."
        }


    @classmethod
    async def mark_account_deactivated(cls, db, assistant_id):
        assistant = await Users.by_id(db, assistant_id)
        if not assistant:
            raise HTTPException(401, "Assistant not Found.")
        assistant.is_active = False
        await db.commit()
        await db.refresh(assistant)
        await AuditLogs.add_audit_log(
                db = db,
                entity_name="Assistant",
                entity_id = assistant.user_id,
                log_type = "Update",
                prev_data = {"is_active": assistant.is_active},
                new_data = {"is_active": False},
                added_by = assistant.user_id,
                admin_id = assistant.admin_id
            )
        logger.info("AssistantService: Assistant account deactivated Successfully.")
        return {
            "message":"Assistant account deactivated successfully."
        }


    @classmethod
    async def get_name_id(cls, db, admin_id):
        stmt = (select(Users.name, Users.user_id).where(Users.admin_id == admin_id, Users.role == "assistant", Users.is_deleted == False))
        result = await db.execute(stmt)
        return result.all()
    
    