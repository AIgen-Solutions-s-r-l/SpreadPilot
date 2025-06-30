"""Enhanced report generator for SpreadPilot with GCS integration.

This module provides comprehensive report generation capabilities including:
- PDF reports using ReportLab with daily P&L tables
- Excel reports using pandas and openpyxl
- GCS bucket storage for generated files
- Signed URL generation for secure access
- Integration with P&L data and commission calculations
"""

import datetime
import os
import tempfile

from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

from spreadpilot_core.db.postgresql import get_async_db_session
from spreadpilot_core.logging import get_logger
from spreadpilot_core.models import Follower
from spreadpilot_core.models.pnl import CommissionMonthly, PnLDaily
from spreadpilot_core.utils.excel import generate_excel_report
from spreadpilot_core.utils.pdf import generate_pdf_report

from ..config import Settings

logger = get_logger(__name__)


class ReportGenerator:
    """Enhanced report generator with GCS integration."""

    def __init__(self, settings: Settings):
        """Initialize the report generator.

        Args:
            settings: Application settings containing GCS configuration
        """
        self.settings = settings
        self.gcs_client = None
        self.bucket = None

        # Initialize GCS client if bucket name is configured
        if hasattr(settings, "gcs_bucket_name") and settings.gcs_bucket_name:
            try:
                self.gcs_client = storage.Client()
                self.bucket = self.gcs_client.bucket(settings.gcs_bucket_name)
                logger.info(f"Initialized GCS client for bucket: {settings.gcs_bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                self.gcs_client = None
                self.bucket = None

    async def get_daily_pnl_data(self, follower_id: str, year: int, month: int) -> dict[str, float]:
        """Retrieve daily P&L data for a follower and month.

        Args:
            follower_id: The follower ID
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            Dictionary mapping dates (YYYYMMDD) to daily P&L values
        """
        daily_pnl = {}

        try:
            async with get_async_db_session() as session:
                # Query daily P&L records for the specified month
                from sqlalchemy import extract, select

                stmt = (
                    select(PnLDaily)
                    .where(
                        PnLDaily.follower_id == follower_id,
                        extract("year", PnLDaily.date) == year,
                        extract("month", PnLDaily.date) == month,
                    )
                    .order_by(PnLDaily.date)
                )

                result = await session.execute(stmt)
                pnl_records = result.scalars().all()

                # Convert to dictionary format expected by report utilities
                for record in pnl_records:
                    date_key = record.date.strftime("%Y%m%d")
                    daily_pnl[date_key] = float(record.pnl_total)

                logger.info(
                    f"Retrieved {len(daily_pnl)} daily P&L records for follower {follower_id} "
                    f"for {year}-{month:02d}"
                )

        except Exception as e:
            logger.error(
                f"Error retrieving daily P&L data for follower {follower_id}: {e}",
                exc_info=True,
            )
            # Return empty dict on error

        return daily_pnl

    async def get_commission_data(
        self, follower_id: str, year: int, month: int
    ) -> tuple[float, float]:
        """Retrieve commission data for a follower and month.

        Args:
            follower_id: The follower ID
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            Tuple of (total_pnl, commission_amount)
        """
        try:
            async with get_async_db_session() as session:
                from sqlalchemy import select

                stmt = select(CommissionMonthly).where(
                    CommissionMonthly.follower_id == follower_id,
                    CommissionMonthly.year == year,
                    CommissionMonthly.month == month,
                )

                result = await session.execute(stmt)
                commission_record = result.scalar_one_or_none()

                if commission_record:
                    total_pnl = float(commission_record.pnl_total)
                    commission_amount = float(commission_record.commission_amount)
                    logger.info(
                        f"Retrieved commission data for follower {follower_id} "
                        f"for {year}-{month:02d}: P&L=${total_pnl:.2f}, "
                        f"Commission=${commission_amount:.2f}"
                    )
                    return total_pnl, commission_amount
                else:
                    logger.warning(
                        f"No commission record found for follower {follower_id} "
                        f"for {year}-{month:02d}"
                    )
                    return 0.0, 0.0

        except Exception as e:
            logger.error(
                f"Error retrieving commission data for follower {follower_id}: {e}",
                exc_info=True,
            )
            return 0.0, 0.0

    async def generate_pdf_report(
        self, follower: Follower, year: int, month: int, logo_path: str | None = None
    ) -> str:
        """Generate PDF report for a follower.

        Args:
            follower: Follower model
            year: Report year
            month: Report month (1-12)
            logo_path: Optional path to logo image

        Returns:
            Local path to generated PDF file
        """
        try:
            # Get P&L and commission data
            daily_pnl = await self.get_daily_pnl_data(follower.id, year, month)
            total_pnl, commission_amount = await self.get_commission_data(follower.id, year, month)

            # Create temporary directory for report generation
            temp_dir = tempfile.mkdtemp(prefix=f"report_pdf_{follower.id}_{year}_{month:02d}_")

            # Generate PDF using core utility
            pdf_path = generate_pdf_report(
                output_path=temp_dir,
                follower=follower,
                month=month,
                year=year,
                pnl_total=total_pnl,
                commission_amount=commission_amount,
                daily_pnl=daily_pnl,
                logo_path=logo_path,
            )

            logger.info(
                f"Generated PDF report for follower {follower.id} "
                f"for {year}-{month:02d}: {pdf_path}"
            )

            return pdf_path

        except Exception as e:
            logger.error(
                f"Error generating PDF report for follower {follower.id}: {e}",
                exc_info=True,
            )
            raise

    async def generate_excel_report(self, follower: Follower, year: int, month: int) -> str:
        """Generate Excel report for a follower.

        Args:
            follower: Follower model
            year: Report year
            month: Report month (1-12)

        Returns:
            Local path to generated Excel file
        """
        try:
            # Get P&L and commission data
            daily_pnl = await self.get_daily_pnl_data(follower.id, year, month)
            total_pnl, commission_amount = await self.get_commission_data(follower.id, year, month)

            # Create temporary directory for report generation
            temp_dir = tempfile.mkdtemp(prefix=f"report_excel_{follower.id}_{year}_{month:02d}_")

            # Generate Excel using core utility
            excel_path = generate_excel_report(
                output_path=temp_dir,
                follower=follower,
                month=month,
                year=year,
                pnl_total=total_pnl,
                commission_amount=commission_amount,
                daily_pnl=daily_pnl,
            )

            logger.info(
                f"Generated Excel report for follower {follower.id} "
                f"for {year}-{month:02d}: {excel_path}"
            )

            return excel_path

        except Exception as e:
            logger.error(
                f"Error generating Excel report for follower {follower.id}: {e}",
                exc_info=True,
            )
            raise

    def upload_to_gcs(self, local_path: str, gcs_path: str) -> bool:
        """Upload file to GCS bucket.

        Args:
            local_path: Path to local file
            gcs_path: Destination path in GCS bucket

        Returns:
            True if upload successful, False otherwise
        """
        if not self.bucket:
            logger.error("GCS bucket not configured, cannot upload file")
            return False

        try:
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_filename(local_path)

            logger.info(f"Uploaded file to GCS: {gcs_path}")
            return True

        except GoogleCloudError as e:
            logger.error(f"Error uploading file to GCS: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading file to GCS: {e}")
            return False

    def generate_signed_url(self, gcs_path: str, expiration_hours: int = 24) -> str | None:
        """Generate signed URL for GCS object.

        Args:
            gcs_path: Path to object in GCS bucket
            expiration_hours: Hours until URL expires

        Returns:
            Signed URL or None if error
        """
        if not self.bucket:
            logger.error("GCS bucket not configured, cannot generate signed URL")
            return None

        try:
            blob = self.bucket.blob(gcs_path)

            # Generate signed URL with expiration
            expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=expiration_hours)
            url = blob.generate_signed_url(expiration=expiration, method="GET")

            logger.info(f"Generated signed URL for {gcs_path}, expires in {expiration_hours}h")
            return url

        except GoogleCloudError as e:
            logger.error(f"Error generating signed URL for {gcs_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating signed URL for {gcs_path}: {e}")
            return None

    async def generate_and_store_reports(
        self,
        follower: Follower,
        year: int,
        month: int,
        formats: list[str] | None = None,
        logo_path: str | None = None,
        expiration_hours: int = 24,
    ) -> dict[str, str | None]:
        """Generate reports in specified formats, store in GCS, and return signed URLs.

        Args:
            follower: Follower model
            year: Report year
            month: Report month (1-12)
            formats: List of formats to generate ('pdf', 'excel'). Defaults to both.
            logo_path: Optional path to logo image (PDF only)
            expiration_hours: Hours until signed URLs expire

        Returns:
            Dictionary mapping format to signed URL (or None if error)
        """
        if formats is None:
            formats = ["pdf", "excel"]

        results = {}

        for format_type in formats:
            try:
                if format_type == "pdf":
                    # Generate PDF report
                    local_path = await self.generate_pdf_report(follower, year, month, logo_path)
                    file_extension = "pdf"

                elif format_type == "excel":
                    # Generate Excel report
                    local_path = await self.generate_excel_report(follower, year, month)
                    file_extension = "xlsx"

                else:
                    logger.warning(f"Unsupported format: {format_type}")
                    results[format_type] = None
                    continue

                # Generate GCS path
                gcs_path = (
                    f"reports/{year}/{month:02d}/"
                    f"spreadpilot-report-{year}-{month:02d}-{follower.id}.{file_extension}"
                )

                # Upload to GCS
                if self.upload_to_gcs(local_path, gcs_path):
                    # Generate signed URL
                    signed_url = self.generate_signed_url(gcs_path, expiration_hours)
                    results[format_type] = signed_url
                else:
                    results[format_type] = None

                # Clean up local file
                try:
                    os.remove(local_path)
                    # Also remove temp directory if empty
                    temp_dir = os.path.dirname(local_path)
                    if not os.listdir(temp_dir):
                        os.rmdir(temp_dir)
                except OSError as e:
                    logger.warning(f"Failed to clean up local file {local_path}: {e}")

            except Exception as e:
                logger.error(
                    f"Error generating {format_type} report for follower {follower.id}: {e}",
                    exc_info=True,
                )
                results[format_type] = None

        logger.info(
            f"Generated reports for follower {follower.id} for {year}-{month:02d}: "
            f"{len([url for url in results.values() if url])} successful, "
            f"{len([url for url in results.values() if not url])} failed"
        )

        return results


# Convenience functions for backward compatibility and ease of use


async def generate_follower_reports(
    follower: Follower,
    year: int,
    month: int,
    settings: Settings,
    formats: list[str] | None = None,
    logo_path: str | None = None,
    expiration_hours: int = 24,
) -> dict[str, str | None]:
    """Generate and store reports for a follower.

    This is a convenience function that creates a ReportGenerator instance
    and generates reports in the specified formats.

    Args:
        follower: Follower model
        year: Report year
        month: Report month (1-12)
        settings: Application settings
        formats: List of formats to generate ('pdf', 'excel'). Defaults to both.
        logo_path: Optional path to logo image (PDF only)
        expiration_hours: Hours until signed URLs expire

    Returns:
        Dictionary mapping format to signed URL (or None if error)
    """
    generator = ReportGenerator(settings)
    return await generator.generate_and_store_reports(
        follower=follower,
        year=year,
        month=month,
        formats=formats,
        logo_path=logo_path,
        expiration_hours=expiration_hours,
    )
