from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, DateTime, func, select, or_, and_, false, case, cast
from sqlalchemy.orm import relationship, selectinload, joinedload, aliased
from app.config.database import Base
from datetime import datetime, time, timedelta

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

    
    def to_dict(self, exclude=None):
        if exclude is None:
            exclude = set()
        result = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
                
            value = getattr(self, column.name)
            
            # Convert datetime objects to string format
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
                
        return result

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
        order_by="desc(LeadRemarks.created_at)"
    )
    assignments = relationship("LeadAssignment", back_populates="lead", cascade="all, delete-orphan")
    status_history = relationship(
        "LeadStatusHistory", 
        back_populates="lead", 
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="LeadStatusHistory.created_at"
    )


    def to_dict(self, exclude=None):
        if exclude is None:
            exclude = set()
        result = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
                
            value = getattr(self, column.name)
            
            # Convert datetime objects to string format
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
                
        return result

    @classmethod
    async def get_lead(cls, db, admin_id, email=None, phone=None):
        if email is None and phone is None:
            return None

        stmt = select(LeadResponse).where(
            LeadResponse.admin_id == admin_id,
            LeadResponse.is_deleted == False
        )

        filters = []

        if email:
            filters.append(
                cast(LeadResponse.submitted_data["email"], String) == email
            )

        if phone:
            filters.append(
                cast(LeadResponse.submitted_data["phone"], String) == phone
            )

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

    # @classmethod
    # async def get_all_by_admin_id(cls, db, admin_id, page=1, size=20):
    #     offset = (page - 1) * size
    #     stmt = (
    #         select(LeadResponse)
    #         .where(LeadResponse.admin_id == admin_id, LeadResponse.is_deleted == False)
    #         .order_by(LeadResponse.created_at.desc())
    #         .offset(offset)
    #         .limit(size)
    #     )
    #     result = await db.execute(stmt)
    #     items = result.scalars().all()

    #     count_stmt = select(func.count(LeadResponse.id)).where(LeadResponse.admin_id == admin_id, LeadResponse.is_deleted == False)
    #     total_count = (await db.execute(count_stmt)).scalar()

    #     return {
    #         "items": items,
    #         "total_count": total_count or 0,
    #         "page": page,
    #         "size": size,
    #         "total_pages": (total_count + size - 1) // size if total_count else 0,
    #     }


    @classmethod
    async def get_all_by_admin_id(cls, db, admin_id, page=1, size=20):
        offset = (page - 1) * size

        stmt = (
            select(LeadResponse)
            .where(LeadResponse.admin_id == admin_id, LeadResponse.is_deleted == False)
            .options(
                selectinload(LeadResponse.assignments).selectinload(LeadAssignment.assistant)
            )
            .order_by(LeadResponse.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        
        result = await db.execute(stmt)
        leads = result.scalars().all()

        count_stmt = select(func.count(LeadResponse.id)).where(
            LeadResponse.admin_id == admin_id, 
            LeadResponse.is_deleted == False  
        )
        total_count = (await db.execute(count_stmt)).scalar() or 0

        formatted_items = []
        for lead in leads:
            active_assignments = [a for a in lead.assignments if not a.is_deleted]
            
            assigned_assistant = None
            if active_assignments:
                latest_assignment = sorted(active_assignments, key=lambda x: x.created_at, reverse=True)[0]
                assistant_user = latest_assignment.assistant
                
                if assistant_user:
                    assigned_assistant = {
                        "assignment_id": latest_assignment.id,
                        "assistant_id": assistant_user.user_id,
                        "name": getattr(assistant_user, "name", None),  
                        "email": assistant_user.email,
                        "assigned_at": latest_assignment.created_at.isoformat() if latest_assignment.created_at else None
                    }

            # Build clean response object
            lead_dict = {
                "id": lead.id,
                "template_id": lead.template_id,
                "admin_id": lead.admin_id,
                "collected_from": lead.collected_from,
                "submitted_data": lead.submitted_data,
                "is_deleted": lead.is_deleted,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
                "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
                "assigned_assistant": assigned_assistant  # Returns details OR null if unassigned
            }
            formatted_items.append(lead_dict)

        return {
            "items": formatted_items,
            "total_count": total_count,
            "page": page,
            "size": size,
            "total_pages": (total_count + size - 1) // size if total_count else 0,
        }
        

    @classmethod
    async def get_time_based_stats(cls, db, admin_id=None, assistant_id=None):

        now = datetime.utcnow()

        ranges = {
            "today": datetime(now.year, now.month, now.day),
            "week": now - timedelta(days=7),
            "month": now - timedelta(days=30),
        }

        # Latest Status Subquery
        # -------------------------------
        latest_status_subq = (
            select(
                LeadStatusHistory.lead_id,
                LeadStatusHistory.status,
                func.row_number()
                .over(
                    partition_by=LeadStatusHistory.lead_id,
                    order_by=LeadStatusHistory.created_at.desc(),
                )
                .label("rn"),
            )
            .where(LeadStatusHistory.is_deleted == False)
            .subquery()
        )

        latest_status = aliased(latest_status_subq)

        final_result = {}

        # Loop over time ranges
        # -------------------------------
        for key, start_date in ranges.items():

            query = select(
                func.count(cls.id).label("total_leads"),

                func.count(case((latest_status.c.status == "Converted", 1))).label("converted"),

                func.count(case((latest_status.c.status == "Pending", 1))).label("pending"),

                func.count(case((latest_status.c.status == "InDiscussion", 1))).label("discussion"),

                func.count(case((latest_status.c.status == "Rejected", 1))).label("rejected"),
            )

            query = query.join(
                latest_status,
                (cls.id == latest_status.c.lead_id) & (latest_status.c.rn == 1),
                isouter=True,
            )

            # Time filter
            query = query.where(cls.created_at >= start_date)

            # Admin filter
            if admin_id:
                query = query.where(cls.admin_id == admin_id)

            # Assistant filter
            if assistant_id:
                query = query.join(LeadAssignment).where(
                    LeadAssignment.assistant_id == assistant_id
                )

            result = await db.execute(query)
            stats = result.mappings().first()

            final_result[key] = {
                "total_leads": stats["total_leads"] or 0,
                "converted": stats["converted"] or 0,
                "pending": stats["pending"] or 0,
                "discussion": stats["discussion"] or 0,
                "rejected": stats["rejected"] or 0,
                "conversion_rate" : stats["converted"] / stats["total_leads"] * 100
            }

        return final_result


class LeadRemarks(Base):
    __tablename__ = "lead_remarks" 
    
    id = Column(String, primary_key=True)
    for_lead = Column(String, ForeignKey("lead_responses.id", ondelete="CASCADE"))
    remarks = Column(String, nullable=True)
    # --- FOLLOW-UP FIELDS ---
    # If this is null, it's just a note. If populated, it's a scheduled task.
    next_follow_up_date = Column(DateTime, nullable=True) 
    is_completed = Column(Boolean, default=False)

    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    lead = relationship("LeadResponse", back_populates="remarks")

    
    def to_dict(self, exclude=None):
        if exclude is None:
            exclude = set()
        result = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
                
            value = getattr(self, column.name)
            
            # Convert datetime objects to string format
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
                
        return result

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
    async def get_today_follow_ups(
        cls,
        db,
        start_date,
        end_date,
        admin_id: str = None,
        assistant_id: str = None,
        page: int = 1,
        size: int = 20,
    ):
        try:
            start_parsed_date = datetime.strptime(start_date, "%d%m%Y").date()
            end_parsed_date = datetime.strptime(end_date, "%d%m%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Expected 'ddmmyyyy' string (e.g., 20052026).")

        from_date = datetime.combine(start_parsed_date, time.min)
        end_date_time = datetime.combine(end_parsed_date, time.max)

        offset = (page - 1) * size

        query = (
            select(LeadRemarks)
            .join(LeadResponse, LeadRemarks.for_lead == LeadResponse.id)
            .options(joinedload(LeadRemarks.lead))
        )

        filters = [
            LeadRemarks.next_follow_up_date >= from_date,
            LeadRemarks.next_follow_up_date <= end_date_time,
            LeadRemarks.is_completed == False,
            LeadRemarks.is_deleted == False,
        ]

        if assistant_id:
            query = query.join(LeadAssignment, LeadResponse.id == LeadAssignment.lead_id)
            filters.append(LeadAssignment.assistant_id == assistant_id)
            filters.append(LeadAssignment.is_deleted == False)

        if admin_id:
            filters.append(LeadResponse.admin_id == admin_id)

        count_stmt = (
            select(func.count(LeadRemarks.id))
            .select_from(LeadRemarks)
            .join(LeadResponse, LeadRemarks.for_lead == LeadResponse.id)
            .where(and_(*filters))
        )
        total_count = (await db.execute(count_stmt)).scalar() or 0

        query = query.where(and_(*filters)).order_by(LeadRemarks.next_follow_up_date.asc()).offset(offset).limit(size)

        result = await db.execute(query)
        items = result.scalars().unique().all()

        return {
            "items": items,
            "total_count": total_count,
        }
    

class LeadStatusHistory(Base):
    __tablename__ = "lead_status_history"

    id = Column(String, primary_key=True)
    lead_id = Column(String, ForeignKey("lead_responses.id", ondelete="CASCADE"), nullable=False)
    # The status at this point (e.g., "Created", "Assigned", "Contacted", "Interested", "Converted")
    status = Column(String, nullable=False)
    changed_by = Column(String, ForeignKey("users.user_id"), nullable=True)
    
    is_deleted = Column(Boolean, default = False)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("LeadResponse", back_populates="status_history")
    user = relationship("Users")


    @classmethod
    async def get_all_lead_history(cls, db, lead_id):
        stmt = select(LeadStatusHistory).where(LeadStatusHistory.lead_id == lead_id, LeadStatusHistory.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    
    def to_dict(self, exclude=None):
        if exclude is None:
            exclude = set()
        result = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
                
            value = getattr(self, column.name)
            
            # Convert datetime objects to string format
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
                
        return result





class LeadAssignment(Base):
    __tablename__ = "lead_assignments"

    id = Column(String, primary_key=True)
    lead_id = Column(String, ForeignKey("lead_responses.id", ondelete="CASCADE"), nullable=False)
    assistant_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    is_deleted = Column(Boolean, default = False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = relationship("LeadResponse", back_populates="assignments")
    assistant = relationship("Users") 

    
    def to_dict(self, exclude=None):
        result = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue  
            value = getattr(self, column.name)
            # Convert datetime objects to string format
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value     
        return result

    @classmethod
    async def get_assistant_by_lead_id(cls, db, lead_id):
        stmt = select(LeadAssignment).where(LeadAssignment.lead_id == lead_id, LeadAssignment.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_lead_id(cls, db, lead_id):
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



    # @classmethod
    # async def get_all_paginated_leads_by_assistant_id(cls, db, assistant_id, page, size):
    #     offset = (page - 1) * size
    #     # Base query joining Assignment to LeadResponse
    #     # We use selectinload to pull remarks efficiently
    #     stmt = (
    #         select(LeadResponse)
    #         .join(LeadAssignment, LeadAssignment.lead_id == LeadResponse.id)
    #         .where(
    #             LeadAssignment.assistant_id == assistant_id,
    #             LeadAssignment.is_deleted == False,
    #             LeadResponse.is_deleted == False
    #         )
    #         .options(selectinload(LeadResponse.remarks)) 
    #         .order_by(LeadResponse.created_at.desc())
    #         .offset(offset)
    #         .limit(size)
    #     )

    #     result = await db.execute(stmt)
    #     leads = result.scalars().all()

    #     # Count total for pagination metadata
    #     count_stmt = (
    #         select(func.count(LeadResponse.id))
    #         .join(LeadAssignment, LeadAssignment.lead_id == LeadResponse.id)
    #         .where(
    #             LeadAssignment.assistant_id == assistant_id,
    #             LeadAssignment.is_deleted == False
    #         )
    #     )
    #     count_result = await db.execute(count_stmt)
    #     total_count = count_result.scalar()

    #     return {
    #         "items": leads, # Contains LeadResponse objects + their remarks
    #         "total_count": total_count,
    #         "page": page,
    #         "size": size,
    #         "total_pages": (total_count + size - 1) // size if total_count else 0,
    #     }



    @classmethod
    async def get_all_paginated_leads_by_assistant_id(cls, db, assistant_id, page, size):
        offset = (page - 1) * size

        stmt = (
            select(LeadResponse)
            .join(LeadAssignment, LeadAssignment.lead_id == LeadResponse.id)
            .where(
                LeadAssignment.assistant_id == assistant_id,
                LeadAssignment.is_deleted == False,
                LeadResponse.is_deleted == False
            )
            .options(selectinload(LeadResponse.status_history)) 
            .order_by(LeadResponse.created_at.desc())
            .offset(offset)
            .limit(size)
        )

        result = await db.execute(stmt)
        leads = result.scalars().all()

        count_stmt = (
            select(func.count(LeadResponse.id))
            .join(LeadAssignment, LeadAssignment.lead_id == LeadResponse.id)
            .where(
                LeadAssignment.assistant_id == assistant_id,
                LeadAssignment.is_deleted == False,
                LeadResponse.is_deleted == False
            )
        )
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar() or 0

        formatted_leads = []
        for lead in leads:
            active_history = [h for h in lead.status_history if not h.is_deleted]
            
            current_status = "Created" 
            if active_history:
                latest_entry = max(active_history, key=lambda x: x.created_at)
                current_status = latest_entry.status

            lead_data = {
                "id": lead.id,
                "template_id": lead.template_id,
                "admin_id": lead.admin_id,
                "collected_from": lead.collected_from,
                "submitted_data": lead.submitted_data,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
                "status": current_status,
                "assigned_assistant": "You" 
            }
            formatted_leads.append(lead_data)

        return {
            "items": formatted_leads, 
            "total_count": total_count,
            "page": page,
            "size": size,
            "total_pages": (total_count + size - 1) // size if total_count else 0,
        }


        
        