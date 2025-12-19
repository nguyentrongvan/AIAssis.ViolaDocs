#!/usr/bin/env python
"""
Script to check Qdrant collection and verify embeddings
"""
import os
import sys
from typing import Optional

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from app.config import settings


def check_qdrant_collection(doc_id: Optional[int] = None):
    """Check Qdrant collection status"""
    print("=" * 60)
    print("Qdrant Collection Checker")
    print("=" * 60)
    
    try:
        from qdrant_client import QdrantClient
        
        qdrant_host = getattr(settings, "qdrant_host", "localhost")
        qdrant_port = getattr(settings, "qdrant_port", 6333)
        qdrant_collection_name = getattr(settings, "qdrant_collection", "embeddings")
        qdrant_api_key = getattr(settings, "qdrant_api_key", None) or None
        
        print(f"\nConnecting to Qdrant at: {qdrant_host}:{qdrant_port}")
        client = QdrantClient(
            url=f"http://{qdrant_host}:{qdrant_port}" if not qdrant_host.startswith("http") else f"{qdrant_host}:{qdrant_port}",
            api_key=qdrant_api_key
        )
        
        print("\n" + "-" * 60)
        print("Available Collections:")
        print("-" * 60)
        collections = client.get_collections().collections
        if not collections:
            print("  No collections found.")
            return
        
        for col in collections:
            print(f"  - {col.name} (points: {col.points_count})")
        
        print("\n" + "-" * 60)
        print(f"Checking Collection: '{qdrant_collection_name}'")
        print("-" * 60)
        
        try:
            collection_info = client.get_collection(qdrant_collection_name)
            print("✓ Collection exists")
            print(f"  Points count: {collection_info.points_count}")
            print(f"  Vector size: {collection_info.config.params.vectors.size}")
            print(f"  Distance: {collection_info.config.params.vectors.distance}")
        except Exception as e:
            print(f"✗ Collection '{qdrant_collection_name}' not found: {e}")
            return
        
        total_points = collection_info.points_count
        if total_points == 0:
            print("⚠️  WARNING: Collection is EMPTY!")
            print("   No embeddings found in Qdrant.")
            return
        
        # Get sample points
        print("\n" + "-" * 60)
        print("Sample Points:")
        print("-" * 60)
        try:
            scroll_result, _ = client.scroll(
                collection_name=qdrant_collection_name,
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            
            doc_ids_in_qdrant = set()
            for point in scroll_result:
                payload = point.payload if point.payload else {}
                doc_id = payload.get("doc_id")
                if doc_id is not None:
                    try:
                        doc_ids_in_qdrant.add(int(doc_id))
                    except (ValueError, TypeError):
                        pass
            
            print(f"Unique doc_ids with embeddings: {len(doc_ids_in_qdrant)}")
            print(f"Sample doc_ids: {sorted(list(doc_ids_in_qdrant))[:10]}")
            
            if doc_id:
                print(f"\nChecking specific Document ID: {doc_id}")
                # Search for points with this doc_id
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                search_result = client.scroll(
                    collection_name=qdrant_collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="doc_id",
                                match=MatchValue(value=doc_id)
                            )
                        ]
                    ),
                    limit=10,
                    with_payload=True,
                    with_vectors=False
                )
                
                if search_result[0]:
                    print(f"✓ Found {len(search_result[0])} points for doc_id {doc_id}")
                    print("  Sample payload:", search_result[0][0].payload if search_result[0] else "N/A")
                else:
                    print(f"✗ No points found for doc_id {doc_id}")
        except Exception as e:
            print(f"Error getting sample points: {e}")
            import traceback
            traceback.print_exc()
    
    except ImportError:
        print("\nERROR: qdrant-client not installed. Install with: pip install qdrant-client")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    target_doc_id = None
    if len(sys.argv) > 1:
        try:
            target_doc_id = int(sys.argv[1])
        except ValueError:
            print(f"Invalid document ID: {sys.argv[1]}. Please provide an integer.")
            sys.exit(1)
    check_qdrant_collection(target_doc_id)


