from fastapi import Request, Response, HTTPException, status
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy.exc import IntegrityError
from app.core.utils_functions import generate_id, generate_alphanumeric_password
from sqlalchemy import select
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


class AdminService:
    
    async def create_admin(cls, db, data: UserCreate):
        admin = Users.get_by_email(cls, db, data.email)
        if admin:
            raise HTTPException(500, "Email Already in database please try with another one or contact the team")
        try:
            temp_password = generate_alphanumeric_password()
            hashed_password = hash_password(temp_password)
            new_admin = Users(
                user_id = generate_id(data.name),
                name = data.name,
                role = data.role,
                email = data.email,
                password= hashed_password,
            )

            new_admin.address = Address(
                user_id=new_admin.user_id,  
                address_line_1=data.address_line_1,
                address_line_2=data.address_line_2,
                city=data.city,
                province=data.province,
                country=data.country,
                postal_code=data.postal_code,
            )

            db.add(new_admin)
            await db.commit()
            logger.info("AdminService: New user admin is added successfully")
            await db.refresh(new_admin, ["address"])
            # MonitorAsync.deferred(
            #     MailTemplatesService.send_credentials_template,
            #     new_admin.email,
            #     new_admin.fname,
            #     "admin",
            #     temp_password,
            # )
            return new_admin
        
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
    async def update_admin(cls, db, user_id: str, data: UserUpdate, request: Request):
        admin = await Users.get_by_id(cls, db, user_id)

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AdminService: Admin not found"
            )

        try:
            if hasattr(data, "email") and data.email is not None:
                admin.email = data.email

            if hasattr(data, "role") and data.role is not None:
                admin.role = data.role
            
            if hasattr(data, "name") and data.name is not None:
                admin.name = data.name

            admin_data = data.model_dump(
                exclude_unset=True,
                exclude={"address", "email", "role", "name"}
            )

            for field, value in admin_data.items():
                setattr(admin, field, value)

            if data.address:
                address_data = data.address.model_dump(exclude_unset=True)

                if admin.address:
                    for field, value in address_data.items():
                        setattr(admin.address, field, value)
                else:
                    admin.address = Address(
                        user_id=admin.user_id,
                        **address_data
                    )

            await db.commit()
            await db.refresh(admin, ["address"])
            logger.info("AdminService: Admin data updated successfully")
            return admin

        except Exception:
            await db.rollback()
            logger.error("AdminService: Error updating admin detials")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating admin details"
            )
        

    @classmethod
    async def get_my_info(cls, db, user_id):
        return await Users.get_my_info(cls, db, user_id)
