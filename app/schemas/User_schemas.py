from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class AddressBase(BaseModel):
    address_line_1: str
    address_line_2: str | None = None
    city: str
    province: str
    country: str
    postal_code: str

    class Config:
        from_attributes = True


class UserCreate(AddressBase):
    name: str
    role: str
    email: str
    profile_image: str | None = None

    class Config:
        from_attributes = True

class UserUpdate(AddressBase):
    name: str | None = None
    role: str | None = None
    email: str | None = None
    profile_image: str | None = None

# class UserResponse(UserCreate):
#     user_id: str
#     is_active: bool
#     is_deleted: bool
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         from_attributes = True

class UserResponse(BaseModel):
    user_id: str
    name: str
    role: str
    email: str
    profile_image: str | None = None
    is_active: bool
    is_deleted: bool
    created_at: datetime
    admin_id: Optional[str] = None
    # FIXED: updated_at can be None on creation, so make it Optional
    updated_at: datetime | None = None 
    
    # FIXED: Nest the address schema to match the SQLAlchemy relationship
    address: AddressBase | None = None

    class Config:
        from_attributes = True

class UserPaginationResponse(BaseModel):
    items: List[UserResponse]
    total_count: int
    page: int
    size: int
    total_pages: int

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    new_password: str

class ForgetPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

class AssistantNameIdResponse(BaseModel):
    name: str
    user_id: str

    class Config:
        from_attributes = True


class ComposeEmailRequest(BaseModel):
    email_to: EmailStr
    subject: str
    body: str

class EmailRecipient(BaseModel):
    email: EmailStr
    
class ComposeBulkEmailRequest(BaseModel):
    email_to: list[EmailRecipient]
    subject: str
    body: str


class ComposeBulkEmailToUsers(BaseModel):
    subject: str
    body: str