from sqlalchemy.orm import relationship
from app.config.database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, select
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime

class Users(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key = True, index = True)
    name = Column(String, nullable = False)
    role = Column(String, nullable = False)
    email = Column(String, nullable = False, unique = True, index = True)
    password = Column(String, nullable = False)
    profile_image = Column(String, nullable = True)
    admin_id = Column(String, nullable = True)
    is_deleted = Column(Boolean, default = False)
    is_active = Column(Boolean, default = True)
    created_at = Column(DateTime, default = datetime.utcnow)
    updated_at = Column(DateTime, nullable = True, onupdate = datetime.utcnow)

    address = relationship(
        "Address", 
        back_populates="user", 
        uselist=False, 
        cascade="all, delete-orphan"
    )

    form = relationship("FormTemplate", back_populates="admin")
    assignment  = relationship("LeadAssignment", back_populates="assistant")


    @classmethod
    async def get_by_email(cls, db, email):
        stmt = select(Users).where(Users.email == email, Users.is_deleted == False, Users.is_active == True)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_id(cls, db, user_id):
        stmt = select(Users).where(Users.user_id == user_id, Users.is_deleted == False, Users.is_active == True)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def by_id(cls, db, user_id):
        stmt = select(Users).where(Users.user_id == user_id, Users.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_id_with_address(cls, db, user_id):
        stmt = (
            select(Users)
            .options(joinedload(Users.address)) 
            .where(
                Users.user_id == user_id, 
                Users.is_deleted == False, 
                Users.is_active == True
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    
    @classmethod
    async def by_email(cls, db, email):
        stmt = (select(Users).where(Users.email == email))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_my_info(cls, db, user_id):
        stmt = (
            select(Users)
            .options(selectinload(Users.address)) 
            .where(
                Users.user_id == user_id, 
                Users.is_deleted == False, 
                Users.is_active == True
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()




class OtpModel(Base):
    __tablename__ = "otp_table"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


    @classmethod
    async def get_by_email(cls, db, email):
        stmt = select(OtpModel).where(
        OtpModel.email == email,
        OtpModel.is_used.is_(False),
        )
        result = await db.execute(stmt)
        otp_data = result.scalar_one_or_none()
        return otp_data
    
    @classmethod
    async def by_email(cls, db, email):
        stmt = select(OtpModel).where(
        OtpModel.email == email,
        )
        result = await db.execute(stmt)
        otp_data = result.scalar_one_or_none()
        return otp_data





