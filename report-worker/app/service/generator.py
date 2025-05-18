import os
import datetime
import tempfile
from typing import Dict, Any, Optional

from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower
from spreadpilot_core.utils.excel import generate_excel_report
from spreadpilot_core.utils.pdf import generate_pdf_report

from .. import config

logger = get_logger(__name__)

def generate_pdf_report(
    follower: Follower,
    report_period: str,
    total_pnl: float,
    commission_percentage: float,
    commission_amount: float
) -> str:
    """
    Generates a PDF report for a follower.
    
    Args:
        follower: The follower to generate the report for
        report_period: The period the report covers (e.g., "2025-05")
        total_pnl: The total P&L for the period
        commission_percentage: The commission percentage
        commission_amount: The calculated commission amount
        
    Returns:
        Path to the generated PDF file
    """
    logger.info(f"Generating PDF report for follower {follower.id} for period {report_period}")
    
    try:
        # Create a temporary directory for the report
        report_dir = tempfile.mkdtemp(prefix=f"report_{follower.id}_{report_period}_")
        
        # Parse the report period (expected format: "YYYY-MM")
        year, month = map(int, report_period.split('-'))
        
        # Create a dummy daily PnL for now (this should be replaced with actual data)
        # Format: Dict[str, float] where key is date in YYYYMMDD format
        daily_pnl = {
            f"{year}{month:02d}01": total_pnl / 20,  # Just a placeholder
            f"{year}{month:02d}15": total_pnl / 20 * 19,  # Just a placeholder
        }
        
        # Generate PDF file path
        pdf_path = os.path.join(report_dir, f"{follower.id}_{report_period}_report.pdf")
        
        # Generate PDF using core utility with the expected parameters
        filepath = generate_pdf_report(
            output_path=report_dir,
            follower=follower,
            month=month,
            year=year,
            pnl_total=total_pnl,
            commission_amount=commission_amount,
            daily_pnl=daily_pnl
        )
        
        logger.info(f"PDF report generated successfully: {filepath}")
        return filepath
    except Exception as e:
        logger.exception(f"Error generating PDF report for follower {follower.id}", exc_info=e)
        # Return a placeholder path in case of error
        return ""

def generate_excel_report(
    follower: Follower,
    report_period: str,
    total_pnl: float,
    commission_percentage: float,
    commission_amount: float
) -> str:
    """
    Generates an Excel report for a follower.
    
    Args:
        follower: The follower to generate the report for
        report_period: The period the report covers (e.g., "2025-05")
        total_pnl: The total P&L for the period
        commission_percentage: The commission percentage
        commission_amount: The calculated commission amount
        
    Returns:
        Path to the generated Excel file
    """
    logger.info(f"Generating Excel report for follower {follower.id} for period {report_period}")
    
    try:
        # Create a temporary directory for the report
        report_dir = tempfile.mkdtemp(prefix=f"report_{follower.id}_{report_period}_")
        
        # Parse the report period (expected format: "YYYY-MM")
        year, month = map(int, report_period.split('-'))
        
        # Create a dummy daily PnL for now (this should be replaced with actual data)
        # Format: Dict[str, float] where key is date in YYYYMMDD format
        daily_pnl = {
            f"{year}{month:02d}01": total_pnl / 20,  # Just a placeholder
            f"{year}{month:02d}15": total_pnl / 20 * 19,  # Just a placeholder
        }
        
        # Generate Excel file path
        excel_path = os.path.join(report_dir, f"{follower.id}_{report_period}_report.xlsx")
        
        # Generate Excel using core utility with the expected parameters
        filepath = generate_excel_report(
            output_path=report_dir,
            follower=follower,
            month=month,
            year=year,
            pnl_total=total_pnl,
            commission_amount=commission_amount,
            daily_pnl=daily_pnl
        )
        
        logger.info(f"Excel report generated successfully: {filepath}")
        return filepath
    except Exception as e:
        logger.exception(f"Error generating Excel report for follower {follower.id}", exc_info=e)
        # Return a placeholder path in case of error
        return ""