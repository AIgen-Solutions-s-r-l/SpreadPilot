"""MinIO/S3 service for uploading and managing report files."""

import os
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from spreadpilot_core.logging.logger import get_logger

from .. import config

logger = get_logger(__name__)


class MinIOService:
    """Service for uploading reports to MinIO/S3 with lifecycle management."""

    def __init__(self):
        """Initialize MinIO service with configuration."""
        self.endpoint_url = config.MINIO_ENDPOINT_URL
        self.access_key = config.MINIO_ACCESS_KEY
        self.secret_key = config.MINIO_SECRET_KEY
        self.bucket_name = config.MINIO_BUCKET_NAME
        self.region = config.MINIO_REGION
        self.secure = config.MINIO_SECURE

        self._s3_client = None

    @property
    def s3_client(self):
        """Lazy-initialize and return S3 client."""
        if self._s3_client is None and self.endpoint_url:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                use_ssl=self.secure,
            )
        return self._s3_client

    def is_configured(self) -> bool:
        """Check if MinIO is properly configured."""
        return bool(self.endpoint_url and self.access_key and self.secret_key and self.bucket_name)

    def upload_report(self, local_file_path: str, object_key: str) -> str | None:
        """
        Upload a report file to MinIO with 180-day lifecycle.

        Args:
            local_file_path: Path to local file to upload
            object_key: S3 object key (path in bucket)

        Returns:
            S3 object key if successful, None otherwise
        """
        if not self.is_configured():
            logger.warning("MinIO not configured, skipping upload")
            return None

        if not os.path.exists(local_file_path):
            logger.error(f"File not found: {local_file_path}")
            return None

        try:
            # Upload file
            with open(local_file_path, "rb") as file:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=file,
                    # Set object to expire after 180 days
                    Expires=datetime.utcnow() + timedelta(days=180),
                )

            logger.info(f"Successfully uploaded {local_file_path} to {object_key}")
            return object_key

        except FileNotFoundError:
            logger.error(f"File not found: {local_file_path}")
        except NoCredentialsError:
            logger.error("MinIO credentials not found")
        except ClientError as e:
            logger.error(f"Failed to upload to MinIO: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error uploading to MinIO: {e}")

        return None

    def generate_presigned_url(self, object_key: str, expiration_days: int = 30) -> str | None:
        """
        Generate a pre-signed URL for downloading a report.

        Args:
            object_key: S3 object key
            expiration_days: Number of days until URL expires (default 30)

        Returns:
            Pre-signed URL if successful, None otherwise
        """
        if not self.is_configured():
            logger.warning("MinIO not configured, cannot generate URL")
            return None

        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expiration_days * 24 * 3600,  # Convert days to seconds
            )

            logger.info(f"Generated pre-signed URL for {object_key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate pre-signed URL: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error generating pre-signed URL: {e}")

        return None

    def upload_report_with_url(
        self, local_file_path: str, follower_id: str, report_period: str, file_type: str
    ) -> tuple[str | None, str | None]:
        """
        Upload report and generate pre-signed URL.

        Args:
            local_file_path: Path to local file
            follower_id: Follower ID for organizing files
            report_period: Report period (e.g., "2025-05")
            file_type: File type (pdf or xlsx)

        Returns:
            Tuple of (object_key, presigned_url) or (None, None) if failed
        """
        # Generate object key with folder structure
        object_key = f"reports/{report_period}/{follower_id}/report_{report_period}.{file_type}"

        # Upload file
        uploaded_key = self.upload_report(local_file_path, object_key)
        if not uploaded_key:
            return None, None

        # Generate pre-signed URL
        presigned_url = self.generate_presigned_url(uploaded_key)

        return uploaded_key, presigned_url


# Create singleton instance
minio_service = MinIOService()
