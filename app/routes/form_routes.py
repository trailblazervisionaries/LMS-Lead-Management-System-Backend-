from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from app.config.database import get_db
from app.services.form_service import FormService
from app.schemas.form_schemas import (
    FormTemplateCreate,
    FormTemplateUpdate,
    FormTemplateResponse,
    FormSnippetResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession as Session
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/template", response_model=FormTemplateResponse)
async def create_template(data: FormTemplateCreate, request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user.user_id
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create form templates")
    template = await FormService.create_the_lead_form(db, data, user_id)
    return template


@router.get("/template/{template_id}", response_model=FormTemplateResponse)
async def get_template(template_id: str, db: Session = Depends(get_db)):
    template = await FormService.get_template_by_id(db, template_id)
    if not template or not template.is_active:
        raise HTTPException(status_code=404, detail="Form template not found")
    return template


@router.put("/template/{template_id}", response_model=FormTemplateResponse)
async def update_template(template_id: str, data: FormTemplateUpdate, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update form templates")
    template = await FormService.update_the_lead_form(db, template_id, data, request.state.user.user_id)
    return template


@router.get("/templates", response_model=list[FormTemplateResponse])
async def list_templates(request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can list templates")
    templates = await FormService.get_templates_by_admin(db, request.state.user.user_id)
    return templates

#  get snippet for the data ========================
@router.get("/template/{template_id}/snippet")
async def get_template_snippet(template_id: str, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    admin_id = request.state.user.user_id
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can fetch snippet")
    snippet = await FormService.generate_embed_snippet(db, admin_id, template_id)
    return snippet

#  get public form for the lead
@router.get("/public/embed/{admin_id}/{template_id}", response_class=HTMLResponse)
async def make_embed_form_render(template_id: str, admin_id: str, db: Session = Depends(get_db)):
    return await FormService.render_embed_form(db, admin_id, template_id)


@router.delete("/template/{template_id}")
async def delete_template(request: Request, template_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can perform this operations.")
    result = await FormService.delete_form_by_template_id(db, template_id)
    return result


@router.put("/template/activate/{template_id}")
async def activate_template(request: Request, template_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    admin_id = request.state.user.user_id
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can perform this operations.")
    result = await FormService.mark_form_active(db, template_id, admin_id)
    return result


@router.put("/template/deactivate/{template_id}")
async def deactivate_template(request: Request, template_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    admin_id = request.state.user.user_id
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can perform this operations.")
    result = await FormService.mark_form_deactive(db, template_id, admin_id)
    return result

