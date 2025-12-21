"""
Avatar upload service for handling user avatar images
"""
import os
import uuid
from typing import Optional, Tuple
from io import BytesIO
import logging

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ..services.storage import upload_file_to_minio, delete_file_from_minio, get_minio_client
from ..config import settings

logger = logging.getLogger(__name__)

# Allowed image formats
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_SIZE = (200, 200)  # Target size for avatars


def validate_avatar_file(file_data: bytes, filename: str, content_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate avatar file.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    if len(file_data) > MAX_FILE_SIZE:
        return False, f"File size exceeds maximum {MAX_FILE_SIZE / 1024 / 1024}MB"
    
    # Check file extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check MIME type
    if content_type not in ALLOWED_MIME_TYPES:
        return False, f"MIME type not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
    
    # Try to open as image to verify it's a valid image
    if PIL_AVAILABLE:
        try:
            img = Image.open(BytesIO(file_data))
            img.verify()
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
    
    return True, None


def process_avatar_image(file_data: bytes) -> bytes:
    """
    Process and resize avatar image.
    
    Returns:
        Processed image bytes
    """
    if not PIL_AVAILABLE:
        raise ValueError("PIL/Pillow is not available. Cannot process images.")
    
    try:
        img = Image.open(BytesIO(file_data))
        
        # Convert to RGB if necessary (for PNG with transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize maintaining aspect ratio
        img.thumbnail(AVATAR_SIZE, Image.Resampling.LANCZOS)
        
        # Create new image with exact size (centered)
        new_img = Image.new('RGB', AVATAR_SIZE, (255, 255, 255))
        offset = ((AVATAR_SIZE[0] - img.size[0]) // 2, (AVATAR_SIZE[1] - img.size[1]) // 2)
        new_img.paste(img, offset)
        
        # Save to bytes
        output = BytesIO()
        new_img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        return output.read()
    except Exception as e:
        logger.error(f"Error processing avatar image: {e}", exc_info=True)
        raise ValueError(f"Failed to process image: {str(e)}")


async def upload_avatar(user_id: int, file_data: bytes, filename: str, content_type: str, old_avatar_url: Optional[str] = None) -> str:
    """
    Upload avatar for user.
    
    Args:
        user_id: User ID
        file_data: Image file bytes
        filename: Original filename
        content_type: MIME type
        old_avatar_url: Old avatar URL to delete (optional)
    
    Returns:
        Avatar URL
    """
    # Validate file
    is_valid, error = validate_avatar_file(file_data, filename, content_type)
    if not is_valid:
        raise ValueError(error)
    
    # Process image (resize, optimize)
    processed_data = process_avatar_image(file_data)
    
    # Generate object name
    ext = '.jpg'  # Always save as JPEG after processing
    avatar_id = str(uuid.uuid4())
    object_name = f"avatars/{user_id}/{avatar_id}{ext}"
    
    # Upload to MinIO
    success = await upload_file_to_minio(processed_data, object_name, 'image/jpeg')
    if not success:
        raise ValueError("Failed to upload avatar to storage")
    
    # Delete old avatar if exists
    if old_avatar_url:
        try:
            # Extract object name from URL
            # URL format: /api/v1/uploads/{path} or full MinIO URL
            if '/avatars/' in old_avatar_url:
                old_object_name = old_avatar_url.split('/avatars/')[-1]
                if not old_object_name.startswith('avatars/'):
                    old_object_name = f"avatars/{old_object_name}"
                await delete_file_from_minio(old_object_name)
        except Exception as e:
            logger.warning(f"Failed to delete old avatar: {e}")
    
    # Return URL - store the object_name so we can retrieve it later
    # In dev mode, use proxy endpoint but store object_name for retrieval
    if settings.debug:
        # Store object_name in URL format that we can parse later
        return f"/api/v1/users/me/avatar?object={object_name}"
    else:
        # In production, return MinIO URL
        return f"{settings.minio_endpoint}/{settings.minio_bucket}/{object_name}"


async def delete_avatar(avatar_url: str) -> bool:
    """
    Delete avatar from storage.
    
    Args:
        avatar_url: Avatar URL
    
    Returns:
        True if deleted successfully
    """
    try:
        # Extract object name from URL
        if '/avatars/' in avatar_url:
            object_name = avatar_url.split('/avatars/')[-1]
            if not object_name.startswith('avatars/'):
                object_name = f"avatars/{object_name}"
            return await delete_file_from_minio(object_name)
        return False
    except Exception as e:
        logger.error(f"Error deleting avatar: {e}", exc_info=True)
        return False

