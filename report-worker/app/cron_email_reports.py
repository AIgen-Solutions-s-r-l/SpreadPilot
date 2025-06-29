"""Cron job for sending commission reports weekly."""

import logging
import os

from service.mailer import create_mailer_from_env
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def send_weekly_commission_reports():
    """Send all pending commission reports.

    This function is designed to be run as a weekly cron job.
    """
    try:
        # Database configuration
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            # Construct from individual components
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "spreadpilot")
            db_user = os.getenv("DB_USER", "postgres")
            db_password = os.getenv("DB_PASSWORD", "")

            db_url = (
                f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            )

        # Create database session
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Create mailer instance
            mailer = create_mailer_from_env()

            # Send pending reports
            logger.info("Starting weekly commission report sending job")
            results = mailer.send_pending_reports(db)

            logger.info(
                f"Commission report sending completed: "
                f"Total={results['total']}, Success={results['success']}, "
                f"Failed={results['failed']}"
            )

            if results["errors"]:
                logger.error(f"Errors encountered: {results['errors']}")

            # Return success if at least some emails were sent
            return results["failed"] == 0 or results["success"] > 0

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to run commission report job: {e!s}")
        return False


if __name__ == "__main__":
    # Run the job
    success = send_weekly_commission_reports()
    exit(0 if success else 1)
