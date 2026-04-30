from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, DateTime, func, select, desc
from sqlalchemy.orm import relationship, selectinload
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
        return result.scalar_one_or_none()







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
    assignments = relationship("LeadAssignment", back_populates="lead")
    status_history = relationship(
        "LeadStatusHistory", 
        back_populates="lead", 
        order_by="LeadStatusHistory.created_at"
    )

    @classmethod
    async def get_lead_by_id(cls, db, id, admin_id):
        stmt = select(LeadResponse).where(LeadResponse.id == id, LeadResponse.admin_id == admin_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()





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
        return result.scalar_one_or_none()
    

    @classmethod
    async def get_all_remarks(cls, db, id, for_lead):
        stmt = select(LeadResponse).where(LeadResponse.id == id, LeadResponse.for_lead == for_lead, LeadResponse.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalars().all()


class LeadStatusHistory(Base):
    __tablename__ = "lead_status_history"

    id = Column(String, primary_key=True)
    lead_id = Column(String, ForeignKey("lead_responses.id"), nullable=False)
    # The status at this point (e.g., "Created", "Assigned", "Contacted", "Interested", "Converted")
    status = Column(String, nullable=False)
    # Optional: Track who made the change (the Admin or Assistant)
    changed_by = Column(String, ForeignKey("users.user_id"), nullable=True)
    
    is_deleted = Column(Boolean, default = False)
    # This creates your "1 April 2026", "2 April 2026" timeline
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("LeadResponse", back_populates="status_history")
    user = relationship("Users")


    @classmethod
    async def get_all_lead_history(cls, db, lead_id):
        stmt = select(LeadStatusHistory).where(LeadStatusHistory.lead_id == lead_id, LeadStatusHistory.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalars().all()
    




class LeadAssignment(Base):
    __tablename__ = "lead_assignments"

    id = Column(String, primary_key=True)
    lead_id = Column(String, ForeignKey("lead_responses.id"), nullable=False)
    assistant_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    is_deleted = Column(Boolean, default = False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = relationship("LeadResponse", back_populates="assignments")
    assistant = relationship("Users") 


    @classmethod
    async def get_assistant_by_lead_id(cls, db, lead_id):
        stmt = select(LeadAssignment).where(LeadAssignment.lead_id == lead_id, LeadAssignment.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalar_one_one_none()
        


    @classmethod
    async def get_all_paginated_leads_by_assistant_id(cls, db, assistant_id, page, size):
        offset = (page - 1) * size
        # Base query joining Assignment to LeadResponse
        # We use selectinload to pull remarks efficiently
        stmt = (
            select(LeadResponse)
            .join(LeadAssignment, LeadAssignment.lead_id == LeadResponse.id)
            .where(
                LeadAssignment.assistant_id == assistant_id,
                LeadAssignment.is_deleted == False,
                LeadResponse.is_deleted == False
            )
            .options(selectinload(LeadResponse.remarks)) 
            .order_by(LeadResponse.created_at.desc())
            .offset(offset)
            .limit(size)
        )

        result = await db.execute(stmt)
        leads = result.scalars().all()

        # Count total for pagination metadata
        count_stmt = (
            select(func.count(LeadResponse.id))
            .join(LeadAssignment, LeadAssignment.lead_id == LeadResponse.id)
            .where(
                LeadAssignment.assistant_id == assistant_id,
                LeadAssignment.is_deleted == False
            )
        )
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()

        return {
            "items": leads, # Contains LeadResponse objects + their remarks
            "total": total_count,
            "page": page,
            "size": size
        }




