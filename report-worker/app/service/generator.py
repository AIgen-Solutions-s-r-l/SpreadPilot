import os
import datetime
import tempfile
from typing import Dict, Any, Optional

from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower
from spreadpilot_core.utils.excel import create_excel_report
from spreadpilot_core.utils.pdf import create_pdf_report

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
        
        # Prepare report data
        report_data = {
            "follower_id": follower.id,
            "follower_name": follower.name if hasattr(follower, 'name') else "Unknown",
            "follower_email": follower.email,
            "report_period": report_period,
            "total_pnl": total_pnl,
            "commission_percentage": commission_percentage,
            "commission_amount": commission_amount,
            "generation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # Generate PDF file path
        pdf_path = os.path.join(report_dir, f"{follower.id}_{report_period}_report.pdf")
        
        # Generate PDF using core utility
        create_pdf_report(report_data, pdf_path)
        
        logger.info(f"PDF report generated successfully: {pdf_path}")
        return pdf_path
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
        
        # Prepare report data
        report_data = {
            "follower_id": follower.id,
            "follower_name": follower.name if hasattr(follower, 'name') else "Unknown",
            "follower_email": follower.email,
            "report_period": report_period,
            "total_pnl": total_pnl,
            "commission_percentage": commission_percentage,
            "commission_amount": commission_amount,
            "generation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # Generate Excel file path
        excel_path = os.path.join(report_dir, f"{follower.id}_{report_period}_report.xlsx")
        
        # Generate Excel using core utility
        create_excel_report(report_data, excel_path)
        
        logger.info(f"Excel report generated successfully: {excel_path}")
        return excel_path
    except Exception as e:
        logger.exception(f"Error generating Excel report for follower {follower.id}", exc_info=e)
        # Return a placeholder path in case of error
        return ""