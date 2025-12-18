from datetime import timedelta
from typing import Optional
from minio import Minio
from minio.error import S3Error
from minio.deleteobjects import DeleteObject

from ..config import settings

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
                print(f"Created MinIO bucket: {settings.minio_bucket}")
        except S3Error as e:
            print(f"Error creating bucket: {e}")
    return _minio_client


def generate_presigned_upload_url(object_name: str, expires: timedelta = timedelta(hours=1)) -> str:
    client = get_minio_client()
    url = client.presigned_put_object(
        settings.minio_bucket,
        object_name,
        expires=expires
    )
    return url


def generate_presigned_download_url(object_name: str, expires: timedelta = timedelta(hours=1)) -> str:
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
        print(f"Error uploading to MinIO: {e}")
        return False


async def delete_file_from_minio(object_name: str) -> bool:
    try:
        client = get_minio_client()
        client.remove_object(settings.minio_bucket, object_name)
        return True
    except S3Error as e:
        print(f"Error deleting from MinIO: {e}")
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
        print(f"Error getting file from MinIO: {e}")
        return None
    except Exception as e:
        print(f"Error reading file from MinIO: {e}")
        return None

