from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.core.utils_functions import generate_id
from app.models.lead_form import FormTemplate
import logging
import os
from dotenv import load_dotenv
import json

load_dotenv()
logger = logging.getLogger(__name__)

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL")
class FormService:

    @classmethod
    async def create_the_lead_form(cls, db: Session, data, admin_id: str):
        form_avl = FormTemplate.get_active_forms_by_admin_id(db, admin_id)
        if form_avl:
            raise HTTPException(400, "Form already available for this admin please delete previous one to create new one")
        new_template = FormTemplate(
            id=generate_id(admin_id),
            admin_id=admin_id,
            schema_definition=data.schema_definition,
        )
        db.add(new_template)
        await db.commit()
        await db.refresh(new_template)
        return new_template

    @classmethod
    async def get_template_by_id(cls, db: Session, template_id: str):
        return await FormTemplate.get_form_by_id(db, template_id)

    @classmethod
    async def get_templates_by_admin(cls, db: Session, admin_id: str):
        return await FormTemplate.get_all_forms_by_admin_id(db, admin_id)

    @classmethod
    async def update_the_lead_form(cls, db: Session, template_id: str, data, admin_id: str):
        existing_template = await FormTemplate.get_form_by_id(db, template_id)
        if not existing_template or existing_template.admin_id != admin_id:
            raise HTTPException(status_code=404, detail="Form template not found")

        if data.schema_definition is not None:
            existing_template.schema_definition = data.schema_definition
        if data.is_active is not None:
            existing_template.is_active = data.is_active

        await db.commit()
        await db.refresh(existing_template)
        return existing_template
    
    
    @classmethod
    async def mark_form_active(cls, db: Session, template_id: str, admin_id: str):
        template = await FormTemplate.get_form_by_id(db, template_id)
        if not template or template.admin_id != admin_id:
            raise HTTPException(status_code=404, detail="Form template not found")
        template.is_active = True
        await db.commit()
        await db.refresh(template)
        return template
    

    @classmethod
    async def mark_form_deactive(cls, db: Session, template_id: str, admin_id: str):
        template = await FormTemplate.get_form_by_id(db, template_id)
        if not template or template.admin_id != admin_id:
            raise HTTPException(status_code=404, detail="Form template not found")
        template.is_active = False
        await db.commit()
        await db.refresh(template)
        return template
    

    @classmethod
    async def delete_form_by_admin_id(cls, db: Session, template_id: str, admin_id: str):
        template = await FormTemplate.get_form_by_id(db, template_id)
        if not template or template.admin_id != admin_id:
            raise HTTPException(status_code=404, detail="Form template not found")
        await db.delete(template)
        await db.commit()
        return {"detail": f"Form template {template_id} deleted successfully"}
    
    
    @classmethod
    async def delete_form_by_template_id(cls, db: Session, template_id: str):
        template = await FormTemplate.get_form_by_id(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Form template not found")
        await db.delete(template)
        await db.commit()
        return {"detail": f"Form template {template_id} deleted successfully"}


#  generate the integration snippets ========= 
    @classmethod
    async def generate_embed_snippet(cls, db: Session, admin_id: str, template_id: str):
        backend_url = (BACKEND_BASE_URL).rstrip("/")
        snippet = f"""
        <div id=\"lms-form-{template_id}\"></div>
        <script>
        (function() {{
            var container = document.getElementById(\"lms-form-{template_id}\");
            if (!container) return;
            var script = document.createElement('script');
            script.src = '{backend_url}/api/form/public/embed/{admin_id}/{template_id}/loader.js';
            script.async = true;
            container.appendChild(script);
        }})();
        </script>""".strip()
        return snippet
    

    @classmethod
    async def render_embed_loader_script(cls, db: Session, admin_id: str, template_id: str):
        template = await FormTemplate.get_form_by_id(db, template_id)
        if not template or not template.is_active:
            return HTMLResponse("<p>Form not found</p>", status_code=404)

        schema = template.schema_definition or {}
        backend_url = (BACKEND_BASE_URL).rstrip("/")
        schema_json = json.dumps(schema)
        button_text = schema.get("submit_button", {}).get("text", "Submit")

        return HTMLResponse(f"""
            (function() {{
                const formConfig = {schema_json};
                const backendUrl = '{backend_url}';
                const templateId = '{template.id}';
                const submitText = '{button_text}';
                const container = document.getElementById('lms-form-' + templateId);
                if (!container) return;

                const style = document.createElement('style');
                style.textContent = `
                    .lms-form-wrapper {{ max-width: 100%; font-family: Arial, sans-serif; }}
                    .lms-form-wrapper form {{ display: grid; gap: 12px; }}
                    .lms-form-wrapper .full {{ grid-column: 1 / -1; }}
                    .lms-form-wrapper label {{ display: block; margin-bottom: 4px; font-weight: 600; }}
                    .lms-form-wrapper input, .lms-form-wrapper textarea {{ width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #ccc; border-radius: 6px; }}
                    .lms-form-wrapper textarea {{ min-height: 100px; resize: vertical; }}
                    .lms-form-wrapper button {{ background: #2563EB; color: white; border: none; border-radius: 6px; padding: 12px 16px; cursor: pointer; }}
                    .lms-form-wrapper button:disabled {{ opacity: 0.65; cursor: not-allowed; }}
                    .lms-form-wrapper .lms-form-message {{ margin-top: 12px; font-size: 0.95rem; }}
                    .lms-form-wrapper .lms-success {{ color: #166534; }}
                    .lms-form-wrapper .lms-error {{ color: #B91C1C; }}
                `;
                document.head.appendChild(style);

                function escapeHtml(value) {{
                    return String(value || '').replace(/[&<>'"`]/g, function(match) {{
                        return {{
                            '&': '&amp;',
                            '<': '&lt;',
                            '>': '&gt;',
                            "'": '&#39;',
                            '"': '&quot;',
                            '`': '&#96;'
                        }}[match];
                    }});
                }}

                function renderField(field) {{
                    const name = escapeHtml(field.name || (field.label || '').toLowerCase().replace(/\s+/g, '_'));
                    const label = escapeHtml(field.label || '');
                    const placeholder = escapeHtml(field.placeholder || '');
                    const required = field.required ? 'required' : '';
                    const fieldClass = field.width === 'full' ? 'full' : '';
                    if (field.type === 'textarea') {{
                        return `
                            <div class="${{fieldClass}}">
                                <label>${{label}}</label>
                                <textarea name="${{name}}" placeholder="${{placeholder}}" ${{required}}></textarea>
                            </div>
                        `;
                    }}
                    const inputType = ['text','email','tel','number','date','url','password'].includes(field.type) ? field.type : 'text';
                    return `
                        <div class="${{fieldClass}}">
                            <label>${{label}}</label>
                            <input type="${{inputType}}" name="${{name}}" placeholder="${{placeholder}}" ${{required}} />
                        </div>
                    `;
                }}

                const fieldsHtml = (formConfig.fields || []).map(renderField).join('');
                container.innerHTML = `
                    <div class="lms-form-wrapper">
                        <form class="lms-form" novalidate>
                            ${{fieldsHtml}}
                            <button type="submit">${{escapeHtml(submitText)}}</button>
                        </form>
                        <div class="lms-form-message"></div>
                    </div>
                `;

                const form = container.querySelector('form');
                const message = container.querySelector('.lms-form-message');
                const button = form.querySelector('button');

                form.addEventListener('submit', async function(event) {{
                    event.preventDefault();
                    button.disabled = true;
                    button.textContent = 'Submitting...';
                    const formData = new FormData(form);
                    const submittedData = {{}};
                    for (const [key, value] of formData.entries()) {{
                        submittedData[key] = value;
                    }}

                    const payload = new FormData();
                    payload.append('template_id', templateId);
                    payload.append('collected_from', document.referrer || 'website');
                    payload.append('submitted_data', JSON.stringify(submittedData));

                    try {{
                        const response = await fetch(backendUrl + '/api/lead/add', {{ method: 'POST', body: payload }});
                        if (response.ok) {{
                            message.innerHTML = '<p class="lms-success">Submitted successfully</p>';
                            form.reset();
                        }} else {{
                            const errorText = await response.text();
                            message.innerHTML = '<p class="lms-error">Submission failed</p>';
                            console.error('Lead submit error:', errorText);
                        }}
                    }} catch (error) {{
                        message.innerHTML = '<p class="lms-error">Submission failed</p>';
                        console.error('Lead submit error:', error);
                    }} finally {{
                        button.disabled = false;
                        button.textContent = submitText;
                    }}
                }});
            }})();
            """, media_type="application/javascript")

