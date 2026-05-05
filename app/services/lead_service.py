from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.core.utils_functions import generate_id
from sqlalchemy import select, insert, func
from datetime import datetime
from dotenv import load_dotenv
from app.models.lead_form import (
    FormTemplate,
    LeadResponse,
    LeadRemarks,
    LeadStatusHistory,
    LeadAssignment,
)
import pandas as pd
import io
from app.models.user_model import Users
# from app.templates.send_template_mail import MailTemplatesService
# from app.backgroundTasks.MonitorAsync import MonitorAsync
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class LeadService:

    @classmethod
    async def add_new_lead(cls, db: Session, data):
        template = await FormTemplate.get_form_by_id(db, data.template_id)
        if not template or not template.is_active:
            raise HTTPException(status_code=404, detail="Lead form template not found or inactive")

        admin_id = template.admin_id
        lead_duplicate = await LeadResponse.get_lead(
            db,
            admin_id,
            email=data.submitted_data.get("email"),
            phone=data.submitted_data.get("phone"),
        )
        if lead_duplicate:
            raise HTTPException(status_code=400, detail="Lead already exists")

        new_lead = LeadResponse(
            id=generate_id(template.id),
            template_id=data.template_id,
            collected_from = data.collected_from,
            admin_id=admin_id,
            submitted_data=data.submitted_data,
        )

        created_status = LeadStatusHistory(
            id=generate_id(admin_id),
            lead_id=new_lead.id,
            status="Created",
        )

        db.add(new_lead)
        db.add(created_status)
        await db.commit()
        await db.refresh(new_lead)

        await cls.auto_assign_lead(db, admin_id, new_lead.id)
        return new_lead

    @classmethod
    async def auto_assign_lead(cls, db: Session, admin_id: str, lead_id: str):
        assistant_stmt = select(Users).where(
            Users.admin_id == admin_id,
            Users.role == "assistant",
            Users.is_active == True,
            Users.is_deleted == False,
        )
        result = await db.execute(assistant_stmt)
        assistants = result.scalars().all()
        if not assistants:
            return None

        least_assigned = None
        lowest_count = None
        for assistant in assistants:
            count_stmt = select(func.count(LeadAssignment.id)).where(
                LeadAssignment.assistant_id == assistant.user_id,
                LeadAssignment.is_deleted == False,
            )
            count = (await db.execute(count_stmt)).scalar() or 0
            if lowest_count is None or count < lowest_count:
                lowest_count = count
                least_assigned = assistant

        if not least_assigned:
            return None

        new_assignment = LeadAssignment(
            id=generate_id(lead_id),
            lead_id=lead_id,
            assistant_id=least_assigned.user_id,
        )
        assigned_status = LeadStatusHistory(
            id=generate_id(least_assigned.user_id),
            lead_id=lead_id,
            status="Assigned",
            changed_by=least_assigned.user_id,
        )

        db.add(new_assignment)
        db.add(assigned_status)
        await db.commit()
        return new_assignment

    @classmethod
    async def assign_unassigned_leads(cls, db: Session, admin_id: str):
        unassigned_leads = await LeadAssignment.get_unassigned_leads_by_admin(db, admin_id)
        if not unassigned_leads:
            return {"leads_assigned": 0, "assistants_involved": 0}

        assistant_stmt = select(Users).where(
            Users.admin_id == admin_id,
            Users.role == "assistant",
            Users.is_active == True,
            Users.is_deleted == False,
        )
        result = await db.execute(assistant_stmt)
        assistants = result.scalars().all()
        if not assistants:
            return {"leads_assigned": 0, "assistants_involved": 0}

        counts = {}
        for assistant in assistants:
            counts[assistant.user_id] = 0

        assignments_created = 0
        assistant_cycle = list(assistants)
        index = 0
        for lead in unassigned_leads:
            if not assistant_cycle:
                break
            assistant = assistant_cycle[index % len(assistant_cycle)]
            index += 1
            new_assignment = LeadAssignment(
                id=generate_id(lead.id),
                lead_id=lead.id,
                assistant_id=assistant.user_id,
            )
            db.add(new_assignment)
            status = LeadStatusHistory(
                id=generate_id(assistant.user_id),
                lead_id=lead.id,
                status="Assigned",
                changed_by=assistant.user_id,
            )
            db.add(status)
            counts[assistant.user_id] += 1
            assignments_created += 1

        if assignments_created:
            await db.commit()

        return {
            "leads_assigned": assignments_created,
            "assistants_involved": len(assistants),
        }
    

    @classmethod
    async def assign_assistant_to_lead_one_by_one(db, admin_id, assistant_id, lead_id):
        # assigned = await LeadAssignment.get_assistant_by_lead_id(db, lead_id)
        # if assigned:
        #     raise HTTPException(404, "Lead is already assign to another person")
        
        new_assignment = LeadAssignment(
            id = str(generate_id()),
            lead_id = lead_id,
            assistant_id = assistant_id
        )
        db.add(new_assignment)

        status = LeadStatusHistory(
            id=str(generate_id()),
            lead_id=lead_id,
            status="Assigned",
            changed_by=admin_id,
        )
        db.add(status)
        await db.commit()
        await db.refresh()
        return new_assignment
    

    @classmethod
    async def get_leads_for_admin(cls, db: Session, admin_id: str, page: int = 1, size: int = 20):
        return await LeadResponse.get_all_by_admin_id(db, admin_id, page, size)

    @classmethod
    async def get_leads_for_assistant(cls, db: Session, assistant_id: str, page: int = 1, size: int = 20):
        return await LeadAssignment.get_all_paginated_leads_by_assistant_id(db, assistant_id, page, size)

    @classmethod
    async def update_lead(cls, db: Session, lead_id: str, user_id: str, role: str, data):
        lead = await LeadResponse.get_lead_by_id(db, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        if role == "assistant":
            assignment = await LeadAssignment.get_assistant_by_lead_id(db, lead_id)
            if not assignment or assignment.assistant_id != user_id:
                raise HTTPException(status_code=403, detail="Lead not assigned to this assistant")

        if data.status:
            status_entry = LeadStatusHistory(
                id=generate_id(user_id),
                lead_id=lead_id,
                status=data.status,
                changed_by=user_id,
            )
            db.add(status_entry)

        if data.remarks or data.next_follow_up_date is not None or data.is_completed is not None:
            remark_entry = LeadRemarks(
                id=generate_id(lead_id),
                for_lead=lead_id,
                remarks=data.remarks,
                next_follow_up_date=data.next_follow_up_date,
                is_completed=data.is_completed if data.is_completed is not None else False,
            )
            db.add(remark_entry)

        await db.commit()
        await db.refresh(lead)
        return lead
    
    @classmethod
    async def delete_lead_permanentaly(cls, db, lead_id):
        lead = await LeadResponse.get_lead_by_id(db, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        await db.delete(lead)
        await db.commit()
        return {"detail": f"Lead with id {lead_id} deleted successfully"}
    
    @classmethod
    async def lead_mark_deleted(cls, db, lead_id):
        lead = await LeadResponse.get_by_id(db, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="lead not found")
        await db.is_deleted == True
        await db.commit()
        return {"detail": f"Lead with id {lead_id} deleted successfully"}


    @classmethod
    async def get_todays_followups(cls, db: Session, assistant_id: str = None, admin_id: str = None):
        return await LeadRemarks.get_today_follow_ups(db, admin_id, assistant_id)

    @classmethod
    async def get_lead_history(cls, db: Session, lead_id: str):
        lead = await LeadResponse.get_lead_by_id(db, lead_id)
        if not lead:
            return None
        history = await LeadStatusHistory.get_all_lead_history(db, lead_id)
        return [
            {
                "id": item.id,
                "lead_id": item.lead_id,
                "status": item.status,
                "changed_by": item.changed_by,
                "created_at": item.created_at,
            }
            for item in history
        ]

    @classmethod
    async def upload_leads(cls, db, template_id, admin_id, file):
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload Excel.")

        contents = await file.read()

        df = pd.read_excel(io.BytesIO(contents))
        df = df.where(pd.notnull(df), None)

        new_leads = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            new_leads.append(
                LeadResponse(
                    id=generate_id(),
                    template_id=template_id,
                    admin_id=admin_id,
                    submitted_data=row_dict,
                )
            )

        try:
            db.bulk_save_objects(new_leads)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

        return {"message": f"Successfully uploaded {len(new_leads)} leads"}



