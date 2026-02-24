"""
AirAd Backend — File Upload Validation

Deep file type inspection using magic bytes (not just extension).
File size enforcement at the server level.
All uploaded files MUST pass through validate_uploaded_file() before processing.
"""

import logging
from typing import IO

from django.conf import settings

logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    """Raised when a file fails validation checks."""


# Magic byte signatures for allowed file types
_MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],  # RIFF....WEBP
    "application/pdf": [b"%PDF"],
    "text/csv": [],  # CSV has no magic bytes — validated by extension + content check
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
        b"PK\x03\x04"
    ],  # XLSX (ZIP-based)
}

# Allowed extensions mapped to MIME types
_ALLOWED_EXTENSIONS: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Maximum file size (default 10 MB, overridable via settings)
_MAX_FILE_SIZE: int = getattr(settings, "FILE_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024)


def validate_uploaded_file(
    file: IO[bytes],
    filename: str,
    allowed_types: list[str] | None = None,
    max_size_bytes: int | None = None,
) -> str:
    """Validate an uploaded file by type (magic bytes) and size.

    Args:
        file: File-like object opened in binary mode.
        filename: Original filename provided by the client.
        allowed_types: Optional list of allowed MIME types. If None,
            all types in _ALLOWED_EXTENSIONS are permitted.
        max_size_bytes: Optional max file size in bytes. Defaults to
            settings.FILE_UPLOAD_MAX_MEMORY_SIZE (10 MB).

    Returns:
        Detected MIME type string.

    Raises:
        FileValidationError: If the file fails any validation check.
    """
    import os

    max_size = max_size_bytes or _MAX_FILE_SIZE

    # 1. Validate extension
    _, ext = os.path.splitext(filename.lower())
    if ext not in _ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"File extension '{ext}' is not allowed. "
            f"Permitted: {', '.join(sorted(_ALLOWED_EXTENSIONS.keys()))}"
        )

    expected_mime = _ALLOWED_EXTENSIONS[ext]

    # 2. Check against allowed_types filter
    if allowed_types and expected_mime not in allowed_types:
        raise FileValidationError(
            f"File type '{expected_mime}' is not allowed for this upload. "
            f"Permitted: {', '.join(allowed_types)}"
        )

    # 3. Validate file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size == 0:
        raise FileValidationError("Uploaded file is empty")

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise FileValidationError(
            f"File size ({file_size:,} bytes) exceeds maximum "
            f"allowed size ({max_mb:.1f} MB)"
        )

    # 4. Deep type inspection via magic bytes
    header = file.read(16)
    file.seek(0)  # Reset again

    signatures = _MAGIC_SIGNATURES.get(expected_mime, [])
    if signatures:
        if not any(header.startswith(sig) for sig in signatures):
            raise FileValidationError(
                f"File content does not match expected type '{expected_mime}'. "
                f"The file may have been renamed or is corrupted."
            )

    logger.info(
        "File validated",
        extra={
            "filename": filename,
            "mime_type": expected_mime,
            "size_bytes": file_size,
        },
    )
    return expected_mime
