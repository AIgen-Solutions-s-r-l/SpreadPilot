"""Email sending utilities for SpreadPilot."""

import os

import sendgrid
from sendgrid.helpers.mail import (
    Attachment,
    Disposition,
    Email,
    FileContent,
    FileName,
    FileType,
    Mail,
)

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
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    cc_emails: list[str] | None = None,
    bcc_emails: list[str] | None = None,
    attachments: list[str] | None = None,
    api_key: str | None = None,
    from_email: str | None = None,
    from_name: str | None = None,
) -> bool:
    """Send an email using SendGrid.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content
        cc_emails: CC recipients (optional)
        bcc_emails: BCC recipients (optional)
        attachments: List of file paths to attach (optional)
        api_key: SendGrid API key (optional, defaults to SENDGRID_API_KEY env var)
        from_email: From email address (optional, defaults to SENDGRID_FROM_EMAIL env var)
        from_name: From name (optional, defaults to "SpreadPilot")

    Returns:
        True if email was sent successfully, False otherwise
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.environ.get("SENDGRID_API_KEY")
        if not api_key:
            logger.error("SendGrid API key not provided")
            return False

    # Get from email from environment if not provided
    if not from_email:
        from_email = os.environ.get("SENDGRID_FROM_EMAIL", "capital@tradeautomation.it")

    # Get from name from environment if not provided
    if not from_name:
        from_name = os.environ.get("SENDGRID_FROM_NAME", "SpreadPilot")

    # Create email sender
    sender = EmailSender(api_key, from_email, from_name)

    # Send email
    return sender.send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        cc_emails=cc_emails,
        bcc_emails=bcc_emails,
        attachments=attachments,
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
