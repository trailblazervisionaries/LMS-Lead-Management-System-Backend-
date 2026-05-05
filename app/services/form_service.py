from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.core.utils_functions import generate_id
from app.models.lead_form import FormTemplate
import logging

logger = logging.getLogger(__name__)


class FormService:

    @classmethod
    async def create_the_lead_form(cls, db: Session, data, admin_id: str):
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
    async def generate_embed_snippet(cls, db: Session, template_id: str):
        template = await FormTemplate.get_form_by_id(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Form template not found")

        snippet = f"""
        <div id=\"lms-lead-form-{template.id}\"></div>
        <script>
        (async function() {{
        const backendUrl = "{{BACKEND_BASE_URL}}";
        const target = document.getElementById('lms-lead-form-{template.id}');

        const response = await fetch(`${{backendUrl}}/api/lead/template/{template.id}`);
        if (!response.ok) {{
            target.innerHTML = '<p>Unable to load lead form.</p>';
            return;
        }}

        const formDefinition = await response.json();
        const form = document.createElement('form');
        form.id = 'lms-form-{template.id}';

        const fields = formDefinition.schema_definition || [];
        fields.forEach(field => {{
            const wrapper = document.createElement('div');
            const label = document.createElement('label');
            label.textContent = field.label || field.name || 'Field';
            wrapper.appendChild(label);

            const input = document.createElement(field.type === 'textarea' ? 'textarea' : 'input');
            input.name = field.name || field.label?.toLowerCase().replace(/\s+/g, '_');
            input.required = field.required || false;
            if (field.type && field.type !== 'textarea') {{
            input.type = field.type;
            }}
            wrapper.appendChild(input);
            form.appendChild(wrapper);
        }});

        const button = document.createElement('button');
        button.type = 'submit';
        button.textContent = 'Submit';
        form.appendChild(button);

        form.addEventListener('submit', async event => {{
            event.preventDefault();
            const data = {{ template_id: '{template.id}', submitted_data: {{}} }};
            new FormData(form).forEach((value, key) => {{ data.submitted_data[key] = value; }});

            const submitResponse = await fetch(`${{backendUrl}}/api/lead/add`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(data),
            }});

            if (submitResponse.ok) {{
            target.innerHTML = '<p>Thank you! Your lead has been submitted.</p>';
            }} else {{
            const error = await submitResponse.json();
            target.innerHTML = `<p>Error: ${{error.detail || 'Unable to submit form.'}}</p>`;
            }}
        }});

        target.appendChild(form);
        }})();
        </script>
        """
        return {"template_id": template.id, "snippet": snippet}








#  popup form open when user visit that site and not filled the form till now ------
# snippet = f"""
# <div id="lms-popup-overlay-{template.id}" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 999999; justify-content: center; align-items: center;">
#     <div id="lms-popup-content" style="background: #fff; padding: 30px; border-radius: 8px; position: relative; max-width: 500px; width: 90%; max-height: 90vh; overflow-y: auto; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
#         <button id="lms-close-{template.id}" style="position: absolute; top: 10px; right: 10px; background: none; border: none; font-size: 24px; cursor: pointer; line-height: 1;">&times;</button>
#         <div id="lms-lead-form-{template.id}"></div>
#     </div>
# </div>

# <script>
# (async function() {{
#     const storageKey = 'lms_form_filled_{template.id}';
    
#     // 1. CHECK IF ALREADY SUBMITTED
#     if (localStorage.getItem(storageKey)) {{
#         console.log("User already submitted this form. Skipping popup.");
#         return; 
#     }}

#     const backendUrl = window.lmsBackendUrl || "{{BACKEND_BASE_URL}}";
#     const overlay = document.getElementById('lms-popup-overlay-{template.id}');
#     const closeBtn = document.getElementById('lms-close-{template.id}');
#     const target = document.getElementById('lms-lead-form-{template.id}');

#     closeBtn.onclick = () => {{ overlay.style.display = 'none'; }};
#     overlay.onclick = (e) => {{ if(e.target === overlay) overlay.style.display = 'none'; }};

#     const response = await fetch(`${{backendUrl}}/api/lead/template/{template.id}`);
#     if (!response.ok) return;

#     const formDefinition = await response.json();
#     const form = document.createElement('form');
    
#     const fields = formDefinition.schema_definition || [];
#     fields.forEach(field => {{
#         const wrapper = document.createElement('div');
#         wrapper.style.marginBottom = '10px';
#         const label = document.createElement('label');
#         label.textContent = field.label;
#         label.style.display = 'block';
#         wrapper.appendChild(label);
        
#         const input = document.createElement(field.type === 'textarea' ? 'textarea' : 'input');
#         input.name = field.name || field.label?.toLowerCase().replace(/\s+/g, '_');
#         input.required = field.required || false;
#         input.placeholder = field.placeholder || '';
#         if (field.type !== 'textarea') input.type = field.type;
        
#         input.style.width = '100%';
#         input.style.height = field.height || 'auto';
#         input.style.backgroundColor = field.color || '#fff';
#         input.style.border = field.border || '1px solid #ccc';
#         input.style.padding = '8px';
#         input.style.boxSizing = 'border-box';
        
#         wrapper.appendChild(input);
#         form.appendChild(wrapper);
#     }});

#     const button = document.createElement('button');
#     button.type = 'submit';
#     button.textContent = 'Submit';
#     button.style.width = '100%';
#     button.style.padding = '10px';
#     button.style.marginTop = '10px';
#     button.style.cursor = 'pointer';
#     form.appendChild(button);

#     form.addEventListener('submit', async event => {{
#         event.preventDefault();
#         const data = {{ template_id: '{template.id}', submitted_data: {{}} }};
#         new FormData(form).forEach((value, key) => {{ data.submitted_data[key] = value; }});
        
#         const submitResponse = await fetch(`${{backendUrl}}/api/lead/add`, {{
#             method: 'POST',
#             headers: {{ 'Content-Type': 'application/json' }},
#             body: JSON.stringify(data),
#         }});

#         if (submitResponse.ok) {{
#             // 2. SET THE SUCCESS FLAG
#             localStorage.setItem(storageKey, 'true');
            
#             target.innerHTML = '<h3 style="text-align:center;">Thank you! Your lead has been submitted.</h3>';
#             setTimeout(() => {{ overlay.style.display = 'none'; }}, 2500);
#         }}
#     }});

#     target.appendChild(form);

#     // 3. SHOW POPUP AFTER 3 SECONDS
#     setTimeout(() => {{
#         overlay.style.display = 'flex';
#     }}, 3000);

# }})();
# </script>
# """
