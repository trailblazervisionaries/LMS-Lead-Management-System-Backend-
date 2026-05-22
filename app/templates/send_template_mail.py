from app.core.mail_service import MailService
from celery import shared_task
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

SUPPORT_MAIL = os.getenv("SUPPORT_MAIL","sales@lmps.com")
class MailTemplatesService:
    @staticmethod
    def mask_email(email:str):
        if "@" not in email:
            return email
        
        local, domain = email.split("@", 1)
        if len(local) <= 3:
            masked_local = local[:-1] + "*" if len(local) > 1 else "*"
        else:
            masked_local = local[:-3] + "***"
        return f"{masked_local}@{domain}"
    

    @staticmethod
    @shared_task(name="app.template.send_template_mail.send_credentials_template")
    def send_credentials_template(email: str, name: str, role: str, password: str, created_by: str = None):
        masked_email = MailTemplatesService.mask_email(email)
        role = role.lower()

        subjects = {
            "admin": "Thank You for Registering in Lead Management Portal.",
            "assistant": f"Your assistant Account has been Created by {created_by} in Lead Management Portal.",
        }

        subject = subjects.get(role, "Your Lead Management Portal Account Details")

        html_message = f"""
            <html>
                <body>
                    <div>
                        <h2>🎉 Welcome to {'Lead Management Portal'} 🎉</h2>

                        <p>Hi <strong>{name}</strong>,</p>

                        <p>
                            Your <strong>{role.capitalize()}</strong> account has been created successfully.
                        </p>

                        <div class="highlight">
                            <p><strong>Login Credentials</strong></p>
                            <ul>
                                <li><strong>Email:</strong> {masked_email}</li>
                                <li><strong>Password:</strong> {password}</li>
                            </ul>
                        </div>

                        <p>
                            ⚠️ <strong>Security Note:</strong>  
                            This is a temporary password. Please change it immediately after logging in.
                        </p><br>
                        <p>Need help? Contact us at <strong>{SUPPORT_MAIL}</strong></p><br>
                        <div class="footer">
                            Warm Regards, <br>
                            <strong>Lead Management Team<strong><br>
                            {f"({created_by})" if created_by else ""}
                        </div>
                    </div>
                </body>
            </html>
        """

        asyncio.run(MailService.send_mail(email, subject, html_message))


    @staticmethod
    @shared_task(name="app.template.send_template_mail.send_otp_template")
    def send_otp_template(email: str, otp: str):
        masked_email = MailTemplatesService.mask_email(email)
        subject = "Your One-Time Password (OTP) for Lead Management Portal."
        html_message = f"""
            <html>
                <body>
                    <div>
                        <h2>🔐 OTP Verification</h2>

                        <p>Dear <strong>{masked_email}</strong>,</p>

                        <p>Your One-Time Password (OTP) is:</p>

                        <div class="highlight" style="text-align:center;">
                            <div class="otp">{otp}</div>
                        </div>

                        <p>
                            This OTP is valid for <strong>10 minutes</strong>.  
                            Please do not share it with anyone.
                        </p>
                        <br>
                        <p>Need help? Contact us at <strong>{SUPPORT_MAIL}</strong></p><br>
                        <div class="footer">
                            Warm Regards,<br>
                            <strong>Lead Management Team<strong>
                        </div>
                    </div>
                </body>
            </html>
        """

        asyncio.run(MailService.send_mail(email, subject, html_message))



    @staticmethod
    @shared_task(name="app.template.send_template_mail.send_notif_password_change")
    def send_notif_password_change(email: str):
        masked_email = MailTemplatesService.mask_email(email)
        subject = "Your Lead Management Password Has Been Changed"
        html_message = f"""
            <html>
                <body>
                    <div>
                        <h2>🔒 Password Changed</h2>

                        <p>Dear <strong>{masked_email}</strong>,</p>

                        <p>
                            This is to inform you that your Lead Management Portal account password has been
                            <strong>changed successfully</strong>.
                        </p>

                        <div class="highlight">
                            <p>
                                If you did <strong>NOT</strong> initiate this change,  
                                please contact support immediately.
                            </p>
                        </div>
                        <br>
                        <p>Need help? Contact us at <strong>{SUPPORT_MAIL}</strong></p><br>

                        <div class="footer">
                            Warm Regards,<br>
                            <strong>Lead Management Team<strong>
                        </div>
                    </div>
                </body>
            </html>
        """
        asyncio.run(MailService.send_mail(email, subject, html_message))



    @staticmethod
    @shared_task(name="app.template.send_template_mail.send_custom_email")
    def send_custom_email(email_to: str, subject: str, body: str):
        """
        Generic task to send custom emails, mimicking a Gmail compose action.
        """
        html_message = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333333;">
                <div>Dear Sir/Ma'am </div>
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        {body}
                    </div>
                    <div>
                        <center>Thankyou For Your Important Time</center>
                    </div>
                    <br>
                    <p>Need help? Contact us at <strong>{SUPPORT_MAIL}</strong></p><br>
                    <div>
                        Warm Regards,<br>
                        <strong>Lead Management Team</strong>
                    </div>
                </body>
            </html>
        """

        asyncio.run(MailService.send_mail(email_to, subject, html_message))

