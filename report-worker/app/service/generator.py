import os
import tempfile
import asyncio
from datetime import date, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase
from spreadpilot_core.db.mongodb import get_mongo_db
from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower
from spreadpilot_core.utils.excel import generate_excel_report
from spreadpilot_core.utils.pdf import generate_pdf_report

logger = get_logger(__name__)


async def _get_daily_pnl_for_month(follower_id: str, year: int, month: int) -> dict[str, float]:
    """
    Fetches daily P&L data for a specific follower and month.
    
    Args:
        follower_id: The follower ID
        year: The year
        month: The month (1-12)
    
    Returns:
        Dict[str, float] where key is date in YYYYMMDD format and value is daily P&L
    """
    try:
        db: AsyncIOMotorDatabase = await get_mongo_db()
        daily_pnl_collection = db["daily_pnl"]
        
        # Calculate date range for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # Query daily P&L data
        daily_pnl = {}
        current_date = start_date
        
        while current_date < end_date:
            date_str = current_date.isoformat()
            
            # Find P&L for this specific date
            pnl_doc = await daily_pnl_collection.find_one({
                "date": date_str,
                "follower_id": follower_id
            })
            
            if pnl_doc:
                # Format as YYYYMMDD
                date_key = current_date.strftime("%Y%m%d")
                daily_pnl[date_key] = float(pnl_doc.get("total_pnl", 0))
            
            current_date += timedelta(days=1)
        
        # If no daily data found, use PostgreSQL pnl_daily table as fallback
        if not daily_pnl:
            logger.info(f"No daily P&L found in MongoDB for {follower_id}, checking PostgreSQL")
            # This could be expanded to query PostgreSQL pnl_daily table
            # For now, return empty dict
            return {}
        
        return daily_pnl
        
    except Exception as e:
        logger.error(f"Error fetching daily P&L: {e}", exc_info=True)
        return {}


async def generate_pdf_report(
    follower: Follower,
    report_period: str,
    total_pnl: float,
    commission_percentage: float,
    commission_amount: float,
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
    logger.info(
        f"Generating PDF report for follower {follower.id} for period {report_period}"
    )

    try:
        # Create a temporary directory for the report
        report_dir = tempfile.mkdtemp(prefix=f"report_{follower.id}_{report_period}_")

        # Parse the report period (expected format: "YYYY-MM")
        year, month = map(int, report_period.split("-"))

        # Get actual daily P&L data from database
        daily_pnl = await _get_daily_pnl_for_month(follower.id, year, month)
        
        # If no daily data available, create a simple breakdown
        if not daily_pnl:
            logger.warning(f"No daily P&L data found for {follower.id}, using simple breakdown")
            # Create a simple daily breakdown based on total
            # Calculate days in month correctly
            if month == 12:
                next_month_date = date(year + 1, 1, 1)
            else:
                next_month_date = date(year, month + 1, 1)
            last_day_of_month = next_month_date - timedelta(days=1)
            days_in_month = last_day_of_month.day
            daily_amount = total_pnl / days_in_month
            daily_pnl = {
                f"{year}{month:02d}{day:02d}": daily_amount 
                for day in range(1, days_in_month + 1)
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
            daily_pnl=daily_pnl,
        )

        logger.info(f"PDF report generated successfully: {filepath}")
        return filepath
    except Exception as e:
        logger.exception(
            f"Error generating PDF report for follower {follower.id}", exc_info=e
        )
        # Return a placeholder path in case of error
        return ""


async def generate_excel_report(
    follower: Follower,
    report_period: str,
    total_pnl: float,
    commission_percentage: float,
    commission_amount: float,
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
    logger.info(
        f"Generating Excel report for follower {follower.id} for period {report_period}"
    )

    try:
        # Create a temporary directory for the report
        report_dir = tempfile.mkdtemp(prefix=f"report_{follower.id}_{report_period}_")

        # Parse the report period (expected format: "YYYY-MM")
        year, month = map(int, report_period.split("-"))

        # Get actual daily P&L data from database
        daily_pnl = await _get_daily_pnl_for_month(follower.id, year, month)
        
        # If no daily data available, create a simple breakdown
        if not daily_pnl:
            logger.warning(f"No daily P&L data found for {follower.id}, using simple breakdown")
            # Create a simple daily breakdown based on total
            # Calculate days in month correctly
            if month == 12:
                next_month_date = date(year + 1, 1, 1)
            else:
                next_month_date = date(year, month + 1, 1)
            last_day_of_month = next_month_date - timedelta(days=1)
            days_in_month = last_day_of_month.day
            daily_amount = total_pnl / days_in_month
            daily_pnl = {
                f"{year}{month:02d}{day:02d}": daily_amount 
                for day in range(1, days_in_month + 1)
            }

        # Generate Excel file path
        excel_path = os.path.join(
            report_dir, f"{follower.id}_{report_period}_report.xlsx"
        )

        # Generate Excel using core utility with the expected parameters
        filepath = generate_excel_report(
            output_path=report_dir,
            follower=follower,
            month=month,
            year=year,
            pnl_total=total_pnl,
            commission_amount=commission_amount,
            daily_pnl=daily_pnl,
        )

        logger.info(f"Excel report generated successfully: {filepath}")
        return filepath
    except Exception as e:
        logger.exception(
            f"Error generating Excel report for follower {follower.id}", exc_info=e
        )
        # Return a placeholder path in case of error
        return ""
