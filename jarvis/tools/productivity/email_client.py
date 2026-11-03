"""Email client for sending and receiving messages via SMTP/IMAP."""

from __future__ import annotations
import email
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import imaplib
import smtplib
from typing import Any, Dict, List, Optional
from jarvis.core.config import get_settings
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.Email")


class EmailClient:
    """Handles sending notifications and reading unread emails."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> Dict[str, Any]:
        """Send an email via configured SMTP server."""
        sender = self.settings.EMAIL_ADDRESS
        password = self.settings.EMAIL_PASSWORD
        server = self.settings.EMAIL_SMTP_SERVER
        port = self.settings.EMAIL_SMTP_PORT

        if not all([sender, password, server]):
            logger.warning("Email credentials not configured in settings.")
            return {
                "success": False,
                "error": "Email credentials (EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_SMTP_SERVER) are not configured.",
            }

        try:
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = to_address
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html" if is_html else "plain", "utf-8"))

            with smtplib.SMTP(server, port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(sender, password)
                smtp.send_message(msg)

            logger.info(f"Successfully sent email to '{to_address}' with subject '{subject}'")
            return {"success": True, "to": to_address, "subject": subject}
        except Exception as exc:
            logger.error(f"Failed to send email to '{to_address}': {exc}")
            return {"success": False, "error": str(exc)}

    def fetch_unread_emails(self, limit: int = 5) -> List[Dict[str, str]]:
        """Fetch the most recent unread emails via IMAP."""
        username = self.settings.EMAIL_ADDRESS
        password = self.settings.EMAIL_PASSWORD
        server = self.settings.EMAIL_IMAP_SERVER
        port = self.settings.EMAIL_IMAP_PORT

        if not all([username, password, server]):
            logger.warning("IMAP email credentials not configured in settings.")
            return []

        try:
            mail = imaplib.IMAP4_SSL(server, port, timeout=10)
            mail.login(username, password)
            mail.select("INBOX")

            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                mail.logout()
                return []

            email_ids = messages[0].split()
            latest_ids = email_ids[-limit:]
            emails_list = []

            for eid in reversed(latest_ids):
                res, data = mail.fetch(eid, "(RFC822)")
                if res != "OK":
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject, encoding = decode_header(msg.get("Subject", "No Subject"))[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors="ignore")

                sender = msg.get("From", "Unknown")
                emails_list.append({
                    "from": sender,
                    "subject": str(subject),
                    "date": msg.get("Date", ""),
                })

            mail.logout()
            return emails_list
        except Exception as exc:
            logger.error(f"Error fetching unread emails: {exc}")
            return []


# Singleton email client instance
email_client = EmailClient()
