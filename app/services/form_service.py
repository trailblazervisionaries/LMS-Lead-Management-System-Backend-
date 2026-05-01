from fastapi import Request, Response, HTTPException, status
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy.exc import IntegrityError
from app.core.utils_functions import generate_id
from sqlalchemy import select,insert
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app.models.lead_form import FormTemplate
# from app.templates.send_template_mail import MailTemplatesService
# from app.backgroundTasks.MonitorAsync import MonitorAsync
import traceback
import os
import logging



load_dotenv()
logger = logging.getLogger(__name__)


class FormService:

    @classmethod
    async def create_the_lead_form(cls, db, data, admin_id):
        prev_form = await FormTemplate.get_form_by_admin_id(db, admin_id)
        if prev_form:
            raise HTTPException(400, "Form page already available for this admin")
        
        new_template = FormTemplate(
            admin_id = admin_id,
            # title = data.title,
            # form_color = data.form_color,
            # page_color = data.page_color,
            # border_color = data.border_color,
            collected_from = data.collected_from,
            schema_definition = data.schema_definition
        )
        db.add(new_template)
        await db.commit()
        await db.refresh(new_template)
        return new_template


    @classmethod
    async def update_the_lead_form(cls, db, data, admin_id):
        prev_form = await FormTemplate.get_form_by_admin_id(db, admin_id)
        if not prev_form:
            raise HTTPException(400, "Form page not available for this admin")
        
        if data.admin_id:
            prev_form.admin_id = data.admin_id
        
        if data.title:
            prev_form.title = data.title

        if data.form_color:
            prev_form.form_color = data.form_color
        
        if data.page_color:
            prev_form.page_color = data.page_color
        
        if data.border_color:
            prev_form.border_color = data.border_color

        if data.schema_definition:
            prev_form.schema_definition = data.schema_definition

        await db.commit()
        await db.refresh(prev_form)
        return prev_form
    

    @classmethod
    async def mark_form_active(cls, db, admin_id):
        prev_form = await FormTemplate.get_form_by_admin_id(db, admin_id)
        if not prev_form:
            raise HTTPException(400, "Form page not available for this admin")

        prev_form.is_active = True
        await db.commit()
        await db.refresh(prev_form)
        return prev_form
    

    @classmethod
    async def mark_form_deactive(cls, db, admin_id):
        prev_form = await FormTemplate.get_form_by_admin_id(db, admin_id)
        if not prev_form:
            raise HTTPException(400, "Form page not available for this admin")

        prev_form.is_active = False
        await db.commit()
        await db.refresh(prev_form)
        return prev_form
    

    @classmethod
    async def delete_form_by_admin_id(cls, db, admin_id):
        prev_form = await FormTemplate.get_form_by_admin_id(db, admin_id)

        if not prev_form:
            raise HTTPException(status_code=404, detail="Form not found for this admin")

        await db.delete(prev_form)
        await db.commit()
        return {"detail": f"Form for admin {admin_id} deleted successfully"}



