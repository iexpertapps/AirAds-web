"""
AirAd Backend — S3 Storage Utilities

All file access uses presigned URLs — never public URLs.
S3 keys are stored in the database; presigned URLs are generated on read.
"""

import logging
import uuid
from pathlib import Path
from typing import IO

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when an S3 operation fails."""


def _get_s3_client() -> "boto3.client":
    """Create and return a boto3 S3 client using settings credentials.

    Returns:
        Configured boto3 S3 client.
    """
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def generate_presigned_url(key: str, expiry: int = 3600) -> str:
    """Generate a presigned S3 URL for a given object key.

    Presigned URLs expire after ``expiry`` seconds. Never returns a
    public URL — all access is time-limited and authenticated.

    Args:
        key: S3 object key (e.g. "imports/2024/01/batch_abc123.csv").
        expiry: URL expiry in seconds. Defaults to 3600 (1 hour).
            Use settings.AWS_S3_PRESIGNED_URL_EXPIRY for the global default.

    Returns:
        Presigned HTTPS URL string valid for ``expiry`` seconds.

    Raises:
        StorageError: If the presigned URL cannot be generated.
        ValueError: If key is empty.

    Example:
        >>> url = generate_presigned_url("imports/batch_001.csv", expiry=300)
        >>> url.startswith("https://")
        True
    """
    if not key:
        raise ValueError("S3 key must not be empty")

    if _is_local_dev():
        return f"/media/{key}"

    try:
        client = _get_s3_client()
        url: str = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key,
            },
            ExpiresIn=expiry,
        )
        return url
    except (BotoCoreError, ClientError) as e:
        logger.error(
            "Failed to generate presigned URL",
            extra={"key": key, "error": str(e)},
        )
        raise StorageError(
            f"Failed to generate presigned URL for key '{key}': {e}"
        ) from e


def generate_presigned_upload_url(
    key: str,
    content_type: str = "application/octet-stream",
    expiry: int = 3600,
) -> str:
    """Generate a presigned S3 URL for uploading an object (PUT).

    Used by the vendor portal for logo/cover photo uploads.
    The client PUTs the file directly to S3 using this URL.

    Args:
        key: S3 object key to upload to.
        content_type: MIME type of the file being uploaded.
        expiry: URL expiry in seconds. Defaults to 3600 (1 hour).

    Returns:
        Presigned HTTPS URL string for PUT upload.

    Raises:
        StorageError: If the presigned URL cannot be generated.
        ValueError: If key is empty.
    """
    if not key:
        raise ValueError("S3 key must not be empty")

    try:
        client = _get_s3_client()
        url: str = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expiry,
        )
        return url
    except (BotoCoreError, ClientError) as e:
        logger.error(
            "Failed to generate presigned upload URL",
            extra={"key": key, "error": str(e)},
        )
        raise StorageError(
            f"Failed to generate presigned upload URL for key '{key}': {e}"
        ) from e


def _is_local_dev() -> bool:
    """Return True when AWS credentials are not configured (local dev)."""
    return not getattr(settings, "AWS_ACCESS_KEY_ID", None)


def upload_file_to_s3(file: IO[bytes], prefix: str) -> str:
    """Upload a file-like object to S3 and return its key.

    Generates a UUID-based key under the given prefix to avoid collisions.
    Returns the S3 key only — never a public URL (store the key in the DB
    and call generate_presigned_url() when access is needed).

    Args:
        file: File-like object opened in binary mode (e.g. Django InMemoryUploadedFile).
        prefix: S3 key prefix / folder path (e.g. "imports", "field-photos").
            Must not start or end with "/".

    Returns:
        S3 object key string (e.g. "imports/550e8400-e29b-41d4-a716-446655440000").

    Raises:
        StorageError: If the upload fails.
        ValueError: If prefix is empty.

    Example:
        >>> with open("data.csv", "rb") as f:
        ...     key = upload_file_to_s3(f, "imports")
        >>> key.startswith("imports/")
        True
    """
    if not prefix:
        raise ValueError("S3 prefix must not be empty")

    key = f"{prefix.strip('/')}/{uuid.uuid4()}"

    if _is_local_dev():
        media_root = Path(getattr(settings, "MEDIA_ROOT", "/tmp/airaad-media"))
        dest = media_root / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        with file as f:
            dest.write_bytes(f.read())
        logger.info("[DEV] Saved file locally", extra={"path": str(dest)})
        return key

    try:
        client = _get_s3_client()
        with file as f:
            client.upload_fileobj(
                f,
                settings.AWS_STORAGE_BUCKET_NAME,
                key,
            )
        logger.info("Uploaded file to S3", extra={"key": key})
        return key
    except (BotoCoreError, ClientError) as e:
        logger.error(
            "Failed to upload file to S3",
            extra={"prefix": prefix, "key": key, "error": str(e)},
        )
        raise StorageError(f"Failed to upload file to S3 at key '{key}': {e}") from e
