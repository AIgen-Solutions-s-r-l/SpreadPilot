"""Email sending utilities for SpreadPilot."""

import asyncio
import datetime
import os
import smtplib
import urllib.parse
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
import sendgrid
from sendgrid.helpers.mail import (Attachment, Disposition, Email, FileContent,
                                   FileName, FileType, Mail)

try:
    from ..dry_run import dry_run, dry_run_async
except ImportError:
    # Fallback if dry_run not available
    def dry_run(operation_type: str, return_value=None, log_args: bool = True):
        def decorator(func):
            return func

        return decorator

    def dry_run_async(operation_type: str, return_value=None, log_args: bool = True):
        def decorator(func):
            return func

        return decorator


from ..logging import get_logger

logger = get_logger(__name__)


class EmailSender:
    """Email sender using SendGrid."""

    def __init__(self, api_key: str, from_email: str, from_name: str = "SpreadPilot"):
        """Initialize the email sender.

        Args:
            api_key: SendGrid API key
            from_email: From email address
            from_name: From name
        """
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.client = sendgrid.SendGridAPIClient(api_key=api_key)

        logger.info(
            "Initialized email sender",
            from_email=from_email,
            from_name=from_name,
        )

    @dry_run("email", return_value=True, log_args=False)
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        cc_emails: list[str] | None = None,
        bcc_emails: list[str] | None = None,
        attachments: list[str] | None = None,
    ) -> bool:
        """Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content
            cc_emails: CC recipients (optional)
            bcc_emails: BCC recipients (optional)
            attachments: List of file paths to attach (optional)

        Returns:
            True if email was sent successfully, False otherwise

        Note:
            When dry-run mode is enabled, this method will log the email
            but not actually send it. Returns True in dry-run mode.
        """
        try:
            # Create message
            from_email = Email(self.from_email, self.from_name)
            to_email = Email(to_email)

            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
            )

            # Add CC recipients
            if cc_emails:
                for cc_email in cc_emails:
                    message.add_cc(Email(cc_email))

            # Add BCC recipients
            if bcc_emails:
                for bcc_email in bcc_emails:
                    message.add_bcc(Email(bcc_email))

            # Add attachments
            if attachments:
                for attachment_path in attachments:
                    if not os.path.exists(attachment_path):
                        logger.warning(
                            f"Attachment file not found: {attachment_path}",
                            to_email=to_email,
                            subject=subject,
                        )
                        continue

                    # Get file name and extension
                    file_name = os.path.basename(attachment_path)
                    _, file_extension = os.path.splitext(file_name)

                    # Determine MIME type
                    mime_type = "application/octet-stream"
                    if file_extension.lower() == ".pdf":
                        mime_type = "application/pdf"
                    elif file_extension.lower() in [".xlsx", ".xls"]:
                        mime_type = (
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    # Read file content
                    with open(attachment_path, "rb") as f:
                        file_content = f.read()

                    # Create attachment
                    encoded_file = FileContent(file_content)
                    attachment_obj = Attachment()
                    attachment_obj.file_content = encoded_file
                    attachment_obj.file_name = FileName(file_name)
                    attachment_obj.file_type = FileType(mime_type)
                    attachment_obj.disposition = Disposition("attachment")

                    # Add attachment to message
                    message.add_attachment(attachment_obj)

            # Send email
            response = self.client.send(message)

            # Check response
            if response.status_code in [200, 201, 202]:
                logger.info(
                    "Email sent successfully",
                    to_email=to_email,
                    subject=subject,
                    status_code=response.status_code,
                )
                return True
            else:
                logger.error(
                    "Failed to send email",
                    to_email=to_email,
                    subject=subject,
                    status_code=response.status_code,
                    response_body=response.body,
                )
                return False
        except Exception as e:
            logger.error(
                f"Error sending email: {e}",
                to_email=to_email,
                subject=subject,
            )
            return False


class SMTPEmailSender:
    """Email sender using SMTP."""

    def __init__(
        self,
        smtp_uri: str = None,
        smtp_host: str = None,
        smtp_port: int = 587,
        smtp_user: str = None,
        smtp_password: str = None,
        smtp_tls: bool = True,
        from_email: str = None,
        from_name: str = "SpreadPilot",
    ):
        """Initialize the SMTP email sender.

        Args:
            smtp_uri: SMTP URI (e.g., smtp://user:pass@host:port)
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            smtp_tls: Enable TLS
            from_email: From email address
            from_name: From name
        """
        if smtp_uri:
            # Parse SMTP URI
            parsed = urllib.parse.urlparse(smtp_uri)
            self.smtp_host = parsed.hostname
            self.smtp_port = parsed.port or 587
            self.smtp_user = parsed.username
            self.smtp_password = parsed.password
            self.smtp_tls = parsed.scheme == "smtps" or smtp_tls
        else:
            self.smtp_host = smtp_host
            self.smtp_port = smtp_port
            self.smtp_user = smtp_user
            self.smtp_password = smtp_password
            self.smtp_tls = smtp_tls

        self.from_email = from_email
        self.from_name = from_name

        logger.info(
            "Initialized SMTP email sender",
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
            from_email=from_email,
            from_name=from_name,
        )

    @dry_run_async("email", return_value=True, log_args=False)
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        cc_emails: list[str] | None = None,
        bcc_emails: list[str] | None = None,
        attachments: list[dict] | None = None,
    ) -> bool:
        """Send an email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content
            cc_emails: CC recipients (optional)
            bcc_emails: BCC recipients (optional)
            attachments: List of attachments with 'path' and 'filename' keys (optional)

        Returns:
            True if email was sent successfully, False otherwise

        Note:
            When dry-run mode is enabled, this method will log the email
            but not actually send it. Returns True in dry-run mode.
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Add attachments
            if attachments:
                for attachment in attachments:
                    file_path = attachment.get("path")
                    filename = attachment.get("filename")

                    if not file_path or not os.path.exists(file_path):
                        logger.warning(f"Attachment file not found: {file_path}")
                        continue

                    with open(file_path, "rb") as f:
                        file_content = f.read()

                    # Determine MIME type
                    if filename.lower().endswith(".pdf"):
                        mime_type = "application/pdf"
                    elif filename.lower().endswith((".xlsx", ".xls")):
                        mime_type = (
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        mime_type = "application/octet-stream"

                    attachment_part = MIMEApplication(file_content, mime_type)
                    attachment_part.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=filename or os.path.basename(file_path),
                    )
                    msg.attach(attachment_part)

            # Prepare recipient list
            recipients = [to_email]
            if cc_emails:
                recipients.extend(cc_emails)
            if bcc_emails:
                recipients.extend(bcc_emails)

            # Send email using aiosmtplib
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=self.smtp_tls,
            )

            logger.info(
                "Email sent successfully via SMTP",
                to_email=to_email,
                subject=subject,
                smtp_host=self.smtp_host,
            )
            return True

        except Exception as e:
            logger.error(
                f"Error sending email via SMTP: {e}",
                to_email=to_email,
                subject=subject,
                smtp_host=self.smtp_host,
            )
            return False


@dry_run("email", return_value=True, log_args=False)
def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    cc_recipients: list[str] | None = None,
    bcc_recipients: list[str] | None = None,
    attachments: list[dict] | None = None,
    from_email: str | None = None,
    from_name: str | None = None,
) -> bool:
    """Send an email using SMTP or SendGrid.

    Automatically chooses SMTP if SMTP_URI is configured, otherwise falls back to SendGrid.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content
        cc_recipients: CC recipients (optional)
        bcc_recipients: BCC recipients (optional)
        attachments: List of attachment dicts with 'path' and 'filename' keys (optional)
        from_email: From email address (optional)
        from_name: From name (optional)

    Returns:
        True if email was sent successfully, False otherwise

    Note:
        When dry-run mode is enabled, this function will log the email
        but not actually send it. Returns True in dry-run mode.
    """
    # Get from email and name from environment if not provided
    if not from_email:
        from_email = os.environ.get("REPORT_SENDER_EMAIL") or os.environ.get(
            "SENDGRID_FROM_EMAIL", "capital@tradeautomation.it"
        )

    if not from_name:
        from_name = os.environ.get("SENDGRID_FROM_NAME", "SpreadPilot")

    # Check if SMTP is configured
    smtp_uri = os.environ.get("SMTP_URI")
    smtp_host = os.environ.get("SMTP_HOST")

    if smtp_uri or smtp_host:
        # Use SMTP
        logger.info("Using SMTP for email delivery")

        smtp_sender = SMTPEmailSender(
            smtp_uri=smtp_uri,
            smtp_host=smtp_host,
            smtp_port=int(os.environ.get("SMTP_PORT", 587)),
            smtp_user=os.environ.get("SMTP_USER"),
            smtp_password=os.environ.get("SMTP_PASSWORD"),
            smtp_tls=os.environ.get("SMTP_TLS", "true").lower() == "true",
            from_email=from_email,
            from_name=from_name,
        )

        # Convert attachment format for SMTP
        smtp_attachments = []
        if attachments:
            for attachment in attachments:
                if isinstance(attachment, dict):
                    smtp_attachments.append(attachment)
                else:
                    # Convert string path to dict format
                    smtp_attachments.append(
                        {"path": attachment, "filename": os.path.basename(attachment)}
                    )

        # Run async function in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            smtp_sender.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                cc_emails=cc_recipients,
                bcc_emails=bcc_recipients,
                attachments=smtp_attachments,
            )
        )

    else:
        # Use SendGrid
        logger.info("Using SendGrid for email delivery")

        api_key = os.environ.get("SENDGRID_API_KEY")
        if not api_key:
            logger.error("Neither SMTP nor SendGrid is properly configured")
            return False

        # Create email sender
        sender = EmailSender(api_key, from_email, from_name)

        # Convert attachment format for SendGrid
        sendgrid_attachments = []
        if attachments:
            for attachment in attachments:
                if isinstance(attachment, dict):
                    sendgrid_attachments.append(attachment.get("path"))
                else:
                    sendgrid_attachments.append(attachment)

        # Send email
        return sender.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            cc_emails=cc_recipients,
            bcc_emails=bcc_recipients,
            attachments=sendgrid_attachments,
        )


def send_monthly_report_email(
    to_email: str,
    follower_id: str,
    month: int,
    year: int,
    pdf_path: str,
    excel_path: str,
    admin_email: str | None = None,
    api_key: str | None = None,
    from_email: str | None = None,
) -> bool:
    """Send monthly report email to a follower.

    Args:
        to_email: Follower email address
        follower_id: Follower ID
        month: Report month (1-12)
        year: Report year
        pdf_path: Path to PDF report
        excel_path: Path to Excel report
        admin_email: Admin email address for CC (optional)
        api_key: SendGrid API key (optional)
        from_email: From email address (optional)

    Returns:
        True if email was sent successfully, False otherwise
    """
    # Generate month name
    month_name = datetime.date(year, month, 1).strftime("%B")

    # Create subject
    subject = f"SpreadPilot Monthly Report - {month_name} {year}"

    # Create HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; }}
            p {{ margin-bottom: 15px; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>SpreadPilot Monthly Report - {month_name} {year}</h1>
            
            <p>Dear Trader,</p>
            
            <p>Please find attached your monthly trading report for {month_name} {year}.</p>
            
            <p>The report includes your trading performance, P&L, and commission details for the month.</p>
            
            <p>If you have any questions or need further information, please don't hesitate to contact us.</p>
            
            <p>Best regards,<br>
            The SpreadPilot Team</p>
            
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>&copy; {year} SpreadPilot. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Create CC list
    cc_emails = []
    if admin_email:
        cc_emails.append(admin_email)

    # Send email
    return send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        cc_emails=cc_emails,
        attachments=[pdf_path, excel_path],
        api_key=api_key,
        from_email=from_email,
    )
