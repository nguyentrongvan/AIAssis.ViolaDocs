#!/usr/bin/env python3
"""
Script to check embedding jobs status from database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from src.app.models.ai import AIJob
from src.app.config import settings
from datetime import datetime

def check_embedding_jobs():
    """Check embedding jobs from database"""
    print("=" * 60)
    print("Embedding Jobs Checker")
    print("=" * 60)
    
    # Connect to database
    engine = create_engine(settings.postgres_dsn)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get all embedding jobs
        jobs = session.query(AIJob).filter(
            AIJob.job_type == "embed"
        ).order_by(AIJob.created_at.desc()).limit(20).all()
        
        print(f"\nTotal embedding jobs found: {len(jobs)}")
        
        if not jobs:
            print("\n⚠️  No embedding jobs found!")
            print("   This might mean:")
            print("   - No documents have been processed for embedding")
            print("   - Embedding jobs are not being created")
            return
        
        # Count by status
        status_counts = {}
        for job in jobs:
            status = job.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\n" + "-" * 60)
        print("Jobs by Status:")
        print("-" * 60)
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        # Show recent jobs
        print("\n" + "-" * 60)
        print("Recent Jobs (last 10):")
        print("-" * 60)
        
        for job in jobs[:10]:
            doc_id = job.target.get("document_id") if isinstance(job.target, dict) else None
            version_id = job.target.get("version_id") if isinstance(job.target, dict) else None
            
            print(f"\nJob ID: {job.id}")
            print(f"  Status: {job.status}")
            print(f"  Document ID: {doc_id}")
            print(f"  Version ID: {version_id}")
            print(f"  Provider: {job.provider}")
            print(f"  Created: {job.created_at}")
            if job.status == "completed":
                print(f"  Output: {job.output_ref}")
            if job.status == "failed":
                print(f"  Error: {job.error}")
            if job.worker_id:
                print(f"  Worker: {job.worker_id}")
        
        # Check for specific document ID
        if len(sys.argv) > 1:
            target_doc_id = int(sys.argv[1])
            print("\n" + "-" * 60)
            print(f"Jobs for Document ID: {target_doc_id}")
            print("-" * 60)
            
            doc_jobs = [j for j in jobs if j.target.get("document_id") == target_doc_id]
            
            if doc_jobs:
                print(f"\nFound {len(doc_jobs)} job(s) for document {target_doc_id}:")
                for job in doc_jobs:
                    print(f"\n  Job ID: {job.id}")
                    print(f"    Status: {job.status}")
                    print(f"    Version ID: {job.target.get('version_id')}")
                    print(f"    Created: {job.created_at}")
                    if job.status == "completed":
                        print(f"    Output: {job.output_ref}")
                        print(f"    ✓ Job completed successfully")
                    elif job.status == "failed":
                        print(f"    ✗ Job failed: {job.error}")
                    elif job.status == "processing":
                        print(f"    ⏳ Job is processing...")
                    elif job.status == "queued":
                        print(f"    ⏸ Job is queued (not started yet)")
            else:
                print(f"\n✗ No jobs found for document ID {target_doc_id}")
                print(f"  Available document IDs in recent jobs:")
                doc_ids = set()
                for job in jobs:
                    doc_id = job.target.get("document_id") if isinstance(job.target, dict) else None
                    if doc_id:
                        doc_ids.add(doc_id)
                print(f"    {sorted(list(doc_ids))}")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    check_embedding_jobs()

