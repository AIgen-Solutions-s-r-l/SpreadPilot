"""Unit tests for MinIO service using moto."""

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import boto3
import pytest
from moto import mock_s3

# Set TESTING environment variable before imports
os.environ["TESTING"] = "true"

from app.service.minio_service import MinIOService


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    with patch("app.service.minio_service.config") as mock_cfg:
        mock_cfg.MINIO_ENDPOINT_URL = "http://localhost:9000"
        mock_cfg.MINIO_ACCESS_KEY = "test-access-key"
        mock_cfg.MINIO_SECRET_KEY = "test-secret-key"
        mock_cfg.MINIO_BUCKET_NAME = "test-bucket"
        mock_cfg.MINIO_REGION = "us-east-1"
        mock_cfg.MINIO_SECURE = False
        yield mock_cfg


@pytest.fixture
def minio_service(mock_config):
    """Create MinIO service instance with mocked config."""
    return MinIOService()


@pytest.fixture
def test_file(tmp_path):
    """Create a test file."""
    test_file = tmp_path / "test_report.pdf"
    test_file.write_text("Test report content")
    return str(test_file)


class TestMinIOService:
    """Test cases for MinIO service."""

    def test_is_configured_true(self, minio_service):
        """Test that is_configured returns True when all config is present."""
        assert minio_service.is_configured() is True

    def test_is_configured_false(self, mock_config):
        """Test that is_configured returns False when config is missing."""
        mock_config.MINIO_ENDPOINT_URL = None
        service = MinIOService()
        assert service.is_configured() is False

    @mock_s3
    def test_upload_report_success(self, minio_service, test_file):
        """Test successful report upload."""
        # Create mock bucket
        s3_client = boto3.client(
            "s3",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
            region_name="us-east-1",
        )
        s3_client.create_bucket(Bucket="test-bucket")

        # Override the service's S3 client
        minio_service._s3_client = s3_client

        # Upload file
        object_key = "reports/2025-05/follower123/report.pdf"
        result = minio_service.upload_report(test_file, object_key)

        assert result == object_key

        # Verify file was uploaded
        response = s3_client.list_objects_v2(Bucket="test-bucket")
        assert response["KeyCount"] == 1
        assert response["Contents"][0]["Key"] == object_key

    def test_upload_report_file_not_found(self, minio_service):
        """Test upload with non-existent file."""
        result = minio_service.upload_report("/nonexistent/file.pdf", "test-key")
        assert result is None

    def test_upload_report_not_configured(self, mock_config):
        """Test upload when MinIO is not configured."""
        mock_config.MINIO_ENDPOINT_URL = None
        service = MinIOService()

        result = service.upload_report("/some/file.pdf", "test-key")
        assert result is None

    @mock_s3
    def test_generate_presigned_url_success(self, minio_service):
        """Test successful pre-signed URL generation."""
        # Create mock bucket and upload file
        s3_client = boto3.client(
            "s3",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
            region_name="us-east-1",
        )
        s3_client.create_bucket(Bucket="test-bucket")
        s3_client.put_object(Bucket="test-bucket", Key="test-object", Body=b"test content")

        # Override the service's S3 client
        minio_service._s3_client = s3_client

        # Generate pre-signed URL
        url = minio_service.generate_presigned_url("test-object", expiration_days=30)

        assert url is not None
        assert "test-bucket" in url
        assert "test-object" in url
        assert "X-Amz-Expires=2592000" in url  # 30 days in seconds

    def test_generate_presigned_url_not_configured(self, mock_config):
        """Test URL generation when MinIO is not configured."""
        mock_config.MINIO_ENDPOINT_URL = None
        service = MinIOService()

        url = service.generate_presigned_url("test-object")
        assert url is None

    @mock_s3
    def test_upload_report_with_url_success(self, minio_service, test_file):
        """Test combined upload and URL generation."""
        # Create mock bucket
        s3_client = boto3.client(
            "s3",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
            region_name="us-east-1",
        )
        s3_client.create_bucket(Bucket="test-bucket")

        # Override the service's S3 client
        minio_service._s3_client = s3_client

        # Upload and get URL
        object_key, url = minio_service.upload_report_with_url(
            test_file,
            follower_id="follower123",
            report_period="2025-05",
            file_type="pdf",
        )

        assert object_key == "reports/2025-05/follower123/report_2025-05.pdf"
        assert url is not None
        assert "test-bucket" in url
        assert "report_2025-05.pdf" in url

    def test_upload_report_with_url_failure(self, minio_service):
        """Test upload_report_with_url with non-existent file."""
        object_key, url = minio_service.upload_report_with_url(
            "/nonexistent/file.pdf",
            follower_id="follower123",
            report_period="2025-05",
            file_type="pdf",
        )

        assert object_key is None
        assert url is None

    @mock_s3
    def test_upload_with_expiration(self, minio_service, test_file):
        """Test that uploaded objects have expiration set."""
        # Create mock bucket
        s3_client = boto3.client(
            "s3",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
            region_name="us-east-1",
        )
        s3_client.create_bucket(Bucket="test-bucket")

        # Override the service's S3 client
        minio_service._s3_client = s3_client

        # Upload file
        object_key = "reports/2025-05/follower123/report.pdf"
        result = minio_service.upload_report(test_file, object_key)

        assert result == object_key

        # Get object metadata
        response = s3_client.head_object(Bucket="test-bucket", Key=object_key)

        # Check that Expires header is set
        assert "Expires" in response
        expires = response["Expires"]

        # Verify expiration is approximately 180 days from now
        expected_expiry = datetime.utcnow() + timedelta(days=180)
        actual_expiry = expires.replace(tzinfo=None)

        # Allow 1 minute tolerance for test execution time
        time_diff = abs((expected_expiry - actual_expiry).total_seconds())
        assert time_diff < 60  # Less than 60 seconds difference
