import os

from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower
from spreadpilot_core.utils.email import send_email

from .. import config

logger = get_logger(__name__)


def send_report_email(
    follower: Follower, report_period: str, pdf_path: str, excel_path: str
) -> bool:
    """
    Sends a report email to a follower with PDF and Excel attachments.

    Args:
        follower: The follower to send the report to
        report_period: The period the report covers (e.g., "2025-05")
        pdf_path: Path to the PDF report file
        excel_path: Path to the Excel report file

    Returns:
        True if the email was sent successfully, False otherwise
    """
    logger.info(f"Sending report email to follower {follower.id} for period {report_period}")

    # Check if files exist
    if not pdf_path or not os.path.exists(pdf_path):
        logger.error(f"PDF report file not found: {pdf_path}")
        return False

    if not excel_path or not os.path.exists(excel_path):
        logger.error(f"Excel report file not found: {excel_path}")
        return False

    # Check if follower has an email
    if not hasattr(follower, "email") or not follower.email:
        logger.error(f"Follower {follower.id} has no email address")
        return False

    try:
        # Prepare email subject and body
        subject = f"SpreadPilot Monthly Report - {report_period}"
        body = f"""
        <html>
        <body>
            <p>Dear {follower.name if hasattr(follower, 'name') else 'Valued Client'},</p>
            
            <p>Please find attached your monthly report for {report_period}.</p>
            
            <p>The report includes your performance summary and commission details.</p>
            
            <p>If you have any questions, please don't hesitate to contact us.</p>
            
            <p>Best regards,<br>
            SpreadPilot Team</p>
        </body>
        </html>
        """

        # Prepare attachments
        attachments = [
            {"path": pdf_path, "filename": f"SpreadPilot_Report_{report_period}.pdf"},
            {
                "path": excel_path,
                "filename": f"SpreadPilot_Report_{report_period}.xlsx",
            },
        ]

        # Determine CC recipients
        cc_recipients = []
        if config.ADMIN_EMAIL:
            cc_recipients.append(config.ADMIN_EMAIL)

        # Send email using core utility
        result = send_email(
            from_email=config.REPORT_SENDER_EMAIL,
            to_email=follower.email,
            subject=subject,
            html_content=body,
            cc_recipients=cc_recipients,
            attachments=attachments,
        )

        if result:
            logger.info(f"Report email sent successfully to {follower.email}")
            return True
        else:
            logger.error(f"Failed to send report email to {follower.email}")
            return False

    except Exception as e:
        logger.exception(f"Error sending report email to follower {follower.id}", exc_info=e)
        return False
