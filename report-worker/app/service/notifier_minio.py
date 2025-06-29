"""Enhanced notifier with MinIO integration for report delivery."""

import os
from typing import Dict, Optional, Tuple

from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower
from spreadpilot_core.utils.email import send_email

from .. import config
from .minio_service import minio_service

logger = get_logger(__name__)


def send_report_email_with_minio(
    follower: Follower,
    report_period: str,
    pdf_path: str,
    excel_path: str
) -> Tuple[bool, Dict[str, str]]:
    """
    Sends a report email to a follower with MinIO links or attachments.
    
    If MinIO is configured, uploads files to MinIO and includes download links.
    Otherwise, falls back to email attachments.
    
    Args:
        follower: The follower to send the report to
        report_period: The period the report covers (e.g., "2025-05")
        pdf_path: Path to the PDF report file
        excel_path: Path to the Excel report file
        
    Returns:
        Tuple of (success, report_info) where report_info contains:
        - pdf_url: MinIO URL for PDF (if uploaded)
        - excel_url: MinIO URL for Excel (if uploaded)
        - email_sent: Whether email was sent
    """
    logger.info(f"Sending report email to follower {follower.id} for period {report_period}")
    
    report_info = {
        'pdf_url': None,
        'excel_url': None,
        'email_sent': False
    }
    
    # Check if files exist
    if not pdf_path or not os.path.exists(pdf_path):
        logger.error(f"PDF report file not found: {pdf_path}")
        return False, report_info
        
    if not excel_path or not os.path.exists(excel_path):
        logger.error(f"Excel report file not found: {excel_path}")
        return False, report_info
    
    # Check if follower has an email
    if not hasattr(follower, 'email') or not follower.email:
        logger.error(f"Follower {follower.id} has no email address")
        return False, report_info
    
    # Upload to MinIO if configured
    pdf_url = None
    excel_url = None
    
    if minio_service.is_configured():
        logger.info("MinIO configured, uploading reports")
        
        # Upload PDF
        pdf_key, pdf_url = minio_service.upload_report_with_url(
            pdf_path,
            follower.id,
            report_period,
            'pdf'
        )
        if pdf_url:
            report_info['pdf_url'] = pdf_url
            logger.info(f"PDF uploaded to MinIO: {pdf_key}")
        
        # Upload Excel
        excel_key, excel_url = minio_service.upload_report_with_url(
            excel_path,
            follower.id,
            report_period,
            'xlsx'
        )
        if excel_url:
            report_info['excel_url'] = excel_url
            logger.info(f"Excel uploaded to MinIO: {excel_key}")
    
    try:
        # Prepare email subject
        subject = f"SpreadPilot Monthly Report - {report_period}"
        
        # Prepare email body based on whether MinIO upload succeeded
        if pdf_url and excel_url:
            # MinIO upload successful - send links
            body = f"""
            <html>
            <body>
                <p>Dear {follower.name if hasattr(follower, 'name') else 'Valued Client'},</p>
                
                <p>Your monthly report for {report_period} is ready.</p>
                
                <p>You can download your reports using the links below (valid for 30 days):</p>
                
                <ul>
                    <li><a href="{pdf_url}">Download PDF Report</a></li>
                    <li><a href="{excel_url}">Download Excel Report</a></li>
                </ul>
                
                <p>The report includes your performance summary and commission details.</p>
                
                <p>If you have any questions, please don't hesitate to contact us.</p>
                
                <p>Best regards,<br>
                SpreadPilot Team</p>
            </body>
            </html>
            """
            # No attachments when using MinIO links
            attachments = []
        else:
            # MinIO not configured or upload failed - use attachments
            logger.info("Using email attachments (MinIO not available)")
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
                {"path": excel_path, "filename": f"SpreadPilot_Report_{report_period}.xlsx"}
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
            attachments=attachments
        )
        
        if result:
            logger.info(f"Report email sent successfully to {follower.email}")
            report_info['email_sent'] = True
            return True, report_info
        else:
            logger.error(f"Failed to send report email to {follower.email}")
            return False, report_info
            
    except Exception as e:
        logger.exception(f"Error sending report email to follower {follower.id}", exc_info=e)
        return False, report_info