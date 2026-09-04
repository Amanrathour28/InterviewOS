import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Enterprise email notification service integrated with Mailpit in development."""

    def __init__(self):
        self.smtp_host = getattr(settings, "SMTP_HOST", "localhost")
        self.smtp_port = int(getattr(settings, "SMTP_PORT", 1025))
        self.sender_email = getattr(settings, "EMAIL_FROM", "no-reply@interviewos.com")
        self.sender_name = getattr(settings, "EMAIL_FROM_NAME", "InterviewOS")

    def _send(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Sends email synchronously in worker/thread pool or catches connection exceptions."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.sender_name} <{self.sender_email}>"
            msg["To"] = to_email

            plain_text = text_content or html_content
            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=2.0) as server:
                server.sendmail(self.sender_email, [to_email], msg.as_string())
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
        except Exception as e:
            # During unit tests or offline development where Mailpit is not running, log cleanly without breaking transaction
            logger.warning(f"Failed to deliver email to {to_email} via {self.smtp_host}:{self.smtp_port}: {e}")
            return False

    async def send_interview_invitation(
        self,
        to_email: str,
        recipient_name: str,
        interview_title: str,
        start_time_str: str,
        timezone_str: str,
        duration_minutes: int,
        invite_url: str,
    ) -> bool:
        subject = f"Interview Invitation: {interview_title}"
        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background-color: #0d0e14; color: #ffffff; border-radius: 12px; border: 1px solid #27272a;">
            <div style="margin-bottom: 20px;">
                <h1 style="color: #6366f1; font-size: 20px; font-weight: bold; margin: 0;">InterviewOS</h1>
                <p style="color: #a1a1aa; font-size: 13px; margin-top: 4px;">Intelligent Technical Interview Platform</p>
            </div>
            <div style="background-color: #18181b; padding: 20px; border-radius: 8px; border: 1px solid #27272a; margin-bottom: 24px;">
                <h2 style="font-size: 16px; margin: 0 0 12px 0; color: #ffffff;">{interview_title}</h2>
                <p style="color: #d4d4d8; font-size: 14px; line-height: 1.5; margin: 0 0 16px 0;">Hello {recipient_name}, you have been invited to participate in a technical interview session.</p>
                <div style="font-size: 13px; color: #a1a1aa; line-height: 1.8;">
                    <div><strong>Date & Time:</strong> <span style="color: #ffffff;">{start_time_str} ({timezone_str})</span></div>
                    <div><strong>Duration:</strong> <span style="color: #ffffff;">{duration_minutes} minutes</span></div>
                </div>
            </div>
            <div style="text-align: center; margin-bottom: 24px;">
                <a href="{invite_url}" style="display: inline-block; background-color: #6366f1; color: #ffffff; font-weight: 600; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-size: 14px;">Review & Respond to Invitation</a>
            </div>
            <p style="color: #71717a; font-size: 12px; text-align: center; margin: 0;">This invitation link will expire in 7 days. If you did not expect this message, please disregard.</p>
        </div>
        """
        return self._send(to_email, subject, html)

    async def send_interview_scheduled(
        self,
        to_email: str,
        recipient_name: str,
        interview_title: str,
        start_time_str: str,
        timezone_str: str,
        duration_minutes: int,
    ) -> bool:
        subject = f"Interview Scheduled: {interview_title}"
        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; padding: 24px; background: #0d0e14; color: #fff; border-radius: 12px; border: 1px solid #27272a;">
            <h2 style="color: #6366f1;">InterviewOS</h2>
            <p>Hello {recipient_name}, the following session has been confirmed:</p>
            <p><strong>{interview_title}</strong></p>
            <p>Time: {start_time_str} ({timezone_str}) • Duration: {duration_minutes} mins</p>
        </div>
        """
        return self._send(to_email, subject, html)

    async def send_interview_rescheduled(
        self,
        to_email: str,
        recipient_name: str,
        interview_title: str,
        new_start_time_str: str,
        new_timezone_str: str,
        reason: Optional[str] = None,
    ) -> bool:
        subject = f"Interview Rescheduled: {interview_title}"
        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; padding: 24px; background: #0d0e14; color: #fff; border-radius: 12px; border: 1px solid #27272a;">
            <h2 style="color: #f59e0b;">Interview Rescheduled</h2>
            <p>Hello {recipient_name}, your session has been rescheduled to a new time:</p>
            <p><strong>{interview_title}</strong></p>
            <p>New Time: {new_start_time_str} ({new_timezone_str})</p>
            {f'<p>Reason: {reason}</p>' if reason else ''}
        </div>
        """
        return self._send(to_email, subject, html)

    async def send_interview_cancelled(
        self,
        to_email: str,
        recipient_name: str,
        interview_title: str,
        reason: Optional[str] = None,
    ) -> bool:
        subject = f"Interview Cancelled: {interview_title}"
        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; padding: 24px; background: #0d0e14; color: #fff; border-radius: 12px; border: 1px solid #27272a;">
            <h2 style="color: #ef4444;">Interview Cancelled</h2>
            <p>Hello {recipient_name}, the interview session has been cancelled.</p>
            <p><strong>{interview_title}</strong></p>
            {f'<p>Reason: {reason}</p>' if reason else ''}
        </div>
        """
        return self._send(to_email, subject, html)


email_service = EmailService()
