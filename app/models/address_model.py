from sqlalchemy.orm import relationship
from app.config.database import Base
from sqlalchemy import Column, Integer, Boolean, String, DateTime, ForeignKey
from datetime import datetime


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    address_line_1 = Column(String, nullable=False)
    address_line_2 = Column(String)
    city = Column(String, nullable=False)
    province = Column(String, nullable=False)   # e.g., ON, BC, QC
    country = Column(String, nullable=False, default="India")
    postal_code = Column(String, nullable=False)  # A1A 1A1
    is_deleted = Column(Boolean, default = False)
    created_at = Column(DateTime, default = datetime.utcnow)
    updated_at = Column(DateTime, default = datetime.utcnow)


    user = relationship("Users", back_populates="address")

    


    def to_dict(self):
        # Automatically converts columns into a standard python dictionary
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


    