from datetime import timedelta
from typing import Optional
import logging
from minio import Minio
from minio.error import S3Error
from minio.deleteobjects import DeleteObject

from ..config import settings

logger = logging.getLogger(__name__)

_minio_client: Optional[Minio] = None


def get_minio_client() -> Minio:
    """Get or create MinIO client instance"""
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        # Ensure bucket exists
        try:
            if not _minio_client.bucket_exists(settings.minio_bucket):
                _minio_client.make_bucket(settings.minio_bucket)
                logger.info(f"Created MinIO bucket: {settings.minio_bucket}")
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}", exc_info=True)
    return _minio_client


def generate_presigned_upload_url(object_name: str, expires: timedelta = timedelta(hours=1)) -> str:
    # Note: In dev mode, uploads should use proxy endpoint instead of presigned URL
    # This function is kept for production mode only
    client = get_minio_client()
    url = client.presigned_put_object(
        settings.minio_bucket,
        object_name,
        expires=expires
    )
    return url


def generate_presigned_download_url(object_name: str, expires: timedelta = timedelta(hours=1)) -> str:
    # Note: In dev mode, downloads should use proxy endpoint instead of presigned URL
    # This function is kept for production mode only
    client = get_minio_client()
    url = client.presigned_get_object(
        settings.minio_bucket,
        object_name,
        expires=expires
    )
    return url


async def upload_file_to_minio(file_data: bytes, object_name: str, content_type: str = "application/octet-stream") -> bool:
    try:
        client = get_minio_client()
        from io import BytesIO
        client.put_object(
            settings.minio_bucket,
            object_name,
            BytesIO(file_data),
            length=len(file_data),
            content_type=content_type
        )
        return True
    except S3Error as e:
        logger.error(f"Error uploading to MinIO: {e}", exc_info=True)
        return False


async def delete_file_from_minio(object_name: str) -> bool:
    try:
        client = get_minio_client()
        client.remove_object(settings.minio_bucket, object_name)
        return True
    except S3Error as e:
        logger.error(f"Error deleting from MinIO: {e}", exc_info=True)
        return False


def get_object_url(object_name: str) -> str:
    """Get object URL (for internal use, not presigned)"""
    protocol = "https" if settings.minio_secure else "http"
    return f"{protocol}://{settings.minio_endpoint}/{settings.minio_bucket}/{object_name}"


async def get_file_bytes_from_minio(object_name: str) -> Optional[bytes]:
    """Get file bytes from MinIO for processing"""
    try:
        client = get_minio_client()
        response = client.get_object(settings.minio_bucket, object_name)
        file_bytes = response.read()
        response.close()
        response.release_conn()
        return file_bytes
    except S3Error as e:
        logger.error(f"Error getting file from MinIO: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error reading file from MinIO: {e}", exc_info=True)
        return None


def get_proxy_download_url(object_name: str, doc_id: int, request_base_url, token: Optional[str] = None) -> str:
    """Generate proxy download URL for dev mode (for thumbnails, etc.)."""
    base_url = str(request_base_url).rstrip('/')
    # URL encode object_name for path safety
    from urllib.parse import quote
    encoded_name = quote(object_name, safe='')
    url = f"{base_url}/api/v1/documents/{doc_id}/preview/{encoded_name}"
    # Add token to query parameter for browser direct access (img/iframe tags)
    if token:
        from urllib.parse import urlencode
        url = f"{url}?{urlencode({'token': token})}"
    return url


def get_proxy_download_url_for_doc(object_name: str, doc_id: int, request_base_url, token: Optional[str] = None) -> str:
    """Generate proxy download URL for document file in dev mode (for download)."""
    base_url = str(request_base_url).rstrip('/')
    url = f"{base_url}/api/v1/documents/{doc_id}/download"
    # Add token to query parameter for browser direct access
    if token:
        from urllib.parse import urlencode
        url = f"{url}?{urlencode({'token': token})}"
    return url


def get_proxy_preview_url_for_doc(doc_id: int, request_base_url, token: Optional[str] = None, version_id: Optional[int] = None) -> str:
    """Generate proxy preview URL for document file in dev mode (for inline preview in browser)."""
    base_url = str(request_base_url).rstrip('/')
    url = f"{base_url}/api/v1/documents/{doc_id}/preview"
    params = {}
    if token:
        params['token'] = token
    if version_id:
        params['version_id'] = version_id
    if params:
        from urllib.parse import urlencode
        url = f"{url}?{urlencode(params)}"
    return url

