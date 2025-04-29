import os
from typing import List, Optional

from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower
from spreadpilot_core.utils import email as email_utils

from .. import config

logger = get_logger(__name__)

def send_report_email(
    follower: Follower,
    report_period: str,
    pdf_path: Optional[str],
    excel_path: Optional[str]
) -> bool:
    """
    Sends the generated report(s) via email to the follower, CC'ing the admin.

    Args:
        follower: The Follower object.
        report_period: The reporting period string (e.g., "YYYY-MM").
        pdf_path: Path to the generated PDF report (if available).
        excel_path: Path to the generated Excel report (if available).

    Returns:
        True if the email was sent successfully (or if no email needed), False otherwise.
    """
    if not follower.email:
        logger.warning(f"Follower {follower.id} has no email address. Skipping report notification.")
        return True # Not an error, just nothing to send

    if not pdf_path and not excel_path:
        logger.warning(f"No report files generated for follower {follower.id} for period {report_period}. Skipping email.")
        return True # Nothing to attach

    subject = f"SpreadPilot Monthly Report - {report_period} - {follower.name or follower.id}"
    body = f"""
Dear {follower.name or 'Follower'},

Please find attached your SpreadPilot performance report for the period {report_period}.

The report is provided in both PDF and Excel formats (if generated successfully).

If you have any questions, please contact the administrator.

Best regards,
The SpreadPilot Team
    """
    sender = config.REPORT_SENDER_EMAIL
    recipient = follower.email
    cc_recipients = [config.ADMIN_EMAIL] if config.ADMIN_EMAIL else []
    attachments = [path for path in [pdf_path, excel_path] if path and os.path.exists(path)]

    if not attachments:
         logger.warning(f"Report files not found at expected paths for follower {follower.id}. PDF: {pdf_path}, Excel: {excel_path}. Skipping email.")
         return True # Or False depending on desired behaviour

    logger.info(f"Sending report email for period {report_period} to {recipient} (CC: {cc_recipients}) for follower {follower.id}...")

    try:
        # Assuming email_utils.send_email exists and handles attachments
        email_utils.send_email(
            subject=subject,
            body=body,
            sender=sender,
            recipients=[recipient], # send_email might expect a list
            cc_recipients=cc_recipients,
            attachments=attachments
        )
        logger.info(f"Successfully sent report email to {recipient} for follower {follower.id}.")
        return True
    except Exception as e:
        logger.exception(f"Failed to send report email to {recipient} for follower {follower.id}", exc_info=e)
        return False
    finally:
        # Clean up temporary report files after attempting to send
        for path in attachments:
            try:
                os.remove(path)
                logger.debug(f"Removed temporary report file: {path}")
            except OSError as e:
                logger.warning(f"Failed to remove temporary report file {path}: {e}")


async def send_monthly_report(report: dict, follower: Follower) -> bool:
    """
    Sends a monthly report to a follower.
    
    Args:
        report: The report data dictionary.
        follower: The Follower object.
        
    Returns:
        True if the report was sent successfully, False otherwise.
    """
    from .generator import generate_pdf_report
    
    logger.info(f"Preparing to send monthly report to follower {follower.id}...")
    
    # Extract report data
    year = report["year"]
    month = report["month"]
    total_pnl = report["total_pnl"]
    commission_amount = report["commission_amount"]
    
    # Format period string
    report_period = f"{year}-{month:02d}"
    
    # Generate PDF report
    pdf_content = generate_pdf_report(
        follower=follower,
        report_period=report_period,
        total_pnl=float(total_pnl),
        commission_percentage=follower.commission_pct,
        commission_amount=float(commission_amount)
    )
    
    # Send email with report
    if pdf_content:
        result = send_report_email(
            follower=follower,
            report_period=report_period,
            pdf_path=pdf_content,
            excel_path=None  # Excel report not implemented yet
        )
        return result
    else:
        logger.error(f"Failed to generate PDF report for follower {follower.id}")
        return False