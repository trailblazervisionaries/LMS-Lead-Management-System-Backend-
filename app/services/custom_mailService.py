from app.backgroundTasks.MonitorAsync import MonitorAsync
from app.templates.send_template_mail import MailTemplatesService

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

