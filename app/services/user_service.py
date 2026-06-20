from fastapi import Request, Response, HTTPException
from app.models.user_model import Users, OtpModel
from app.core.hash import hash_password, verify_password
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.core.auth import create_auth_token, create_refresh_token, verify_refresh_token
from app.core.utils_functions import generate_id, generate_otp
from app.backgroundTasks.MonitorAsync import MonitorAsync
from app.templates.send_template_mail import MailTemplatesService
from datetime import timedelta
from dotenv import load_dotenv
import os
import logging
logger = logging.getLogger(__name__)

load_dotenv()
DOMAIN = os.getenv("DOMAIN", "localhost")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))
REFRESH_TOKEN_EXPIRE_HOURS = int(os.getenv("REFRESH_TOKEN_EXPIRE_HOURS", "168"))


def _cookie_settings():
    cookie_domain = None if DOMAIN in ("localhost", "127.0.0.1", "") else DOMAIN
    secure = False if DOMAIN in ("localhost", "127.0.0.1", "") else True
    return cookie_domain, secure

class UserServices:
    @classmethod
    async def UserLogin(cls, db: Session, email: str, password: str, response: Response):
        user = await Users.get_by_email(db, email)

        if not user:
            logger.error("UserService: User with this email not found or user deactivated or deleted")
            raise HTTPException(404, "UserService: User with this email not found or user deactivated or deleted")
        
        if not verify_password(password, user.password):
            logger.error("UserService: User password verification failed due to password mismatch please enter correct password")
            raise HTTPException(401, "UserService: User password verification failed due to password mismatch please enter correct password")

        access_token = create_auth_token(
            data={"sub": user.email, "user_id": user.user_id, "role": user.role},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token(
            data={"sub": user.email, "user_id": user.user_id, "role": user.role},
            expires_delta=timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS),
        )

        token_expiry = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expiry = timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)
        expiry_seconds = int(token_expiry.total_seconds())
        refresh_expiry_seconds = int(refresh_expiry.total_seconds())
        cookie_domain, secure = _cookie_settings()

        response.set_cookie(
            key="auth",
            value=access_token,
            httponly=True,
            samesite="Lax",
            secure=secure,
            max_age=expiry_seconds,
            expires=expiry_seconds,
            domain=cookie_domain,
            path='/',
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="Lax",
            secure=secure,
            max_age=refresh_expiry_seconds,
            expires=refresh_expiry_seconds,
            domain=cookie_domain,
            path='/',
        )
        return {
            "user_id": str(user.user_id),
            "email": user.email,
            "role": user.role,
            "access_token": access_token,
            "token_type": "bearer",
        }

    @classmethod
    async def refresh_access_token(cls, db: Session, request: Request, response: Response):
        refresh_token_value = request.cookies.get("refresh_token")
        if not refresh_token_value:
            logger.warning("UserService: Refresh token missing")
            raise HTTPException(status_code=401, detail="Refresh token missing")

        payload = verify_refresh_token(refresh_token_value)
        user = await Users.get_by_email(db, payload.get("sub"))
        if not user:
            logger.error("UserService: Invalid refresh token user")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        access_token = create_auth_token(
            data={"sub": user.email, "user_id": user.user_id, "role": user.role},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token(
            data={"sub": user.email, "user_id": user.user_id, "role": user.role},
            expires_delta=timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS),
        )

        token_expiry = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expiry = timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)
        expiry_seconds = int(token_expiry.total_seconds())
        refresh_expiry_seconds = int(refresh_expiry.total_seconds())
        cookie_domain, secure = _cookie_settings()

        response.set_cookie(
            key="auth",
            value=access_token,
            httponly=True,
            samesite="Lax",
            secure=secure,
            max_age=expiry_seconds,
            expires=expiry_seconds,
            domain=cookie_domain,
            path='/',
        )
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="Lax",
            secure=secure,
            max_age=refresh_expiry_seconds,
            expires=refresh_expiry_seconds,
            domain=cookie_domain,
            path='/',
        )

        logger.info("UserServices: Access token refreshed successfully")
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
    
    @classmethod
    async def update_user_password(cls, db: Session, user_id: str, new_password: str):
        user = await Users.get_by_id(db, user_id)
        if not user:
            return None
        hashed_pw = hash_password(new_password)
        user.password = hashed_pw
        await db.commit()
        await db.refresh(user)
        MonitorAsync.deferred(MailTemplatesService.send_notif_password_change, user.email)
        logger.info("UserServices: Password updated successfully :)")
        return user

    @classmethod
    async def forgot_password(cls, db: Session, email: str):
        user = await Users.get_by_email(db, email)
        if not user:
            return None
        new_otp = generate_otp()
        existing = await OtpModel.by_email(db, email)
        if existing and existing.is_used == True:
            existing.otp_code = new_otp
            existing.is_used = False
        elif existing and existing.is_used == False:
            existing.otp_code = new_otp
        else:
            new_record = OtpModel(email=email,otp_code=new_otp)
            db.add(new_record)
        await db.commit()  
        MonitorAsync.deferred(MailTemplatesService.send_otp_template, email, new_otp)
        return {"message": "OTP sent successfully"}

    @classmethod
    async def reset_password(cls, db: Session, email: str, otp_code: str, new_password: str):
        user = await Users.get_by_email(db, email)
        if not user:
            return None
        existing = await OtpModel.get_by_email(db, email)
        if not existing:
            logger.error("UserService: OTP not found with this email or already used")
            raise HTTPException(status_code=400, detail="UserService: OTP not found or already used")
        if existing.otp_code != otp_code:
            logger.error("UserService: Invalid OTP provided by the user")
            raise HTTPException(status_code=400, detail="UserService: Invalid OTP")
        existing.is_used = True
        hashed_pw = hash_password(new_password)
        user.password = hashed_pw
        await db.commit()       
        await db.refresh(user)
        MonitorAsync.deferred(MailTemplatesService.send_notif_password_change, email)
        logger.info("AdminAuthService: Password changed successfully")
        return {"message": "Password changed successfully"}


    def logout(request: Request, response: Response):   
        try:
            response.delete_cookie(
                key="auth",
                httponly=True,
                samesite="Lax",
                secure=False,
                domain=DOMAIN,
                path='/',
            )
            response.delete_cookie(
                key="refresh_token",
                httponly=True,
                samesite="Lax",
                secure=False,
                domain=DOMAIN,
                path='/',
            )
            logger.info("UserService: Logged out successfully")
            return {"message": "UserService: Logged out successfully"}
        except Exception as e:
            logger.error("UserService: Error during logout: %s", e)
            raise HTTPException(status_code=500, detail="UserService: Internal server error")
        





