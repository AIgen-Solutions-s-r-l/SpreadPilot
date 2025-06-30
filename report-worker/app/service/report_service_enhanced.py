"""Enhanced report service with MinIO integration and database updates."""

import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from spreadpilot_core.db.mongodb import get_mongo_db
from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower

from .. import config
from . import generator, pnl
from .notifier_minio import send_report_email_with_minio

logger = get_logger(__name__)


class EnhancedReportService:
    """
    Orchestrates the monthly report generation, MinIO upload, and notification process.
    """

    async def _get_active_followers(self) -> list[Follower]:
        """Fetches all active followers from MongoDB."""
        try:
            db: AsyncIOMotorDatabase = await get_mongo_db()
        except RuntimeError:
            logger.error("MongoDB client not initialized. Cannot fetch followers.")
            return []
        except Exception as e:
            logger.error(f"Failed to get MongoDB database handle: {e}", exc_info=True)
            return []

        followers = []
        try:
            # Assuming the Follower model in core uses 'enabled' field
            followers_collection = db["followers"]
            cursor = followers_collection.find({"enabled": True})

            async for doc in cursor:
                try:
                    # Validate using Pydantic model
                    followers.append(Follower.model_validate(doc))
                except Exception as e:
                    doc_id = doc.get("_id", "UNKNOWN_ID")
                    logger.warning(
                        f"Failed to parse follower data for {doc_id} from MongoDB: {e}",
                        exc_info=True,
                    )

            logger.info(f"Fetched {len(followers)} active followers from MongoDB.")
            return followers
        except Exception as e:
            logger.exception("Error fetching active followers from MongoDB", exc_info=e)
            return []

    def _get_previous_month(self, current_date: datetime.date) -> tuple[int, int]:
        """Calculates the year and month of the previous month."""
        first_day_of_current_month = current_date.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - datetime.timedelta(
            days=1
        )
        return last_day_of_previous_month.year, last_day_of_previous_month.month

    async def _update_report_sent_status(
        self,
        follower_id: str,
        report_period: str,
        email_sent: bool,
        pdf_url: str | None = None,
        excel_url: str | None = None,
    ):
        """Update the database with report_sent status and URLs."""
        try:
            db: AsyncIOMotorDatabase = await get_mongo_db()

            # Create report record
            report_record = {
                "follower_id": follower_id,
                "report_period": report_period,
                "email_sent": email_sent,
                "sent_timestamp": datetime.datetime.utcnow(),
                "pdf_url": pdf_url,
                "excel_url": excel_url,
                "minio_upload": bool(pdf_url or excel_url),
            }

            # Insert or update report_sent collection
            reports_collection = db["report_sent"]
            await reports_collection.update_one(
                {"follower_id": follower_id, "report_period": report_period},
                {"$set": report_record},
                upsert=True,
            )

            logger.info(
                f"Updated report_sent status for follower {follower_id}, period {report_period}"
            )

        except Exception as e:
            logger.error(f"Failed to update report_sent status: {e}", exc_info=True)

    async def process_monthly_reports(self, trigger_date: datetime.date):
        """
        Generates and sends monthly reports for all active followers for the *previous* month.

        Args:
            trigger_date: The date the process was triggered (used to determine the reporting month).
        """
        logger.info(
            f"Starting monthly report process triggered on {trigger_date.isoformat()}..."
        )

        year, month = self._get_previous_month(trigger_date)
        report_period = f"{year:04d}-{month:02d}"
        logger.info(f"Calculating reports for period: {report_period}")

        # --- Step 1: Calculate overall monthly P&L (needed for commission base) ---
        total_monthly_pnl = await pnl.calculate_monthly_pnl(year, month)
        logger.info(f"Total calculated P&L for {report_period}: {total_monthly_pnl}")

        # --- Step 2: Fetch active followers (async) ---
        active_followers = await self._get_active_followers()
        if not active_followers:
            logger.warning("No active followers found. Exiting report process.")
            return

        # --- Step 3: Process each follower ---
        success_count = 0
        failure_count = 0
        minio_upload_count = 0

        for follower in active_followers:
            logger.info(f"Processing report for follower: {follower.id}")
            try:
                # --- 3a: Calculate Commission ---
                commission_pct = (
                    follower.commission_pct
                    if follower.commission_pct is not None
                    else config.DEFAULT_COMMISSION_PERCENTAGE
                )
                commission_amount = pnl.calculate_commission(
                    total_monthly_pnl, follower
                )

                # --- 3b: Generate Reports ---
                pdf_path = await generator.generate_pdf_report(
                    follower=follower,
                    report_period=report_period,
                    total_pnl=total_monthly_pnl,
                    commission_percentage=commission_pct,
                    commission_amount=commission_amount,
                )
                excel_path = await generator.generate_excel_report(
                    follower=follower,
                    report_period=report_period,
                    total_pnl=total_monthly_pnl,
                    commission_percentage=commission_pct,
                    commission_amount=commission_amount,
                )

                # --- 3c: Send Notification with MinIO integration ---
                success, report_info = send_report_email_with_minio(
                    follower, report_period, pdf_path, excel_path
                )

                if success:
                    logger.info(
                        f"Successfully processed and sent report for follower {follower.id}"
                    )
                    success_count += 1

                    # Track MinIO uploads
                    if report_info.get("pdf_url") or report_info.get("excel_url"):
                        minio_upload_count += 1

                    # --- 3d: Update database with report_sent status ---
                    await self._update_report_sent_status(
                        follower_id=follower.id,
                        report_period=report_period,
                        email_sent=report_info.get("email_sent", False),
                        pdf_url=report_info.get("pdf_url"),
                        excel_url=report_info.get("excel_url"),
                    )
                else:
                    logger.error(
                        f"Failed to send report email for follower {follower.id}"
                    )
                    failure_count += 1

                    # Still update database to track failure
                    await self._update_report_sent_status(
                        follower_id=follower.id,
                        report_period=report_period,
                        email_sent=False,
                    )

            except Exception as e:
                logger.exception(
                    f"Unhandled error processing follower {follower.id}", exc_info=e
                )
                failure_count += 1

        logger.info(
            f"Monthly report process finished for period {report_period}. "
            f"Success: {success_count}, Failures: {failure_count}, "
            f"MinIO uploads: {minio_upload_count}"
        )

    async def process_daily_pnl_calculation(self, calculation_date: datetime.date):
        """
        Triggers the calculation and storage of daily P&L.

        Args:
            calculation_date: The date for which to calculate P&L.
        """
        logger.info(
            f"Starting daily P&L calculation for {calculation_date.isoformat()}..."
        )
        daily_pnl = await pnl.calculate_and_store_daily_pnl(calculation_date)
        logger.info(
            f"Daily P&L calculation finished for {calculation_date.isoformat()}. Result: {daily_pnl}"
        )
