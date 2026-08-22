"""Built-in mail client, inbox aggregator, and email composer with IMAP/SMTP support and local archiving."""

import email
from email.header import decode_header
import imaplib
import json
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.workspace.storage import workspace_storage


class EmailMessage(BaseModel):
    """Structured representation of an email message."""

    id: str = Field(default_factory=lambda: f"mail_{str(uuid.uuid4())[:8]}")
    sender: str
    recipient: str
    subject: str
    body_text: str = ""
    body_html: str = ""
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    folder: str = "inbox"  # 'inbox' | 'sent' | 'drafts' | 'archive' | 'trash'
    is_read: bool = False
    is_starred: bool = False
    labels: List[str] = Field(default_factory=list)


class MailEngine:
    """Local-first email client with optional live IMAP/SMTP synchronization."""

    def __init__(self) -> None:
        self.storage = workspace_storage
        self._mail_db_path = "mail/mailbox.json"
        self._messages: List[EmailMessage] = []
        self._load_mailbox()

    def _load_mailbox(self) -> None:
        """Load stored emails from workspace."""
        try:
            content = self.storage.read_file(self._mail_db_path)
            data = json.loads(content)
            self._messages = [EmailMessage.model_validate(m) for m in data]
        except Exception:
            self._messages = []

    def _save_mailbox(self) -> None:
        """Persist mailbox state."""
        dumpable = [m.model_dump(mode="json") for m in self._messages]
        self.storage.write_file(
            rel_path=self._mail_db_path,
            content=json.dumps(dumpable, indent=2),
            file_type="mail",
            change_summary="Mailbox update",
        )

    def compose_draft(self, recipient: str, subject: str, body: str, sender: Optional[str] = None) -> EmailMessage:
        """Create and save a new draft email."""
        msg = EmailMessage(
            sender=sender or settings.email_address or "mitchell@local",
            recipient=recipient,
            subject=subject,
            body_text=body,
            folder="drafts",
        )
        self._messages.append(msg)
        self._save_mailbox()
        logger.info("Email draft composed for '{}'", recipient)
        return msg

    def send_email(self, draft_id_or_msg: str | EmailMessage) -> Dict[str, Any]:
        """Send an email via configured SMTP or record locally as sent."""
        if isinstance(draft_id_or_msg, str):
            msg = next((m for m in self._messages if m.id == draft_id_or_msg), None)
            if not msg:
                return {"status": "error", "message": "Draft not found"}
        else:
            msg = draft_id_or_msg
            self._messages.append(msg)

        # Attempt real SMTP send if credentials present
        if settings.email_smtp_host and settings.email_address and settings.email_password:
            try:
                smtp_msg = MIMEMultipart("alternative")
                smtp_msg["Subject"] = msg.subject
                smtp_msg["From"] = msg.sender
                smtp_msg["To"] = msg.recipient
                smtp_msg.attach(MIMEText(msg.body_text, "plain"))
                if msg.body_html:
                    smtp_msg.attach(MIMEText(msg.body_html, "html"))

                with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port, timeout=15) as server:
                    server.starttls()
                    server.login(settings.email_address, settings.email_password)
                    server.sendmail(msg.sender, [msg.recipient], smtp_msg.as_string())
                logger.info("Email successfully dispatched via SMTP to '{}'", msg.recipient)
            except Exception as e:
                logger.warning("SMTP dispatch failed, keeping in sent folder: {}", e)

        msg.folder = "sent"
        msg.date = datetime.now(timezone.utc)
        self._save_mailbox()

        event_log.log_event(
            "email_sent",
            source="mail_engine",
            data={"recipient": msg.recipient, "subject": msg.subject},
        )
        return {"status": "success", "message_id": msg.id}

    def fetch_remote_emails(self, limit: int = 10) -> List[EmailMessage]:
        """Fetch latest emails via IMAP if configured."""
        if not (settings.email_imap_host and settings.email_address and settings.email_password):
            return []

        fetched = []
        try:
            mail = imaplib.IMAP4_SSL(settings.email_imap_host, settings.email_imap_port)
            mail.login(settings.email_address, settings.email_password)
            mail.select("inbox")

            _, data = mail.search(None, "ALL")
            mail_ids = data[0].split()
            latest_ids = mail_ids[-limit:] if len(mail_ids) > limit else mail_ids

            for num in reversed(latest_ids):
                _, msg_data = mail.fetch(num, "(RFC822)")
                raw_email = msg_data[0][1]
                msg_obj = email.message_from_bytes(raw_email)

                # Decode subject
                subject, encoding = decode_header(msg_obj.get("Subject", "No Subject"))[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors="replace")

                sender = msg_obj.get("From", "")
                body = ""
                if msg_obj.is_multipart():
                    for part in msg_obj.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="replace")
                            break
                else:
                    body = msg_obj.get_payload(decode=True).decode(errors="replace")

                # Deduplicate by subject and sender
                existing = any(m.subject == subject and m.sender == sender for m in self._messages)
                if not existing:
                    em = EmailMessage(
                        sender=sender,
                        recipient=settings.email_address,
                        subject=subject,
                        body_text=body,
                        folder="inbox",
                    )
                    self._messages.append(em)
                    fetched.append(em)

            mail.close()
            mail.logout()
            if fetched:
                self._save_mailbox()
        except Exception as e:
            logger.warning("IMAP fetch failed: {}", e)

        return fetched

    def list_emails(self, folder: str = "inbox", search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List emails in a folder with optional text filtering."""
        filtered = [m for m in self._messages if m.folder == folder]
        if search_query:
            q = search_query.lower()
            filtered = [
                m for m in filtered
                if q in m.subject.lower() or q in m.body_text.lower() or q in m.sender.lower()
            ]

        return [m.model_dump(mode="json") for m in sorted(filtered, key=lambda x: x.date, reverse=True)]


mail_engine = MailEngine()

__all__ = ["EmailMessage", "MailEngine", "mail_engine"]
