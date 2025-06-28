"""Google Cloud Storage utilities for SpreadPilot."""

import datetime
from typing import Optional

from google.cloud import storage

from ..logging import get_logger

logger = get_logger(__name__)


def get_signed_url(
    bucket_name: str,
    blob_name: str,
    expiration_hours: int = 24,
    method: str = "GET"
) -> str:
    """Generate a signed URL for accessing a GCS object.
    
    Args:
        bucket_name: Name of the GCS bucket
        blob_name: Name of the blob/object in the bucket
        expiration_hours: Number of hours until the URL expires
        method: HTTP method for the signed URL (default: GET)
        
    Returns:
        Signed URL string
    """
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Generate signed URL
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=expiration_hours),
            method=method,
        )
        
        logger.info(
            "Generated signed URL",
            bucket=bucket_name,
            blob=blob_name,
            expiration_hours=expiration_hours,
        )
        
        return url
    except Exception as e:
        logger.error(
            f"Error generating signed URL: {e}",
            bucket=bucket_name,
            blob=blob_name,
        )
        raise


def upload_file_to_gcs(
    local_path: str,
    bucket_name: str,
    blob_name: str,
    content_type: Optional[str] = None
) -> str:
    """Upload a file to Google Cloud Storage.
    
    Args:
        local_path: Path to the local file
        bucket_name: Name of the GCS bucket
        blob_name: Name for the blob/object in the bucket
        content_type: MIME type of the file (optional)
        
    Returns:
        Public URL of the uploaded file
    """
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Set content type if provided
        if content_type:
            blob.content_type = content_type
            
        # Upload file
        blob.upload_from_filename(local_path)
        
        logger.info(
            "Uploaded file to GCS",
            local_path=local_path,
            bucket=bucket_name,
            blob=blob_name,
        )
        
        return f"gs://{bucket_name}/{blob_name}"
    except Exception as e:
        logger.error(
            f"Error uploading file to GCS: {e}",
            local_path=local_path,
            bucket=bucket_name,
            blob=blob_name,
        )
        raise