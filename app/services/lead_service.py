from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.core.utils_functions import generate_id
from sqlalchemy import select, insert, func, or_, delete
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
        logger.info("LeadService: Template found for the peovided id.")
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
        logger.info("LeadService: new lead with their status history created successfully.")
        await cls.auto_assign_lead(db, admin_id, new_lead.id)
        logger.info("LeadService: lead auto assigned amoung the available assistants.")
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
        logger.info("LeadService:fetched the detials of available Assistants for assigning the leads.")
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
        logger.info("LeadService: Lead is assigned and the status history also changed successfully.")
        await db.commit()
        return new_assignment

    async def get_lead_by_id(db, lead_id):
        stmt = (select(LeadResponse).where(LeadResponse.id == lead_id))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def assign_unassigned_leads(cls, db: Session, admin_id: str):
        unassigned_leads = await LeadAssignment.get_unassigned_leads_by_admin(db, admin_id)
        if not unassigned_leads:
            return {"leads_assigned": 0, "assistants_involved": 0}
        logger.info("LeadService: collected the data od unassigned leads.")
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
        logger.info("LeadService: Fetched the assistant data to assignmen the leads.")
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
            logger.info("LeadService: leads assigned successfully and lead status also changed successsfully.")
            await db.commit()

        return {
            "leads_assigned": assignments_created,
            "assistants_involved": len(assistants),
        }
    

    @classmethod
    async def assign_unassigned_leads_to_specific_user(cls, db, admin_id, data):
            logger.info("lead_id", data.lead_id)
            lead_assign = await LeadAssignment.get_by_lead_id(db, data.lead_id)
            logger.info("lead_assign data ", lead_assign.lead_id)
            if lead_assign:
                lead_assign.is_deleted = True

            new_assignment = LeadAssignment(
                id=generate_id(data.lead_id),
                lead_id=data.lead_id,
                assistant_id=data.assistant_id,
            )
            db.add(new_assignment)
            status = LeadStatusHistory(
                id=generate_id(data.assistant_id),
                lead_id=data.lead_id,
                status="Assigned",
                changed_by=data.assistant_id,
            )
            db.add(status)
            await db.commit()
            return {
                "id": new_assignment.id,
                "lead_id": new_assignment.lead_id,
                "status": status.status,
                "changed_by": status.changed_by,
                "created_at": new_assignment.created_at,
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
        logger.info("LeadService: Lead is assignd to a specific assistant.")
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
        logger.info("LeadService: leads data find successfully.")
        if role == "assistant":
            assignment = await LeadAssignment.get_assistant_by_lead_id(db, lead_id)
            if not assignment or assignment.assistant_id != user_id:
                raise HTTPException(status_code=403, detail="Lead not assigned to this assistant")
            logger.info("LeadService: Assignment data fetched Successfully.")
        if data.status:
            status_entry = LeadStatusHistory(
                id=generate_id(user_id),
                lead_id=lead_id,
                status=data.status,
                changed_by=user_id,
            )
            db.add(status_entry)
            logger.info("LeadService: lead status history updated successfully.")


        if data.remarks or data.next_follow_up_date is not None or data.is_completed is not None:
            remark_entry = LeadRemarks(
                id=generate_id(lead_id),
                for_lead=lead_id,
                remarks=data.remarks,
                next_follow_up_date=data.next_follow_up_date,
                is_completed=data.is_completed if data.is_completed is not None else False,
            )
            db.add(remark_entry)
            logger.info("LeadService: lead remarks add successfully.")
        await db.commit()
        await db.refresh(lead)
        return lead
    

    @classmethod
    async def delete_lead_permanentaly(cls, db, lead_id):
        lead = await LeadResponse.get_lead_by_id(db, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        await db.execute(
            delete(LeadAssignment).where(LeadAssignment.lead_id == lead_id)
        )
        await db.execute(
            delete(LeadRemarks).where(LeadRemarks.for_lead == lead_id)
        )
        await db.execute(
            delete(LeadStatusHistory).where(LeadStatusHistory.lead_id == lead_id)
        )
        await db.delete(lead)
        await db.commit()
        logger.info("LeadService: lead data deleted permanently successfully.")
        return {"detail": f"Lead with id {lead_id} deleted successfully."}


    @classmethod
    async def lead_mark_deleted(cls, db, lead_id):
        lead = await LeadResponse.get_by_id(db, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="lead not found.")
        lead.is_deleted = True
        await db.commit()
        await db.refresh(lead)
        return {"detail": f"Lead with id : {lead_id} marked deleted successfully."}


    @classmethod
    async def get_todays_followups(cls, db: Session, date: str, assistant_id: str = None, admin_id: str = None):
        return await LeadRemarks.get_today_follow_ups(db, date, admin_id, assistant_id)


    @classmethod
    async def get_lead_history(cls, db: Session, lead_id: str):
        lead = await LeadResponse.get_lead_by_id(db, lead_id)
        if not lead:
            return None
        logger.info("LeadService: lead data fetched successfully.")
        history = await LeadStatusHistory.get_all_lead_history(db, lead_id)
        logger.info("LeadServices: lead history data fetched successfully.")
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
        
        # Validate template status
        template = await FormTemplate.get_form_by_id(db, template_id)
        logger.info("LeadService: template data fetched successfully.")
        if not template or not template.is_active:
            raise HTTPException(status_code=404, detail="Lead form template not found or inactive")

        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        if df.empty:
            return {"message": "No leads found in the file"}

        # Handle null values first safely
        df = df.fillna("")

        # Helper function to find dictionary values using case-insensitive keys
        def get_case_insensitive_value(row_dict, target_key):
            # CRITICAL FIX: Ensure row_dict is an actual, valid dictionary before searching keys
            if not row_dict or not isinstance(row_dict, dict):
                return None
            for key, value in row_dict.items():
                if str(key).strip().lower() == target_key.lower():
                    return str(value).strip() if (value is not None and value != "") else None
            return None

        # Extract clean identifiers from Excel dynamically supporting any casing
        excel_emails = list({
            get_case_insensitive_value(row.to_dict(), "email")
            for _, row in df.iterrows()
            if get_case_insensitive_value(row.to_dict(), "email") is not None
        })
        excel_phones = list({
            get_case_insensitive_value(row.to_dict(), "phone")
            for _, row in df.iterrows()
            if get_case_insensitive_value(row.to_dict(), "phone") is not None
        })

        existing_emails = set()
        existing_phones = set()

        if excel_emails or excel_phones:
            conditions = []
            if excel_emails:
                conditions.append(LeadResponse.submitted_data["email"].as_string().in_(excel_emails))
            if excel_phones:
                conditions.append(LeadResponse.submitted_data["phone"].as_string().in_(excel_phones))

            query = select(LeadResponse.submitted_data).where(
                LeadResponse.admin_id == admin_id,
                or_(*conditions)
            )
            
            result = await db.execute(query)
            existing_leads = result.scalars().all()

            for data in existing_leads:
                # CRITICAL FIX: Skip records if the database returned a None/Empty row context
                if data and isinstance(data, dict):
                    email_val = get_case_insensitive_value(data, "email")
                    phone_val = get_case_insensitive_value(data, "phone")
                    if email_val:
                        existing_emails.add(email_val)
                    if phone_val:
                        existing_phones.add(phone_val)

        lead_mappings = []
        history_mappings = []
        created_lead_ids = []
        seen_in_excel = set()

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            
            email = get_case_insensitive_value(row_dict, "email")
            phone = get_case_insensitive_value(row_dict, "phone")

            if (email and email in existing_emails) or (phone and phone in existing_phones):
                continue
            
            excel_key = (email, phone)
            if excel_key in seen_in_excel:
                continue
            seen_in_excel.add(excel_key)

            # SAFETIED ID GENERATION
            try:
                lead_id = generate_id() 
                if not lead_id:
                    raise ValueError("ID generation returned None")
            except Exception as id_err:
                raise HTTPException(status_code=500, detail=f"ID generation module failure: {str(id_err)}")
                
            created_lead_ids.append(lead_id)

            # Sanitize dictionary values for clean JSON types while keeping original key names
            sanitized_data = {k: (None if (v == "" or v is None) else v) for k, v in row_dict.items()}

            lead_mappings.append({
                "id": lead_id,
                "template_id": template_id,
                "admin_id": admin_id,
                "collected_from": "Manual",
                "submitted_data": sanitized_data,
            })

            try:
                history_id = generate_id()
            except Exception:
                history_id = f"hist_{lead_id}" 

            history_mappings.append({
                "id": history_id,
                "lead_id": lead_id,
                "status": "Created",
            })

        if not lead_mappings:
            return {"message": "All leads already exist or file data was invalid"}

        try:
            await db.execute(insert(LeadResponse), lead_mappings)
            await db.execute(insert(LeadStatusHistory), history_mappings)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error during commit: {str(e)}")

        for lead_id in created_lead_ids:
            await cls.auto_assign_lead(db, admin_id, lead_id)

        return {"message": f"Successfully uploaded and assigned {len(lead_mappings)} leads"}
    




# analytics routes ==========================


    @classmethod
    async def get_lead_status_analytics(
        cls, 
        db: Session, 
        admin_id: str = None, 
        assistant_id: str = None
    ):
        """
        Returns metrics count for 'Created', 'Assigned', 'Contacted', 'Interested', 'Converted'
        filtered dynamically by admin_id or assistant_id.
        """
        
        # 1. Create subquery to isolate the LATEST active history status row for each unique lead
        # This prevents counting old historical transitions for the same lead.
        latest_status_subquery = (
            select(
                LeadStatusHistory.lead_id,
                LeadStatusHistory.status
            )
            .distinct(LeadStatusHistory.lead_id)
            .where(LeadStatusHistory.is_deleted == False)
            .order_by(LeadStatusHistory.lead_id, LeadStatusHistory.created_at.desc())
        ).subquery()

        # 2. Build the main query joining LeadResponse with our cleaned subquery status profile
        stmt = select(
            # Conditional aggregation counts matching status instances cleanly in 1 database pass
            func.count().filter(latest_status_subquery.c.status == "Created").label("total_created"),
            func.count().filter(latest_status_subquery.c.status == "Assigned").label("total_assigned"),
            func.count().filter(latest_status_subquery.c.status == "Contacted").label("total_contacted"),
            func.count().filter(latest_status_subquery.c.status == "Interested").label("total_interested"),
            func.count().filter(latest_status_subquery.c.status == "Converted").label("total_converted")
        ).select_from(LeadResponse).join(
            latest_status_subquery, 
            LeadResponse.id == latest_status_subquery.c.lead_id
        ).where(
            LeadResponse.is_deleted == False
        )

        # 3. Dynamically apply business isolation parameters (Admin scoping vs Assistant assignment mapping)
        if assistant_id:
            # Join assignments table to isolate context down to a specific working assistant identity
            stmt = stmt.join(
                LeadAssignment, 
                LeadAssignment.lead_id == LeadResponse.id
            ).where(
                LeadAssignment.assistant_id == assistant_id,
                LeadAssignment.is_deleted == False
            )
        elif admin_id:
            # Fallback to general administrative tenant perimeter checks
            stmt = stmt.where(LeadResponse.admin_id == admin_id)
        else:
            # Prevent open table scanning if parameters are accidentally omitted
            return {
                "total_created": 0, "total_assigned": 0, "total_contacted": 0,
                "total_interested": 0, "total_converted": 0
            }

        # 4. Execute single optimized database roundtrip fetch
        result = await db.execute(stmt)
        row = result.fetchone()

        # Return results as a clean dictionary map matching your requirements
        return {
            "total_created": row.total_created or 0,
            "total_assigned": row.total_assigned or 0,
            "total_contacted": row.total_contacted or 0,
            "total_interested": row.total_interested or 0,
            "total_converted": row.total_converted or 0
        }



    