from typing import Optional, Dict, List
import difflib
import io
from ..services.storage import get_minio_client
from ..config import settings


async def get_text_from_uri(text_uri: str) -> Optional[str]:
    """Retrieve text content from storage URI."""
    try:
        client = get_minio_client()
        
        # Parse bucket and object name from URI
        # URI formats:
        # 1. minio://bucket/path/to/file
        # 2. s3://bucket/path/to/file
        # 3. path/to/file (use default bucket from settings)
        bucket_name = settings.minio_bucket
        object_name = text_uri
        
        if text_uri.startswith("minio://"):
            # Format: minio://bucket/path/to/file
            uri_without_prefix = text_uri.replace("minio://", "")
            parts = uri_without_prefix.split("/", 1)
            if len(parts) == 2:
                bucket_name, object_name = parts
            else:
                object_name = uri_without_prefix
        elif text_uri.startswith("s3://"):
            # Format: s3://bucket/path/to/file
            uri_without_prefix = text_uri.replace("s3://", "")
            parts = uri_without_prefix.split("/", 1)
            if len(parts) == 2:
                bucket_name, object_name = parts
            else:
                object_name = uri_without_prefix
        else:
            # Plain path format: path/to/file - use default bucket
            # text_uri is already the object name
            object_name = text_uri
        
        # Read object
        response = client.get_object(bucket_name, object_name)
        content = response.read()
        response.close()
        response.release_conn()
        
        return content.decode('utf-8')
    except Exception as e:
        print(f"Error reading text from URI {text_uri}: {e}")
        return None


def compute_text_diff(text1: str, text2: str) -> Dict:
    """Compute text diff between two versions."""
    lines1 = text1.splitlines(keepends=True)
    lines2 = text2.splitlines(keepends=True)
    
    # Use difflib to compute differences
    diff = list(difflib.unified_diff(
        lines1, lines2,
        lineterm='',
        n=3  # Context lines
    ))
    
    # Parse diff into structured format
    added_lines = []
    removed_lines = []
    changed_blocks = []
    
    current_block = None
    for line in diff:
        if line.startswith('+++') or line.startswith('---'):
            continue
        elif line.startswith('@@'):
            # New block
            if current_block:
                changed_blocks.append(current_block)
            current_block = {
                "old_start": 0,
                "old_count": 0,
                "new_start": 0,
                "new_count": 0,
                "changes": []
            }
            # Parse @@ line (simplified)
            parts = line.split()
            if len(parts) >= 2:
                old_info = parts[1][1:]  # Remove +
                new_info = parts[2][1:]  # Remove +
                if ',' in old_info:
                    old_start, old_count = map(int, old_info.split(','))
                    current_block["old_start"] = old_start
                    current_block["old_count"] = old_count
                if ',' in new_info:
                    new_start, new_count = map(int, new_info.split(','))
                    current_block["new_start"] = new_start
                    current_block["new_count"] = new_count
        elif line.startswith('+') and not line.startswith('+++'):
            added_lines.append(line[1:])
            if current_block:
                current_block["changes"].append({"type": "added", "line": line[1:]})
        elif line.startswith('-') and not line.startswith('---'):
            removed_lines.append(line[1:])
            if current_block:
                current_block["changes"].append({"type": "removed", "line": line[1:]})
        elif line.startswith(' '):
            if current_block:
                current_block["changes"].append({"type": "unchanged", "line": line[1:]})
    
    if current_block:
        changed_blocks.append(current_block)
    
    return {
        "added_count": len(added_lines),
        "removed_count": len(removed_lines),
        "added_lines": added_lines[:50],  # Limit to first 50
        "removed_lines": removed_lines[:50],  # Limit to first 50
        "changed_blocks": changed_blocks[:20],  # Limit to first 20 blocks
        "unified_diff": diff[:100]  # Limit to first 100 lines
    }


async def compare_versions(
    v1_text_uri: Optional[str],
    v2_text_uri: Optional[str],
    v1_metadata: Optional[Dict],
    v2_metadata: Optional[Dict]
) -> Dict:
    """Compare two document versions."""
    result = {
        "content_diff": None,
        "metadata_diff": {},
        "has_content_diff": False,
        "has_metadata_diff": False
    }
    
    # Compare text content if available
    if v1_text_uri and v2_text_uri:
        text1 = await get_text_from_uri(v1_text_uri)
        text2 = await get_text_from_uri(v2_text_uri)
        
        if text1 and text2:
            if text1 != text2:
                result["content_diff"] = compute_text_diff(text1, text2)
                result["has_content_diff"] = True
            else:
                result["content_diff"] = {"message": "No text differences"}
        elif text1 or text2:
            result["content_diff"] = {"message": "One version missing text content"}
    elif v1_text_uri or v2_text_uri:
        result["content_diff"] = {"message": "Only one version has text content"}
    else:
        result["content_diff"] = {"message": "No text content available for comparison"}
    
    # Compare metadata
    if v1_metadata and v2_metadata:
        metadata_diff = {}
        all_keys = set(v1_metadata.keys()) | set(v2_metadata.keys())
        
        for key in all_keys:
            val1 = v1_metadata.get(key)
            val2 = v2_metadata.get(key)
            
            if val1 != val2:
                metadata_diff[key] = {
                    "old": val1,
                    "new": val2
                }
                result["has_metadata_diff"] = True
        
        result["metadata_diff"] = metadata_diff
    elif v1_metadata or v2_metadata:
        result["metadata_diff"] = {
            "message": "Only one version has metadata",
            "v1": v1_metadata,
            "v2": v2_metadata
        }
        result["has_metadata_diff"] = True
    
    return result

