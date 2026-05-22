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

        # Dynamic body text adjustment based on role to match the UI flow
        if role == "admin":
            intro_text = "We are pleased to inform you that your registration has been successfully approved."
        else:
            intro_text = f"Your account has been created by {created_by or 'the administrator'}."

        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; background-color: #f4f6f8; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333333; -webkit-font-smoothing: antialiased;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #f4f6f8; padding: 40px 20px;">
                <tr>
                    <td align="center">
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e1e4e8; border-bottom: none;">
                            <!-- Header Section -->
                            <tr>
                                <td style="background-color: #c26d03; padding: 35px 40px;">
                                    <p style="margin: 0 0 10px 0; color: rgba(255, 255, 255, 0.7); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">LEAD MANAGEMENT PORTAL</p>
                                    <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 400; letter-spacing: -0.5px;">Registration Approved</h1>
                                </td>
                            </tr>
                            <!-- Body Section -->
                            <tr>
                                <td style="padding: 40px;">
                                    <p style="margin: 0 0 20px 0; font-size: 15px; color: #333333;">Dear <strong style="color: #111111;">{name}</strong>,</p>
                                    
                                    <p style="margin: 0 0 20px 0; font-size: 15px; line-height: 1.6; color: #4f5d73;">
                                        {intro_text}
                                    </p>
                                    
                                    <p style="margin: 0 0 20px 0; font-size: 15px; line-height: 1.6; color: #4f5d73;">
                                        Your account has now been activated as an <strong>{role.capitalize()}</strong>. You may begin accessing the portal using the credentials below:
                                    </p>

                                    <!-- Credentials Box Structure -->
                                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #fdfaf4; border-left: 4px solid #c26d03; margin: 25px 0; border-radius: 0 4px 4px 0;">
                                        <tr>
                                            <td style="padding: 15px 20px;">
                                                <p style="margin: 0 0 8px 0; font-size: 14px; color: #c26d03; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Login Credentials</p>
                                                <p style="margin: 0 0 5px 0; font-size: 14px; color: #333333;"><strong>Email:</strong> {masked_email}</p>
                                                <p style="margin: 0; font-size: 14px; color: #333333;"><strong>Temporary Password:</strong> <code style="font-family: Consolas, Monaco, monospace; background-color: #f1f1f1; padding: 2px 6px; border-radius: 3px;">{password}</code></p>
                                            </td>
                                        </tr>
                                    </table>

                                    <p style="margin: 0 0 20px 0; font-size: 13px; line-height: 1.5; color: #d93838; font-weight: 500;">
                                        ⚠️ <strong>Security Note:</strong> This is a temporary password. Please change it immediately after logging in.
                                    </p>

                                    <p style="margin: 0 0 40px 0; font-size: 15px; line-height: 1.6; color: #4f5d73;">
                                        Need help? Contact us at <a href="mailto:{SUPPORT_MAIL}" style="color: #c26d03; text-decoration: none; font-weight: 500;">{SUPPORT_MAIL}</a>.
                                    </p>

                                    <!-- Sign-off Block -->
                                    <p style="margin: 0; font-size: 15px; color: #4f5d73; line-height: 1.5;">
                                        Regards,<br>
                                        <strong style="color: #0b1a30; font-weight: bold;">Lead Management Team</strong>
                                    </p>
                                </td>
                            </tr>
                        </table>
                        <!-- Footer Section -->
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px;">
                            <tr>
                                <td style="padding: 25px 40px; align: center; text-align: center; font-size: 12px; color: #8a94a6;">
                                    &copy; 2026 Lead Management Portal. All rights reserved.
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
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
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; background-color: #f4f6f8; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333333; -webkit-font-smoothing: antialiased;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #f4f6f8; padding: 40px 20px;">
                <tr>
                    <td align="center">
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e1e4e8; border-bottom: none;">
                            <!-- Header Section -->
                            <tr>
                                <td style="background-color: #c26d03; padding: 35px 40px;">
                                    <p style="margin: 0 0 10px 0; color: rgba(255, 255, 255, 0.7); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">LEAD MANAGEMENT PORTAL</p>
                                    <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 400; letter-spacing: -0.5px;">🔐 OTP Verification</h1>
                                </td>
                            </tr>
                            <!-- Body Section -->
                            <tr>
                                <td style="padding: 40px;">
                                    <p style="margin: 0 0 20px 0; font-size: 15px; color: #333333;">Dear <strong style="color: #111111;">{masked_email}</strong>,</p>
                                    
                                    <p style="margin: 0 0 25px 0; font-size: 15px; line-height: 1.6; color: #4f5d73;">
                                        You have requested a secure verification action. Please use the following One-Time Password (OTP) to complete your request:
                                    </p>

                                    <!-- OTP Display Box Block -->
                                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin: 30px 0;">
                                        <tr>
                                            <td align="center" style="background-color: #fdfaf4; border: 1px dashed #c26d03; padding: 20px; border-radius: 6px;">
                                                <span style="font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: bold; letter-spacing: 6px; color: #c26d03;">{otp}</span>
                                            </td>
                                        </tr>
                                    </table>

                                    <p style="margin: 0 0 25px 0; font-size: 14px; line-height: 1.5; color: #d93838; font-weight: 500;">
                                        ⏳ <strong>Important Note:</strong> This OTP code is valid for exactly <strong>10 minutes</strong> and can only be used once. Please do not share this code with anyone.
                                    </p>

                                    <p style="margin: 0 0 40px 0; font-size: 15px; line-height: 1.6; color: #4f5d73;">
                                        Didn't request this? Please ignore this message, or contact our support team at <a href="mailto:{SUPPORT_MAIL}" style="color: #c26d03; text-decoration: none; font-weight: 500;">{SUPPORT_MAIL}</a> if you notice suspicious activity.
                                    </p>

                                    <!-- Sign-off Block -->
                                    <p style="margin: 0; font-size: 15px; color: #4f5d73; line-height: 1.5;">
                                        Regards,<br>
                                        <strong style="color: #0b1a30; font-weight: bold;">Lead Management Team</strong>
                                    </p>
                                </td>
                            </tr>
                        </table>
                        <!-- Footer Section -->
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px;">
                            <tr>
                                <td style="padding: 25px 40px; align: center; text-align: center; font-size: 12px; color: #8a94a6;">
                                    &copy; 2026 Lead Management Portal. All rights reserved.
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
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
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; background-color: #f4f6f8; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333333; -webkit-font-smoothing: antialiased;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #f4f6f8; padding: 40px 20px;">
                <tr>
                    <td align="center">
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e1e4e8; border-bottom: none;">
                            <!-- Header Section -->
                            <tr>
                                <td style="background-color: #c26d03; padding: 35px 40px;">
                                    <p style="margin: 0 0 10px 0; color: rgba(255, 255, 255, 0.7); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">LEAD MANAGEMENT PORTAL</p>
                                    <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 400; letter-spacing: -0.5px;">🔒 Password Changed</h1>
                                </td>
                            </tr>
                            <!-- Body Section -->
                            <tr>
                                <td style="padding: 40px;">
                                    <p style="margin: 0 0 20px 0; font-size: 15px; color: #333333;">Dear <strong style="color: #111111;">{masked_email}</strong>,</p>
                                    
                                    <p style="margin: 0 0 25px 0; font-size: 15px; line-height: 1.6; color: #4f5d73;">
                                        This email confirms that the password for your Lead Management Portal account has been <strong>changed successfully</strong>.
                                    </p>

                                    <!-- Security Alert Box -->
                                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #fff5f5; border-left: 4px solid #d93838; margin: 25px 0; border-radius: 0 4px 4px 0;">
                                        <tr>
                                            <td style="padding: 15px 20px;">
                                                <p style="margin: 0 0 5px 0; font-size: 14px; color: #d93838; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">⚠️ Security Alert</p>
                                                <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #555555;">
                                                    If you did <strong>NOT</strong> initiate this change, please take immediate action to secure your account or contact our support team.
                                                </p>
                                            </td>
                                        </tr>
                                    </table>

                                    <p style="margin: 0 0 40px 0; font-size: 15px; line-height: 1.6; color: #4f5d73;">
                                        Need assistance? Get in touch with us at <a href="mailto:{SUPPORT_MAIL}" style="color: #c26d03; text-decoration: none; font-weight: 500;">{SUPPORT_MAIL}</a>.
                                    </p>

                                    <!-- Sign-off Block -->
                                    <p style="margin: 0; font-size: 15px; color: #4f5d73; line-height: 1.5;">
                                        Regards,<br>
                                        <strong style="color: #0b1a30; font-weight: bold;">Lead Management Team</strong>
                                    </p>
                                </td>
                            </tr>
                        </table>
                        <!-- Footer Section -->
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px;">
                            <tr>
                                <td style="padding: 25px 40px; align: center; text-align: center; font-size: 12px; color: #8a94a6;">
                                    &copy; 2026 Lead Management Portal. All rights reserved.
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
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
        formatted_body = body.replace("\n", "<br>")

        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; background-color: #f4f6f8; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333333; -webkit-font-smoothing: antialiased;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #f4f6f8; padding: 40px 20px;">
                <tr>
                    <td align="center">
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e1e4e8; border-bottom: none;">
                            <!-- Header Section -->
                            <tr>
                                <td style="background-color: #c26d03; padding: 35px 40px;">
                                    <p style="margin: 0 0 10px 0; color: rgba(255, 255, 255, 0.7); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">LEAD MANAGEMENT PORTAL</p>
                                    <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 400; letter-spacing: -0.5px;">Official Announcement</h1>
                                </td>
                            </tr>
                            <!-- Body Section -->
                            <tr>
                                <td style="padding: 40px;">
                                    <p style="margin: 0 0 20px 0; font-size: 15px; color: #333333;">Dear Sir/Ma'am,</p>
                                    
                                    <!-- Dynamic Compose Body Area -->
                                    <div style="margin: 0 0 30px 0; font-size: 15px; line-height: 1.6; color: #4f5d73;">
                                        {formatted_body}
                                    </div>

                                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin: 25px 0; text-align: center;">
                                        <tr>
                                            <td style="font-size: 14px; color: #c26d03; font-style: italic; font-weight: 500;">
                                                Thank you for your valuable time.
                                            </td>
                                        </tr>
                                    </table>

                                    <p style="margin: 0 0 40px 0; font-size: 15px; line-height: 1.6; color: #4f5d73;">
                                        Need help? Contact us at <a href="mailto:{SUPPORT_MAIL}" style="color: #c26d03; text-decoration: none; font-weight: 500;">{SUPPORT_MAIL}</a>.
                                    </p>

                                    <!-- Sign-off Block -->
                                    <p style="margin: 0; font-size: 15px; color: #4f5d73; line-height: 1.5;">
                                        Warm Regards,<br>
                                        <strong style="color: #0b1a30; font-weight: bold;">Lead Management Team</strong>
                                    </p>
                                </td>
                            </tr>
                        </table>
                        <!-- Footer Section -->
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px;">
                            <tr>
                                <td style="padding: 25px 40px; align: center; text-align: center; font-size: 12px; color: #8a94a6;">
                                    &copy; 2026 Lead Management Portal. All rights reserved.
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        asyncio.run(MailService.send_mail(email_to, subject, html_message))




