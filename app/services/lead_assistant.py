from fastapi import Request, Response, HTTPException, status
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy.exc import IntegrityError
from app.core.utils_functions import generate_id
from sqlalchemy import select,insert
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app.models.user_model import Users
from app.models.lead_form import LeadAssignment
# from app.templates.send_template_mail import MailTemplatesService
# from app.backgroundTasks.MonitorAsync import MonitorAsync
import traceback
import os
import logging
import uuid
from itertools import cycle


load_dotenv()
logger = logging.getLogger(__name__)

class LeadAssistant:

    async def auto_assign_assistant_to_lead(db, admin_id):
        # 1. Get all unassigned leads for this admin
        all_unassigned_leads = await LeadAssignment.get_unassigned_leads_by_admin(db, admin_id)
        
        if not all_unassigned_leads:
            return {"message": "No unassigned leads found"}

        # 2. Fetch all active assistants for this admin
        # Assuming your Users table has a role or similar flag
        assistant_query = select(Users).where(
            Users.admin_id == admin_id,
            Users.role == "assistant",
            Users.is_active == True,
        )
        assistants_result = await db.execute(assistant_query)
        active_assistants = assistants_result.scalars().all()

        if not active_assistants:
            return {"message": "No active assistants available for assignment"}

        # 3. Create a Round Robin iterator for assistants
        assistant_cycle = cycle(active_assistants)
        
        # 4. Prepare data for bulk insertion
        assignments_to_create = []
        for lead in all_unassigned_leads:
            next_assistant = next(assistant_cycle)
            assignments_to_create.append({
                "id": str(generate_id()),
                "lead_id": lead.id,
                "assistant_id": next_assistant.user_id,
                "is_deleted": False
                # created_at/updated_at will use your model defaults
            })

        # 5. Bulk insert the assignments efficiently
        if assignments_to_create:
            await db.execute(insert(LeadAssignment), assignments_to_create)
            await db.commit()

        return {
            "leads_assigned": len(assignments_to_create),
            "assistants_involved": len(active_assistants)
        }


    @classmethod
    async def assign_assistant_to_lead_one_by_one(db, assistant_id, lead_id):
        assigned = await LeadAssignment.get_assistant_by_lead_id(db, lead_id)
        if assigned:
            raise HTTPException(404, "Lead is already assign to another person")
        
        new_assignment = LeadAssignment(
            id = str(generate_id()),
            lead_id = lead_id,
            assistant_id = assistant_id
        )

        db.add(new_assignment)
        await db.commit()
        await db.refresh()
        return new_assignment
        


