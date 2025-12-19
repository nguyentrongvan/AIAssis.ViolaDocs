#!/usr/bin/env python
"""
Test script to directly test Qdrant upsert functionality
"""
import os
import sys
import random

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from app.config import settings


def test_upsert():
    """Test Qdrant upsert directly"""
    print("=" * 60)
    print("Qdrant Direct Upsert Test")
    print("=" * 60)
    
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, Distance, VectorParams
    except ImportError:
        print("ERROR: qdrant-client not installed. Install with: pip install qdrant-client")
        return
    
    qdrant_host = getattr(settings, "qdrant_host", "localhost")
    qdrant_port = getattr(settings, "qdrant_port", 6333)
    qdrant_collection_name = getattr(settings, "qdrant_collection", "embeddings")
    qdrant_api_key = getattr(settings, "qdrant_api_key", None) or None
    
    print(f"\nConnecting to Qdrant at: {qdrant_host}:{qdrant_port}")
    client = QdrantClient(
        url=f"http://{qdrant_host}:{qdrant_port}" if not qdrant_host.startswith("http") else f"{qdrant_host}:{qdrant_port}",
        api_key=qdrant_api_key
    )
    
    # Check if collection exists
    try:
        collection_info = client.get_collection(qdrant_collection_name)
        initial_count = collection_info.points_count
        print(f"✓ Collection exists with {initial_count} points")
    except Exception:
        print(f"Collection '{qdrant_collection_name}' does not exist, will create")
        initial_count = 0
    
    # Test data
    test_doc_id = 9999
    test_version_id = 9999
    test_point_id = random.randint(100000, 999999)
    test_embedding = [random.random() for _ in range(768)]  # Example dimension
    test_payload = {
        "doc_id": test_doc_id,
        "version_id": test_version_id,
        "owner_id": 1,
        "provider": "test-ollama",
        "text_length": 100
    }
    
    # Create collection if it doesn't exist
    if initial_count == 0:
        try:
            client.create_collection(
                collection_name=qdrant_collection_name,
                vectors_config=VectorParams(
                    size=768,
                    distance=Distance.COSINE
                )
            )
            print(f"✓ Created collection '{qdrant_collection_name}'")
        except Exception as e:
            print(f"ERROR: Failed to create collection: {e}")
            import traceback
            traceback.print_exc()
            return
    
    print(f"\nAttempting to upsert test point with ID: {test_point_id}, doc_id: {test_doc_id}")
    try:
        client.upsert(
            collection_name=qdrant_collection_name,
            points=[
                PointStruct(
                    id=test_point_id,
                    vector=test_embedding,
                    payload=test_payload
                )
            ]
        )
        print("✓ Upsert successful")
    except Exception as e:
        print(f"ERROR: Upsert failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Verify
    try:
        collection_info = client.get_collection(qdrant_collection_name)
        final_count = collection_info.points_count
        print(f"Final point count: {final_count}")
        
        if final_count > initial_count:
            print("✓ Upsert successful: Point count increased")
            
            # Verify by retrieving the point
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            scroll_result, _ = client.scroll(
                collection_name=qdrant_collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchValue(value=test_doc_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False
            )
            
            if scroll_result[0]:
                print(f"✓ Successfully retrieved test point for doc_id {test_doc_id}")
                print("  Retrieved payload:", scroll_result[0][0].payload)
            else:
                print(f"✗ Failed to retrieve test point for doc_id {test_doc_id}")
        else:
            print("✗ Upsert failed: Point count did not increase")
    except Exception as e:
        print(f"ERROR: Failed to verify: {e}")
        import traceback
        traceback.print_exc()
    
    # Clean up test point
    print(f"\nAttempting to delete test point with ID: {test_point_id}")
    try:
        client.delete(
            collection_name=qdrant_collection_name,
            points_selector=[test_point_id]
        )
        print(f"✓ Successfully deleted test point {test_point_id}")
    except Exception as e:
        print(f"Warning: Failed to delete test point: {e}")
    
    try:
        final_count_after_cleanup = client.get_collection(qdrant_collection_name).points_count
        print(f"Final count after cleanup: {final_count_after_cleanup}")
    except:
        pass
    
    print("=" * 60)


if __name__ == "__main__":
    test_upsert()


