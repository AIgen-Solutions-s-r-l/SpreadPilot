import os
import datetime
from decimal import Decimal
from typing import Dict, Any

from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower
from spreadpilot_core.utils import pdf as pdf_utils
from spreadpilot_core.utils import excel as excel_utils

logger = get_logger(__name__)

# Define a temporary directory for report generation (Cloud Run uses /tmp)
TEMP_REPORT_DIR = "/tmp/spreadpilot_reports"

def _ensure_temp_dir():
    """Ensures the temporary directory for reports exists."""
    os.makedirs(TEMP_REPORT_DIR, exist_ok=True)

def _generate_filename(follower_id: str, period: str, extension: str) -> str:
    """Generates a unique filename for the report."""
    safe_follower_id = "".join(c if c.isalnum() else "_" for c in follower_id)
    return f"SpreadPilot_Report_{safe_follower_id}_{period}.{extension}"

def _prepare_report_data(
    follower: Follower,
    report_period: str, # e.g., "YYYY-MM"
    total_pnl: Decimal,
    commission_percentage: float, # Use float as passed, core utils might expect it
    commission_amount: Decimal
) -> Dict[str, Any]:
    """Prepares the data dictionary for the report utilities."""
    return {
        "follower_name": follower.name or follower.id, # Use name if available
        "follower_email": follower.email,
        "period": report_period,
        "total_pnl": total_pnl, # Pass Decimal, utils should handle formatting
        "commission_percentage": commission_percentage,
        "commission_amount": commission_amount, # Pass Decimal
        "iban": follower.iban or "N/A", # Use IBAN if available
        # Add any other fields required by the core utils if necessary
    }

def generate_pdf_report(
    follower: Follower,
    report_period: str,
    total_pnl: Decimal,
    commission_percentage: float,
    commission_amount: Decimal
) -> str | None:
    """
    Generates a PDF report for the follower.

    Args:
        follower: The Follower object.
        report_period: The reporting period string (e.g., "YYYY-MM").
        total_pnl: Calculated total P&L for the period.
        commission_percentage: Commission percentage applied.
        commission_amount: Calculated commission amount.

    Returns:
        The path to the generated PDF file, or None if generation failed.
    """
    _ensure_temp_dir()
    report_data = _prepare_report_data(
        follower, report_period, total_pnl, commission_percentage, commission_amount
    )
    filename = _generate_filename(follower.id, report_period, "pdf")
    output_path = os.path.join(TEMP_REPORT_DIR, filename)

    logger.info(f"Generating PDF report for follower {follower.id} for period {report_period} at {output_path}...")

    try:
        # Assuming pdf_utils.create_report_pdf exists and takes data dict and path
        pdf_utils.create_report_pdf(report_data, output_path)
        logger.info(f"Successfully generated PDF report: {output_path}")
        return output_path
    except Exception as e:
        logger.exception(f"Failed to generate PDF report for follower {follower.id}", exc_info=e)
        return None


def generate_excel_report(
    follower: Follower,
    report_period: str,
    total_pnl: Decimal,
    commission_percentage: float,
    commission_amount: Decimal
) -> str | None:
    """
    Generates an Excel report for the follower.

    Args:
        follower: The Follower object.
        report_period: The reporting period string (e.g., "YYYY-MM").
        total_pnl: Calculated total P&L for the period.
        commission_percentage: Commission percentage applied.
        commission_amount: Calculated commission amount.

    Returns:
        The path to the generated Excel file, or None if generation failed.
    """
    _ensure_temp_dir()
    report_data = _prepare_report_data(
        follower, report_period, total_pnl, commission_percentage, commission_amount
    )
    filename = _generate_filename(follower.id, report_period, "xlsx")
    output_path = os.path.join(TEMP_REPORT_DIR, filename)

    logger.info(f"Generating Excel report for follower {follower.id} for period {report_period} at {output_path}...")

    try:
        # Assuming excel_utils.create_report_excel exists and takes data dict and path
        excel_utils.create_report_excel(report_data, output_path)
        logger.info(f"Successfully generated Excel report: {output_path}")
        return output_path
    except Exception as e:
        logger.exception(f"Failed to generate Excel report for follower {follower.id}", exc_info=e)
        return None


async def generate_monthly_report(
    year: int,
    month: int,
    follower: Follower,
    db=None
) -> Dict[str, Any]:
    """
    Generates a monthly report for a follower.
    
    Args:
        year: The year for the report.
        month: The month for the report.
        follower: The Follower object.
        db: Optional Firestore client.
        
    Returns:
        A dictionary containing the report data.
    """
    from .pnl import calculate_monthly_pnl, calculate_commission
    
    logger.info(f"Generating monthly report for follower {follower.id} for {year}-{month}...")
    
    # Calculate monthly P&L
    total_pnl = calculate_monthly_pnl(year, month)
    
    # Calculate commission
    commission_amount = calculate_commission(total_pnl, follower)
    
    # Generate report ID
    report_id = f"report-{year}-{month:02d}-{follower.id}"
    
    # Create report data
    report = {
        "report_id": report_id,
        "follower_id": follower.id,
        "year": year,
        "month": month,
        "total_pnl": str(total_pnl),
        "commission_amount": str(commission_amount),
        "net_pnl": str(total_pnl - commission_amount),
        "generated_at": datetime.datetime.now().isoformat(),
    }
    
    # Store report in Firestore if DB client provided
    if db:
        try:
            db.collection("monthly_reports").document(report_id).set({
                "followerId": follower.id,
                "year": year,
                "month": month,
                "totalPnl": str(total_pnl),
                "commissionAmount": str(commission_amount),
                "netPnl": str(total_pnl - commission_amount),
                "generatedAt": datetime.datetime.now(),
            })
            logger.info(f"Stored monthly report {report_id} in Firestore.")
        except Exception as e:
            logger.exception(f"Failed to store monthly report in Firestore", exc_info=e)
    
    return report