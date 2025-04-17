"""PDF report generation utilities for SpreadPilot."""

import datetime
import os
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)

from ..logging import get_logger
from ..models import Follower
from .time import format_ny_time

logger = get_logger(__name__)


def generate_pdf_report(
    output_path: str,
    follower: Follower,
    month: int,
    year: int,
    pnl_total: float,
    commission_amount: float,
    daily_pnl: Dict[str, float],
    logo_path: Optional[str] = None,
) -> str:
    """Generate PDF report for a follower.

    Args:
        output_path: Output directory path
        follower: Follower model
        month: Report month (1-12)
        year: Report year
        pnl_total: Total P&L for the month
        commission_amount: Commission amount
        daily_pnl: Dict mapping dates (YYYYMMDD) to daily P&L
        logo_path: Path to logo image (optional)

    Returns:
        Path to generated PDF file
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Generate filename
        filename = f"spreadpilot-report-{year}-{month:02d}-{follower.id}.pdf"
        filepath = os.path.join(output_path, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        heading_style = styles["Heading1"]
        normal_style = styles["Normal"]
        
        # Create custom styles
        table_title_style = ParagraphStyle(
            "TableTitle",
            parent=styles["Heading2"],
            spaceAfter=12,
        )
        
        # Create content elements
        elements = []
        
        # Add logo if provided
        if logo_path and os.path.exists(logo_path):
            img = Image(logo_path, width=200, height=50)
            elements.append(img)
            elements.append(Spacer(1, 12))
        
        # Add title
        month_name = datetime.date(year, month, 1).strftime("%B")
        title = Paragraph(f"SpreadPilot Monthly Report - {month_name} {year}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 24))
        
        # Add follower information
        elements.append(Paragraph("Follower Information", heading_style))
        elements.append(Spacer(1, 12))
        
        follower_data = [
            ["ID", follower.id],
            ["Email", follower.email],
            ["IBAN", follower.iban],
            ["Commission Rate", f"{follower.commission_pct}%"],
        ]
        
        follower_table = Table(follower_data, colWidths=[150, 300])
        follower_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.black),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (1, 0), (-1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(follower_table)
        elements.append(Spacer(1, 24))
        
        # Add summary
        elements.append(Paragraph("Monthly Summary", heading_style))
        elements.append(Spacer(1, 12))
        
        summary_data = [
            ["Total P&L", f"${pnl_total:.2f}"],
            ["Commission Rate", f"{follower.commission_pct}%"],
            ["Commission Amount", f"${commission_amount:.2f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[150, 300])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.black),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (1, 0), (-1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 24))
        
        # Add daily P&L table
        elements.append(Paragraph("Daily P&L", heading_style))
        elements.append(Spacer(1, 12))
        
        # Sort dates
        sorted_dates = sorted(daily_pnl.keys())
        
        # Create table data
        daily_data = [["Date", "P&L"]]
        for date in sorted_dates:
            # Format date from YYYYMMDD to YYYY-MM-DD
            formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            daily_data.append([formatted_date, f"${daily_pnl[date]:.2f}"])
        
        daily_table = Table(daily_data, colWidths=[150, 300])
        daily_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ]))
        elements.append(daily_table)
        elements.append(Spacer(1, 24))
        
        # Add footer
        footer_text = (
            f"This report was generated on {format_ny_time()} by SpreadPilot. "
            f"For any questions, please contact capital@tradeautomation.it."
        )
        footer = Paragraph(footer_text, normal_style)
        elements.append(footer)
        
        # Build PDF
        doc.build(elements)
        
        logger.info(
            "Generated PDF report",
            follower_id=follower.id,
            month=month,
            year=year,
            filepath=filepath,
        )
        
        return filepath
    except Exception as e:
        logger.error(
            f"Error generating PDF report: {e}",
            follower_id=follower.id,
            month=month,
            year=year,
        )
        raise