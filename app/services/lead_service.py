from fastapi import Request, Response, HTTPException, status
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy.exc import IntegrityError
from app.core.utils_functions import generate_id
from sqlalchemy import select,insert
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app.models.lead_form import LeadResponse, LeadRemarks, LeadStatusHistory
# from app.templates.send_template_mail import MailTemplatesService
# from app.backgroundTasks.MonitorAsync import MonitorAsync
import traceback
import pandas as pd
import os
import io
import logging


load_dotenv()
logger = logging.getLogger(__name__)

class LeadService:

    @classmethod
    async def add_new_lead(cls, db, data, admin_id):
        lead = await LeadResponse.get_lead(db, admin_id, data.email, data.phone)
        if lead:
            raise HTTPException(400, "Your Lead already recorded Team will get back to you Shortly")
        
        new_lead = LeadResponse(
            id = generate_id(),
            template_id = data.template_id,
            admin_id = admin_id,
            submitted_data = data.submitted_data
        )
        
        new_history = LeadStatusHistory(
            id = generate_id(),
            lead_id = data.lead_id,
            status = data.status,
        )

        db.add(new_lead)
        db.add(new_history)
        await db.commit()

        await db.refresh(new_lead)
        await db.refresh(new_lead)
        return {
            "lead" : new_lead,
            "history": new_history
        }
    



    @classmethod
    async def upload_leads(db, template_id, admin_id, file):
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload Excel.")

        # 2. Read Excel into memory
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Fill NaN values to avoid DB errors
        df = df.where(pd.notnull(df), None)

        new_leads = []
        
        # 3. Iterate and create objects
        for _, row in df.iterrows():
            # Convert row to a dictionary for 'submitted_data'
            row_dict = row.to_dict()
            
            new_lead = LeadResponse(
                id=generate_id(),
                template_id=template_id,
                admin_id=admin_id,
                submitted_data=row_dict  # Storing the whole row as JSON
            )
            new_leads.append(new_lead)
        
        # 4. Batch insert for efficiency
        try:
            db.bulk_save_objects(new_leads)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

        return {"message": f"Successfully uploaded {len(new_leads)} leads"}



