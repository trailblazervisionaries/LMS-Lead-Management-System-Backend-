from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
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


@router.get("/templates/{admin_id}", response_model=list[FormTemplateResponse])
async def list_templates(request: Request, admin_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role in ("admin", "assistant"):
        raise HTTPException(status_code=403, detail="Only admins can list templates")
    templates = await FormService.get_templates_by_admin(db, admin_id)
    return templates

#  get snippet for the data in json ========================
# @router.get("/template/{template_id}/snippet", response_model=FormSnippetResponse)
# async def get_template_snippet(template_id: str, request: Request, db: Session = Depends(get_db)):
#     role = request.state.user.role
#     admin_id = request.state.user.user_id
#     if role != "admin":
#         raise HTTPException(status_code=403, detail="Only admins can fetch snippet")
#     snippet = await FormService.generate_embed_snippet(db, admin_id, template_id)
#     return {"template_id": template_id, "snippet": snippet}

#  get snippet in text formate =============================
@router.get("/template/{template_id}/snippet",  response_class=PlainTextResponse)
async def get_template_snippet(template_id: str, request: Request, db: Session = Depends(get_db)):
    role = request.state.user.role
    admin_id = request.state.user.user_id
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can fetch snippet")
    snippet = await FormService.generate_embed_snippet(db, admin_id, template_id)
    return snippet


#  get loader script for non-iframe public embed ====================
@router.get("/public/embed/{admin_id}/{template_id}/loader.js", response_class=HTMLResponse)
async def get_embed_loader_script(template_id: str, admin_id: str, db: Session = Depends(get_db)):
    return await FormService.render_embed_loader_script(db, admin_id, template_id)




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

