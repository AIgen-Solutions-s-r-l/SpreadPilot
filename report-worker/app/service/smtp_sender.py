"""SMTP email sender using aiosmtplib for report delivery."""

import asyncio
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlparse

import aiosmtplib

from spreadpilot_core.logging.logger import get_logger

logger = get_logger(__name__)


class SMTPEmailSender:
    """Async SMTP email sender for reports."""

    def __init__(self, smtp_uri: str):
        """Initialize SMTP sender with URI.
        
        Args:
            smtp_uri: SMTP URI in format smtp://user:pass@host:port or smtps://...
        """
        self.smtp_uri = smtp_uri
        self._parse_smtp_uri()
        
    def _parse_smtp_uri(self):
        """Parse SMTP URI to extract connection parameters."""
        parsed = urlparse(self.smtp_uri)
        
        self.use_tls = parsed.scheme == "smtps"
        self.hostname = parsed.hostname or "localhost"
        self.port = parsed.port or (465 if self.use_tls else 587)
        self.username = parsed.username
        self.password = parsed.password
        
        logger.info(
            f"Parsed SMTP URI: host={self.hostname}, port={self.port}, "
            f"tls={self.use_tls}, auth={'yes' if self.username else 'no'}"
        )
    
    async def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        html_content: str,
        cc_recipients: list[str] = None,
        attachments: list[dict] = None,
    ) -> bool:
        """Send email with optional attachments.
        
        Args:
            from_email: Sender email address
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            cc_recipients: Optional CC recipients
            attachments: List of attachment dicts with 'path' and 'filename' keys
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("mixed")
            msg["From"] = from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            
            # Add CC recipients
            if cc_recipients:
                msg["Cc"] = ", ".join(cc_recipients)
            
            # Add HTML body
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    await self._add_attachment(msg, attachment)
            
            # Determine all recipients
            all_recipients = [to_email]
            if cc_recipients:
                all_recipients.extend(cc_recipients)
            
            # Send email
            async with aiosmtplib.SMTP(
                hostname=self.hostname,
                port=self.port,
                use_tls=self.use_tls,
                timeout=30,
            ) as smtp:
                # Authenticate if credentials provided
                if self.username and self.password:
                    await smtp.login(self.username, self.password)
                
                # Send message
                await smtp.send_message(msg, sender=from_email, recipients=all_recipients)
                
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False
    
    async def _add_attachment(self, msg: MIMEMultipart, attachment: dict):
        """Add attachment to email message.
        
        Args:
            msg: Email message object
            attachment: Dict with 'path' and 'filename' keys
        """
        file_path = Path(attachment["path"])
        filename = attachment.get("filename", file_path.name)
        
        if not file_path.exists():
            logger.warning(f"Attachment file not found: {file_path}")
            return
        
        # Read file content
        with open(file_path, "rb") as f:
            file_data = f.read()
        
        # Create attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(file_data)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={filename}",
        )
        
        msg.attach(part)
        logger.debug(f"Added attachment: {filename}")