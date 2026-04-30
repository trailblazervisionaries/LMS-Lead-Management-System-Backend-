from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class AddressBase(BaseModel):
    address_line_1: str
    address_line_2: str
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

class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    email: str | None = None
    profile_image: str | None = None

class UserResponse(UserCreate):
    user_id: str
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserPaginationResponse(UserResponse):
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



