import io
import os
import re
import uuid
import logging
from pathlib import Path
from typing import BinaryIO, Optional, Tuple
from fastapi import HTTPException, status
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger("interviewos.storage")

# Security Constraints
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


def sanitize_filename(filename: str) -> str:
    """Sanitizes filename against path traversal and dangerous characters."""
    base_name = os.path.basename(filename)
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", base_name)
    return sanitized or "document"


class StorageService:
    """Object storage service interfacing with MinIO/S3 with local disk fallback."""

    def __init__(self):
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self.endpoint_url = (
            f"https://{settings.MINIO_ENDPOINT}"
            if settings.MINIO_USE_SSL
            else f"http://{settings.MINIO_ENDPOINT}"
        )
        try:
            self.fallback_dir = Path("./storage_scratch")
            self.fallback_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Fallback to writable /tmp directory in serverless/container environments
            self.fallback_dir = Path("/tmp/storage_scratch")
            self.fallback_dir.mkdir(parents=True, exist_ok=True)
        self._s3_client = None
        self._checked_s3 = False
        self._s3_available = False

    def _get_s3_client(self):
        if not self._checked_s3:
            self._checked_s3 = True
            try:
                client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=settings.MINIO_ACCESS_KEY,
                    aws_secret_access_key=settings.MINIO_SECRET_KEY,
                    config=Config(
                        signature_version="s3v4",
                        connect_timeout=0.2,
                        read_timeout=0.2,
                        retries={"max_attempts": 0},
                    ),
                    region_name="us-east-1",
                )
                try:
                    client.head_bucket(Bucket=self.bucket_name)
                    self._s3_client = client
                    self._s3_available = True
                except ClientError:
                    try:
                        client.create_bucket(Bucket=self.bucket_name)
                        self._s3_client = client
                        self._s3_available = True
                    except Exception:
                        self._s3_available = False
            except Exception:
                self._s3_available = False

        return self._s3_client if self._s3_available else None

    def validate_file(self, file_bytes: bytes, file_name: str, content_type: str) -> str:
        """Validates file size, extension, and MIME type."""
        # 1. Size check
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB",
            )

        # 2. Extension check
        ext = Path(file_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # 3. MIME type check
        normalized_mime = content_type.lower().split(";")[0].strip()
        if normalized_mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported MIME type '{normalized_mime}'. Allowed: PDF, DOCX, DOC",
            )

        return ext

    def upload_document(
        self,
        file_bytes: bytes,
        file_name: str,
        content_type: str,
        candidate_id: uuid.UUID,
    ) -> str:
        """Uploads file to MinIO (or fallback) and returns unique storage_key."""
        ext = self.validate_file(file_bytes, file_name, content_type)
        safe_name = sanitize_filename(file_name)
        storage_key = f"candidates/{candidate_id}/{uuid.uuid4().hex}-{safe_name}"

        client = self._get_s3_client()
        if client:
            try:
                client.put_object(
                    Bucket=self.bucket_name,
                    Key=storage_key,
                    Body=file_bytes,
                    ContentType=content_type,
                )
                logger.info("Uploaded document to MinIO: %s", storage_key)
                return storage_key
            except Exception as e:
                logger.warning("MinIO upload failed: %s. Writing to local fallback.", e)

        # Local fallback
        dest_path = self.fallback_dir / storage_key.replace("/", "_")
        dest_path.write_bytes(file_bytes)
        logger.info("Uploaded document to local storage fallback: %s", dest_path)
        return storage_key

    def get_document_bytes(self, storage_key: str) -> Optional[bytes]:
        """Retrieves file bytes from MinIO or fallback storage."""
        client = self._get_s3_client()
        if client:
            try:
                response = client.get_object(Bucket=self.bucket_name, Key=storage_key)
                return response["Body"].read()
            except Exception as e:
                logger.warning("MinIO get_object failed: %s. Checking local fallback.", e)

        # Local fallback
        dest_path = self.fallback_dir / storage_key.replace("/", "_")
        if dest_path.exists():
            return dest_path.read_bytes()
        return None

    def delete_document(self, storage_key: str) -> bool:
        """Deletes object from MinIO and fallback storage."""
        client = self._get_s3_client()
        deleted = False
        if client:
            try:
                client.delete_object(Bucket=self.bucket_name, Key=storage_key)
                deleted = True
            except Exception as e:
                logger.warning("MinIO delete failed: %s", e)

        dest_path = self.fallback_dir / storage_key.replace("/", "_")
        if dest_path.exists():
            dest_path.unlink()
            deleted = True

        return deleted


storage_service = StorageService()
