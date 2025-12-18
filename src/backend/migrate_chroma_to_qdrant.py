#!/usr/bin/env python
"""
Migration script to migrate embeddings from ChromaDB to Qdrant
"""
import os
import sys
import argparse
from typing import List, Dict, Any

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

from app.config import settings


def migrate_chroma_to_qdrant(dry_run: bool = False):
    """Migrate embeddings from ChromaDB to Qdrant"""
    print("=" * 60)
    print("ChromaDB to Qdrant Migration Script")
    print("=" * 60)
    
    if dry_run:
        print("DRY RUN MODE - No data will be written")
    
    # Import ChromaDB
    try:
        import chromadb
        print("✓ ChromaDB imported")
    except ImportError:
        print("ERROR: chromadb not installed. Install with: pip install chromadb")
        return False
    
    # Import Qdrant
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, Distance, VectorParams
        print("✓ Qdrant client imported")
    except ImportError:
        print("ERROR: qdrant-client not installed. Install with: pip install qdrant-client")
        return False
    
    # Connect to ChromaDB
    print("\n" + "-" * 60)
    print("Connecting to ChromaDB...")
    print("-" * 60)
    
    chroma_host = getattr(settings, "chroma_server_host", "")
    chroma_port = getattr(settings, "chroma_server_port", 8001)
    chroma_collection_name = getattr(settings, "chroma_collection", "embeddings")
    
    try:
        if chroma_host:
            chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
            print(f"✓ Connected to ChromaDB HTTP server: {chroma_host}:{chroma_port}")
        else:
            chroma_persist_dir = getattr(settings, "chroma_persist_dir", "./data/chroma")
            chroma_client = chromadb.PersistentClient(path=chroma_persist_dir)
            print(f"✓ Connected to ChromaDB persistent store: {chroma_persist_dir}")
        
        chroma_collection = chroma_client.get_collection(name=chroma_collection_name)
        chroma_count = chroma_collection.count()
        print(f"✓ ChromaDB collection '{chroma_collection_name}' has {chroma_count} embeddings")
    except Exception as e:
        print(f"ERROR: Failed to connect to ChromaDB: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if chroma_count == 0:
        print("⚠️  ChromaDB collection is empty. Nothing to migrate.")
        return True
    
    # Connect to Qdrant
    print("\n" + "-" * 60)
    print("Connecting to Qdrant...")
    print("-" * 60)
    
    qdrant_host = getattr(settings, "qdrant_host", "localhost")
    qdrant_port = getattr(settings, "qdrant_port", 6333)
    qdrant_collection_name = getattr(settings, "qdrant_collection", "embeddings")
    qdrant_api_key = getattr(settings, "qdrant_api_key", None) or None
    
    try:
        qdrant_client = QdrantClient(
            url=f"http://{qdrant_host}:{qdrant_port}" if not qdrant_host.startswith("http") else f"{qdrant_host}:{qdrant_port}",
            api_key=qdrant_api_key
        )
        print(f"✓ Connected to Qdrant: {qdrant_host}:{qdrant_port}")
    except Exception as e:
        print(f"ERROR: Failed to connect to Qdrant: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Check if Qdrant collection exists
    try:
        qdrant_collection_info = qdrant_client.get_collection(qdrant_collection_name)
        qdrant_count = qdrant_collection_info.points_count
        print(f"⚠️  Qdrant collection '{qdrant_collection_name}' already exists with {qdrant_count} points")
        response = input("Do you want to continue? This will add to existing collection (y/n): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return False
    except Exception:
        print(f"✓ Qdrant collection '{qdrant_collection_name}' does not exist, will be created")
        qdrant_count = 0
    
    # Read all data from ChromaDB
    print("\n" + "-" * 60)
    print("Reading data from ChromaDB...")
    print("-" * 60)
    
    try:
        chroma_data = chroma_collection.get()
        chroma_ids = chroma_data.get("ids", [])
        chroma_embeddings = chroma_data.get("embeddings", [])
        chroma_metadatas = chroma_data.get("metadatas", [])
        
        print(f"✓ Read {len(chroma_ids)} embeddings from ChromaDB")
        
        if len(chroma_ids) == 0:
            print("⚠️  No embeddings found in ChromaDB")
            return True
        
        # Get embedding dimension
        if chroma_embeddings and len(chroma_embeddings) > 0:
            embedding_dim = len(chroma_embeddings[0])
            print(f"✓ Embedding dimension: {embedding_dim}")
        else:
            print("ERROR: No embeddings found")
            return False
    except Exception as e:
        print(f"ERROR: Failed to read from ChromaDB: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Create Qdrant collection if it doesn't exist
    if qdrant_count == 0:
        print("\n" + "-" * 60)
        print("Creating Qdrant collection...")
        print("-" * 60)
        
        if not dry_run:
            try:
                qdrant_client.create_collection(
                    collection_name=qdrant_collection_name,
                    vectors_config=VectorParams(
                        size=embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                print(f"✓ Created Qdrant collection '{qdrant_collection_name}' with dimension {embedding_dim}")
            except Exception as e:
                print(f"ERROR: Failed to create Qdrant collection: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print(f"[DRY RUN] Would create Qdrant collection '{qdrant_collection_name}' with dimension {embedding_dim}")
    
    # Migrate data in batches
    print("\n" + "-" * 60)
    print("Migrating embeddings to Qdrant...")
    print("-" * 60)
    
    batch_size = 100
    total_batches = (len(chroma_ids) + batch_size - 1) // batch_size
    migrated_count = 0
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(chroma_ids))
        
        batch_ids = chroma_ids[start_idx:end_idx]
        batch_embeddings = chroma_embeddings[start_idx:end_idx]
        batch_metadatas = chroma_metadatas[start_idx:end_idx] if chroma_metadatas else [{}] * len(batch_ids)
        
        # Prepare points for Qdrant
        points = []
        for idx, (point_id, embedding, metadata) in enumerate(zip(batch_ids, batch_embeddings, batch_metadatas)):
            # Convert point_id to int if possible
            try:
                if point_id.startswith("embed-"):
                    numeric_id = int(point_id.split("-")[-1])
                else:
                    numeric_id = int(point_id)
                point_id_typed = numeric_id
            except (ValueError, IndexError):
                point_id_typed = point_id
            
            points.append(
                PointStruct(
                    id=point_id_typed,
                    vector=embedding,
                    payload=metadata if metadata else {}
                )
            )
        
        if not dry_run:
            try:
                qdrant_client.upsert(
                    collection_name=qdrant_collection_name,
                    points=points
                )
                migrated_count += len(points)
                print(f"✓ Migrated batch {batch_idx + 1}/{total_batches} ({len(points)} points)")
            except Exception as e:
                print(f"ERROR: Failed to upsert batch {batch_idx + 1}: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            migrated_count += len(points)
            print(f"[DRY RUN] Would migrate batch {batch_idx + 1}/{total_batches} ({len(points)} points)")
    
    # Verify migration
    print("\n" + "-" * 60)
    print("Verifying migration...")
    print("-" * 60)
    
    if not dry_run:
        try:
            qdrant_collection_info = qdrant_client.get_collection(qdrant_collection_name)
            final_count = qdrant_collection_info.points_count
            print(f"✓ Qdrant collection now has {final_count} points")
            
            if final_count >= chroma_count:
                print(f"✓ Migration successful! Migrated {migrated_count} embeddings")
                print(f"  ChromaDB: {chroma_count} embeddings")
                print(f"  Qdrant: {final_count} points")
                return True
            else:
                print(f"⚠️  WARNING: Qdrant count ({final_count}) is less than ChromaDB count ({chroma_count})")
                return False
        except Exception as e:
            print(f"ERROR: Failed to verify migration: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"[DRY RUN] Would migrate {migrated_count} embeddings")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate embeddings from ChromaDB to Qdrant")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode - don't write data")
    args = parser.parse_args()
    
    success = migrate_chroma_to_qdrant(dry_run=args.dry_run)
    sys.exit(0 if success else 1)

