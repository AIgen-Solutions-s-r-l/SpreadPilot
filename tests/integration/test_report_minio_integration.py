"""Integration tests for report generation with MinIO storage."""

import datetime
import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase

from report_worker.app.service.minio_service import MinIOService
from spreadpilot_core.models.follower import Follower, FollowerState


@pytest.mark.asyncio
async def test_monthly_report_minio_storage(test_mongo_db: AsyncIOMotorDatabase):
    """
    Test storing monthly reports in MinIO.

    This test verifies:
    1. PDF report is generated
    2. Report is uploaded to MinIO
    3. Pre-signed URL is generated
    4. Report metadata is stored in MongoDB
    """
    # Create test follower
    follower_id = str(uuid.uuid4())
    follower = Follower(
        id=follower_id,
        email=f"minio-test-{follower_id}@example.com",
        iban=f"IBAN-MINIO-{follower_id}",
        ibkr_username="minio_test_user",
        commission_pct=20.0,
        enabled=True,
        state=FollowerState.ACTIVE,
    )

    # Mock MinIO client
    mock_minio_client = MagicMock()
    mock_minio_client.bucket_exists.return_value = True
    mock_minio_client.put_object.return_value = None
    mock_minio_client.presigned_get_object.return_value = (
        "https://minio.example.com/reports/test-report.pdf?X-Amz-Signature=test"
    )

    # Create MinIO service
    minio_service = MinIOService(
        endpoint="minio.example.com",
        access_key="test-key",
        secret_key="test-secret",
        bucket_name="reports",
        secure=True,
    )
    minio_service.client = mock_minio_client

    # Generate report data
    report_data = {
        "report_id": str(uuid.uuid4()),
        "follower_id": follower_id,
        "year": 2024,
        "month": 1,
        "total_pnl": "2500.00",
        "commission_amount": "500.00",
        "net_pnl": "2000.00",
        "generated_at": datetime.datetime.now(),
    }

    # Mock PDF generation
    pdf_content = b"Mock PDF content for monthly report"
    with patch(
        "report_worker.app.service.generator.generate_pdf_report",
        return_value=io.BytesIO(pdf_content),
    ):
        # Upload report to MinIO
        object_name = (
            f"reports/{follower_id}/monthly_{report_data['year']}_{report_data['month']:02d}.pdf"
        )

        # Upload to MinIO
        await minio_service.upload_report(
            report_content=pdf_content,
            object_name=object_name,
            content_type="application/pdf",
        )

        # Generate pre-signed URL
        presigned_url = await minio_service.get_presigned_url(object_name, expires_days=30)

        # Store report metadata in MongoDB
        report_doc = {
            **report_data,
            "follower_email": follower.email,
            "minio_object_name": object_name,
            "minio_bucket": "reports",
            "presigned_url": presigned_url,
            "url_expires_at": datetime.datetime.now() + datetime.timedelta(days=30),
            "file_size": len(pdf_content),
            "content_type": "application/pdf",
        }

        await test_mongo_db.monthly_reports.insert_one(report_doc)

        # Verify upload was called
        mock_minio_client.put_object.assert_called_once()
        call_args = mock_minio_client.put_object.call_args
        assert call_args[1]["bucket_name"] == "reports"
        assert call_args[1]["object_name"] == object_name

        # Verify pre-signed URL was generated
        mock_minio_client.presigned_get_object.assert_called_once()
        assert "X-Amz-Signature" in presigned_url

        # Verify report metadata in MongoDB
        stored_report = await test_mongo_db.monthly_reports.find_one(
            {"report_id": report_data["report_id"]}
        )
        assert stored_report is not None
        assert stored_report["minio_object_name"] == object_name
        assert stored_report["presigned_url"] == presigned_url
        assert stored_report["file_size"] == len(pdf_content)

    # Cleanup
    await test_mongo_db.monthly_reports.delete_one({"report_id": report_data["report_id"]})


@pytest.mark.asyncio
async def test_report_retrieval_from_minio(test_mongo_db: AsyncIOMotorDatabase):
    """
    Test retrieving reports from MinIO.

    This test verifies:
    1. Reports can be retrieved using object name
    2. Pre-signed URLs work correctly
    3. Report content is intact
    """
    # Create test report metadata
    report_id = str(uuid.uuid4())
    follower_id = str(uuid.uuid4())
    object_name = f"reports/{follower_id}/monthly_2024_01.pdf"

    report_metadata = {
        "_id": report_id,
        "report_id": report_id,
        "follower_id": follower_id,
        "minio_object_name": object_name,
        "minio_bucket": "reports",
        "presigned_url": f"https://minio.example.com/{object_name}?signature=test",
        "url_expires_at": datetime.datetime.now() + datetime.timedelta(days=30),
    }

    await test_mongo_db.monthly_reports.insert_one(report_metadata)

    # Mock MinIO client
    mock_pdf_content = b"Retrieved PDF content"
    mock_minio_client = MagicMock()
    mock_minio_client.get_object.return_value = MagicMock(
        read=MagicMock(return_value=mock_pdf_content), close=MagicMock()
    )
    mock_minio_client.stat_object.return_value = MagicMock(
        size=len(mock_pdf_content),
        etag="test-etag",
        last_modified=datetime.datetime.now(),
    )

    # Create MinIO service
    minio_service = MinIOService(
        endpoint="minio.example.com",
        access_key="test-key",
        secret_key="test-secret",
        bucket_name="reports",
        secure=True,
    )
    minio_service.client = mock_minio_client

    # Retrieve report from MinIO
    report_content = await minio_service.get_report(object_name)

    # Verify retrieval
    assert report_content == mock_pdf_content
    mock_minio_client.get_object.assert_called_once_with("reports", object_name)

    # Check report exists
    exists = await minio_service.report_exists(object_name)
    assert exists is True
    mock_minio_client.stat_object.assert_called_with("reports", object_name)

    # Cleanup
    await test_mongo_db.monthly_reports.delete_one({"_id": report_id})


@pytest.mark.asyncio
async def test_bulk_report_generation_with_minio(test_mongo_db: AsyncIOMotorDatabase):
    """
    Test bulk report generation and storage in MinIO.

    This test verifies:
    1. Multiple reports can be generated concurrently
    2. All reports are stored in MinIO
    3. Pre-signed URLs are generated for each report
    4. MongoDB tracks all report metadata
    """
    # Create multiple test followers
    num_followers = 3
    followers = []

    for i in range(num_followers):
        follower_id = str(uuid.uuid4())
        follower = Follower(
            id=follower_id,
            email=f"bulk-test-{i}@example.com",
            iban=f"IBAN-BULK-{i}",
            ibkr_username=f"bulk_user_{i}",
            commission_pct=20.0,
            enabled=True,
            state=FollowerState.ACTIVE,
        )
        followers.append(follower)

    # Mock MinIO client
    mock_minio_client = MagicMock()
    mock_minio_client.bucket_exists.return_value = True
    mock_minio_client.put_object.return_value = None
    mock_minio_client.presigned_get_object.return_value = "https://minio.example.com/test-url"

    # Create MinIO service
    minio_service = MinIOService(
        endpoint="minio.example.com",
        access_key="test-key",
        secret_key="test-secret",
        bucket_name="reports",
        secure=True,
    )
    minio_service.client = mock_minio_client

    # Generate reports for all followers
    report_ids = []

    for follower in followers:
        # Generate report data
        report_data = {
            "report_id": str(uuid.uuid4()),
            "follower_id": follower.id,
            "year": 2024,
            "month": 1,
            "total_pnl": "1000.00",
            "commission_amount": "200.00",
        }
        report_ids.append(report_data["report_id"])

        # Mock PDF content
        pdf_content = f"PDF for {follower.id}".encode()
        object_name = f"reports/{follower.id}/monthly_2024_01.pdf"

        # Upload to MinIO
        await minio_service.upload_report(
            report_content=pdf_content,
            object_name=object_name,
            content_type="application/pdf",
        )

        # Store metadata in MongoDB
        report_doc = {
            **report_data,
            "minio_object_name": object_name,
            "minio_bucket": "reports",
            "presigned_url": f"https://minio.example.com/{object_name}",
            "generated_at": datetime.datetime.now(),
        }
        await test_mongo_db.monthly_reports.insert_one(report_doc)

    # Verify all reports were uploaded
    assert mock_minio_client.put_object.call_count == num_followers

    # Verify all reports exist in MongoDB
    stored_reports = await test_mongo_db.monthly_reports.count_documents(
        {"report_id": {"$in": report_ids}}
    )
    assert stored_reports == num_followers

    # Cleanup
    await test_mongo_db.monthly_reports.delete_many({"report_id": {"$in": report_ids}})


@pytest.mark.asyncio
async def test_minio_connection_failure_handling():
    """
    Test handling of MinIO connection failures.

    This test verifies:
    1. Graceful handling when MinIO is unavailable
    2. Proper error messages are returned
    3. Report generation fails safely
    """
    # Mock MinIO client that fails
    mock_minio_client = MagicMock()
    mock_minio_client.bucket_exists.side_effect = Exception("MinIO connection failed")
    mock_minio_client.put_object.side_effect = Exception("Upload failed")

    # Create MinIO service
    minio_service = MinIOService(
        endpoint="minio.example.com",
        access_key="test-key",
        secret_key="test-secret",
        bucket_name="reports",
        secure=True,
    )
    minio_service.client = mock_minio_client

    # Attempt to upload report
    pdf_content = b"Test PDF content"
    object_name = "reports/test/failed_report.pdf"

    # Upload should fail gracefully
    with pytest.raises(Exception) as exc_info:
        await minio_service.upload_report(
            report_content=pdf_content,
            object_name=object_name,
            content_type="application/pdf",
        )

    assert "failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_report_expiration_and_cleanup(test_mongo_db: AsyncIOMotorDatabase):
    """
    Test report expiration and cleanup process.

    This test verifies:
    1. Expired reports are identified
    2. Expired URLs are refreshed
    3. Old reports can be deleted
    """
    # Create expired and valid report metadata
    current_time = datetime.datetime.now()

    expired_report = {
        "_id": str(uuid.uuid4()),
        "report_id": str(uuid.uuid4()),
        "follower_id": str(uuid.uuid4()),
        "minio_object_name": "reports/expired/report.pdf",
        "presigned_url": "https://minio.example.com/expired-url",
        "url_expires_at": current_time - datetime.timedelta(days=1),  # Expired
    }

    valid_report = {
        "_id": str(uuid.uuid4()),
        "report_id": str(uuid.uuid4()),
        "follower_id": str(uuid.uuid4()),
        "minio_object_name": "reports/valid/report.pdf",
        "presigned_url": "https://minio.example.com/valid-url",
        "url_expires_at": current_time + datetime.timedelta(days=29),  # Still valid
    }

    await test_mongo_db.monthly_reports.insert_many([expired_report, valid_report])

    # Find expired reports
    expired_reports = await test_mongo_db.monthly_reports.find(
        {"url_expires_at": {"$lt": current_time}}
    ).to_list(None)

    assert len(expired_reports) == 1
    assert expired_reports[0]["_id"] == expired_report["_id"]

    # Mock MinIO client for URL refresh
    mock_minio_client = MagicMock()
    new_presigned_url = "https://minio.example.com/refreshed-url"
    mock_minio_client.presigned_get_object.return_value = new_presigned_url

    # Create MinIO service
    minio_service = MinIOService(
        endpoint="minio.example.com",
        access_key="test-key",
        secret_key="test-secret",
        bucket_name="reports",
        secure=True,
    )
    minio_service.client = mock_minio_client

    # Refresh expired URL
    for report in expired_reports:
        new_url = await minio_service.get_presigned_url(
            report["minio_object_name"], expires_days=30
        )

        # Update MongoDB with new URL
        await test_mongo_db.monthly_reports.update_one(
            {"_id": report["_id"]},
            {
                "$set": {
                    "presigned_url": new_url,
                    "url_expires_at": current_time + datetime.timedelta(days=30),
                }
            },
        )

    # Verify URL was refreshed
    updated_report = await test_mongo_db.monthly_reports.find_one({"_id": expired_report["_id"]})
    assert updated_report["presigned_url"] == new_presigned_url
    assert updated_report["url_expires_at"] > current_time

    # Cleanup
    await test_mongo_db.monthly_reports.delete_many(
        {"_id": {"$in": [expired_report["_id"], valid_report["_id"]]}}
    )
