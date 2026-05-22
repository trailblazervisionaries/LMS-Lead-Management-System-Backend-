from app.backgroundTasks.MonitorAsync import MonitorAsync
from app.templates.send_template_mail import MailTemplatesService
from sqlalchemy import select
from app.models.lead_form import LeadResponse
class CustomMailService:

    @staticmethod
    async def send_custom_email_(email_to, subject, body):
        MonitorAsync.deferred(
            MailTemplatesService.send_custom_email, 
            email_to,
            subject,
            body
            )
        return {"status": "success", "message": "Email queued for delivery successfully"}

    @staticmethod
    async def send_bulk_custom_email_(email_to, subject: str, body: str):
        for em in email_to:
            MonitorAsync.deferred(
                MailTemplatesService.send_custom_email, 
                em.email,
                subject,
                body
            )
        
        return {
            "status": "success", 
            "message": f"{len(email_to)} Emails queued for delivery successfully"
        }
    

    @staticmethod
    async def send_bulk_custom_email_to_all_users(db, admin_id, subject, body):
        stmt = (
            select(LeadResponse.submitted_data)
            .where(
                LeadResponse.admin_id == admin_id, 
                LeadResponse.is_deleted == False
            )
        )
        
        result = await db.execute(stmt)
    
        submitted_data_list = result.scalars().all()
        
        extracted_emails = []
        
        for data in submitted_data_list:
            if not data:
                continue
                
            # variations of the "email" key case-insensitively
            email = None
            for key in ["email", "Email", "EMAIL", "Email Address"]:
                if key in data:
                    email = data[key]
                    break 
            
            # validate that an email string was actually found
            if email and isinstance(email, str) and "@" in email:
                extracted_emails.append(email.strip())
        
        for email_address in extracted_emails:
            MonitorAsync.deferred(
                MailTemplatesService.send_custom_email, 
                email_address,
                subject,
                body
            )
            
        return {
            "status": "success", 
            "message": f"{len(extracted_emails)} Emails extracted and queued successfully"
        }

        

        