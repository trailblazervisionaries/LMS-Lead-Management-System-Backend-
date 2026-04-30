from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, DateTime, func, select, desc
from sqlalchemy.orm import relationship
from app.config.database import Base
from datetime import datetime

class FormTemplate(Base):
    __tablename__ = "form_templates"
    id = Column(String, primary_key=True)
    admin_id = Column(String, ForeignKey("users.user_id"))
    title = Column(String)
    logo_link = Column(String, nullable = True)
    form_color = Column(String, nullable = False)
    page_color = Column(String, nullable = False)
    border_color = Column(String, nullable = False)
    # Stores the structure: [{"label": "Age", "type": "number", "required": True}, ...]
    schema_definition = Column(JSON) 
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    admin = relationship("Users", back_populates="form")


    @classmethod
    async def get_form_by_id(cls, db, id, admin_id):
        stmt = select(FormTemplate).where(FormTemplate.id == id, FormTemplate.admin_id == admin_id)
        result = await db.execute(stmt)
        return result.scalars_one_or_none()







class LeadResponse(Base):
    __tablename__ = "lead_responses"
    id = Column(String, primary_key=True)
    template_id = Column(String, ForeignKey("form_templates.id"))
    admin_id = Column(String, ForeignKey("users.user_id"))
    # Stores the answers: {"Age": 25, "Name": "John"}
    submitted_data = Column(JSON)
    is_deleted = Column(Boolean, default = False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    remarks = relationship(
        "LeadRemarks", 
        back_populates="lead", 
        cascade="all, delete-orphan", 
        order_by="desc(LeadRemarks.created_at)" # FIXED: String or name reference preferred here
    )

    @classmethod
    async def get_form_by_id(cls, db, id, admin_id):
        stmt = select(LeadResponse).where(LeadResponse.id == id, LeadResponse.admin_id == admin_id)
        result = await db.execute(stmt)
        return result.scalars_one_or_none()





class LeadRemarks(Base):
    __tablename__ = "lead_reamrks"

    id  = Column(String, primary_key=True)
    for_lead = Column(String, ForeignKey("lead_responses.id"))
    remarks = Column(String, nullable = True)
    is_deleted = Column(Boolean, default = False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("LeadResponse", back_populates="remarks")

    @classmethod
    async def get_remarks(cls, db, id):
        stmt = select(LeadResponse).where(LeadResponse.id == id, LeadResponse.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalars_one_or_none()
    

    @classmethod
    async def get_all_remarks(cls, db, id, for_lead):
        stmt = select(LeadResponse).where(LeadResponse.id == id, LeadResponse.for_lead == for_lead, LeadResponse.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalars().all()




class LeadAssignment(Base):
    id = Column(String, primary_key = True)
    lead_id = Column(String, ForeignKey("lead_responses.id"))
    assign_to = Column(String, ForeignKey("users.user_id"))
    is_deleted = Column(Boolean, default = False)
    created_at = Column(DateTime, default = datetime.utcnow)
    updated_at = Column(DateTime, default = datetime.utcnow)


    assistant = relationship("Users", back_populates="assignment")
