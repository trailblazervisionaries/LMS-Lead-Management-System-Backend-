from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, DateTime, func, select, or_, and_, false
from sqlalchemy.orm import relationship, selectinload, joinedload
from app.config.database import Base
from datetime import datetime, time

class FormTemplate(Base):
    __tablename__ = "form_templates"
    id = Column(String, primary_key=True)
    admin_id = Column(String, ForeignKey("users.user_id"))
    # Stores the structure: [{"label": "Age", "type": "number", "required": True}, ...]
    is_active = Column(Boolean, default = True)
    schema_definition = Column(JSON) 
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    admin = relationship("Users", back_populates="form")

    @classmethod
    async def get_form_by_id(cls, db, form_id):
        stmt = select(FormTemplate).where(FormTemplate.id == form_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_active_forms_by_admin_id(cls, db, admin_id):
        stmt = select(FormTemplate).where(FormTemplate.admin_id == admin_id, FormTemplate.is_active == True)
        result = await db.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_all_forms_by_admin_id(cls, db, admin_id):
        stmt = select(FormTemplate).where(FormTemplate.admin_id == admin_id)
        result = await db.execute(stmt)
        return result.scalars().all()




class LeadResponse(Base):
    __tablename__ = "lead_responses"
    id = Column(String, primary_key=True)
    template_id = Column(String, ForeignKey("form_templates.id"))
    admin_id = Column(String, ForeignKey("users.user_id"))
    collected_from = Column(String, nullable = False, default = "website")
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
    async def get_lead(cls, db, admin_id, email=None, phone=None):
        if email is None and phone is None:
            return None

        stmt = select(LeadResponse).where(LeadResponse.admin_id == admin_id, LeadResponse.is_deleted == False)
        filters = []
        if email:
            filters.append(LeadResponse.submitted_data["email"].astext == email)
        if phone:
            filters.append(LeadResponse.submitted_data["phone"].astext == phone)

        stmt = stmt.where(or_(*filters))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_lead_by_id(cls, db, lead_id):
        stmt = select(LeadResponse).where(LeadResponse.id == lead_id, LeadResponse.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_id(cls, db, lead_id):
        stmt = select(LeadResponse).where(LeadResponse.lead_id == lead_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_all_by_admin_id(cls, db, admin_id, page=1, size=20):
        offset = (page - 1) * size
        stmt = (
            select(LeadResponse)
            .where(LeadResponse.admin_id == admin_id, LeadResponse.is_deleted == False)
            .order_by(LeadResponse.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        count_stmt = select(func.count(LeadResponse.id)).where(LeadResponse.admin_id == admin_id, LeadResponse.is_deleted == False)
        total_count = (await db.execute(count_stmt)).scalar()

        return {
            "items": items,
            "total": total_count or 0,
            "page": page,
            "size": size,
            "total_pages": (total_count + size - 1) // size if total_count else 0,
        }


class LeadRemarks(Base):
    __tablename__ = "lead_remarks" # Fixed typo from "reamrks"
    
    id = Column(String, primary_key=True)
    for_lead = Column(String, ForeignKey("lead_responses.id"))
    remarks = Column(String, nullable=True)
    # --- FOLLOW-UP FIELDS ---
    # If this is null, it's just a note. If populated, it's a scheduled task.
    next_follow_up_date = Column(DateTime, nullable=True) 
    is_completed = Column(Boolean, default=False)

    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    lead = relationship("LeadResponse", back_populates="remarks")


    @classmethod
    async def get_remarks(cls, db, lead_id):
        stmt = select(LeadRemarks).where(LeadRemarks.for_lead == lead_id, LeadRemarks.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalars().all()
    

    @classmethod
    async def get_all_remarks(cls, db, lead_id):
        stmt = select(LeadRemarks).where(LeadRemarks.for_lead == lead_id, LeadRemarks.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    
    @classmethod
    async def get_today_follow_ups(db, admin_id: str = None, assistant_id: str = None):
        today_start = datetime.combine(datetime.utcnow().date(), time.min)
        today_end = datetime.combine(datetime.utcnow().date(), time.max)

        # Start query from LeadRemarks
        query = (
            select(LeadRemarks)
            .join(LeadResponse, LeadRemarks.for_lead == LeadResponse.id)
            .options(joinedload(LeadRemarks.lead))
        )

        # Basic filters: Today's date, not completed, not deleted
        filters = [
            LeadRemarks.next_follow_up_date >= today_start,
            LeadRemarks.next_follow_up_date <= today_end,
            LeadRemarks.is_completed == False,
            LeadRemarks.is_deleted == False
        ]

        if admin_id:
            filters.append(LeadResponse.admin_id == admin_id)

        if assistant_id:
            query = query.join(LeadAssignment, LeadResponse.id == LeadAssignment.lead_id)
            filters.append(LeadAssignment.assistant_id == assistant_id)
            filters.append(LeadAssignment.is_deleted == False)

        query = query.where(and_(*filters)).order_by(LeadRemarks.next_follow_up_date.asc())

        result = await db.execute(query)
        return result.scalars().unique().all()
    

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
        return result.scalar_one_or_none()


    @classmethod
    async def get_unassigned_leads_by_admin(cls, db, admin_id: str):
        stmt = (
            select(LeadResponse)
            .outerjoin(LeadAssignment, LeadResponse.id == LeadAssignment.lead_id)
            .where(
                LeadResponse.admin_id == admin_id,
                LeadResponse.is_deleted == False,
                or_(
                    LeadAssignment.id == None,
                    LeadAssignment.is_deleted == True
                )
            )
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()



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








