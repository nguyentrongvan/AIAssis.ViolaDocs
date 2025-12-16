#!/usr/bin/env python
"""
OCR Worker Entry Point
Standalone service for processing OCR jobs from database
"""
import asyncio
import argparse
import sys
import os
import signal
import traceback
from pathlib import Path

print("=== OCR Worker Main Starting ===")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

# Add src directory to Python path
try:
    backend_dir = Path(__file__).parent.parent.parent.parent
    src_dir = backend_dir / "src"
    print(f"Backend dir: {backend_dir}")
    print(f"Source dir: {src_dir}")
    print(f"Source dir exists: {src_dir.exists()}")
    
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))
        print(f"Added {src_dir} to Python path")
    else:
        # Try alternative path (if running from /app)
        alt_src_dir = Path("/app/src")
        if alt_src_dir.exists():
            sys.path.insert(0, str(alt_src_dir))
            print(f"Added {alt_src_dir} to Python path (alternative)")
        else:
            print(f"WARNING: Source directory not found at {src_dir} or {alt_src_dir}")
except Exception as e:
    print(f"ERROR: Failed to setup Python path: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import with error handling
try:
    print("Importing OCRWorkerService...")
    from app.workers.ocr_worker_service import OCRWorkerService
    print("OCRWorkerService imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import OCRWorkerService: {e}")
    print(f"Python path: {sys.path}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("Importing settings...")
    from app.config import settings
    print("Settings imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import settings: {e}")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Failed to load settings: {e}")
    traceback.print_exc()
    sys.exit(1)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="OCR Worker Service")
    parser.add_argument(
        "--worker-id",
        type=str,
        default=None,
        help="Worker ID (default: auto-generated)"
    )
    # Get default values safely
    try:
        default_poll = getattr(settings, 'worker_batch_size', 2)
        default_max = getattr(settings, 'max_concurrent_ocr_jobs', 2)
    except:
        default_poll = 2
        default_max = 2
    
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=None,
        help=f"Poll interval in seconds (default: {default_poll})"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=None,
        help=f"Max concurrent jobs (default: {default_max})"
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=30,
        help="Heartbeat interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--stuck-timeout",
        type=int,
        default=10,
        help="Stuck job timeout in minutes (default: 10)"
    )
    return parser.parse_args()


async def main():
    """Main entry point"""
    try:
        print("Parsing arguments...")
        args = parse_args()
        print("Arguments parsed successfully")
        
        # Get configuration
        worker_id = args.worker_id or os.getenv("WORKER_ID")
        poll_interval = args.poll_interval or int(os.getenv("OCR_WORKER_POLL_INTERVAL", "2"))
        max_concurrent = args.max_concurrent or int(os.getenv("OCR_WORKER_MAX_CONCURRENT", "2"))
        heartbeat_interval = args.heartbeat_interval or int(os.getenv("OCR_WORKER_HEARTBEAT_INTERVAL", "30"))
        stuck_timeout = args.stuck_timeout or int(os.getenv("OCR_WORKER_STUCK_TIMEOUT", "10"))
        
        print(f"Worker configuration:")
        print(f"  Worker ID: {worker_id}")
        print(f"  Poll interval: {poll_interval}s")
        print(f"  Max concurrent: {max_concurrent}")
        print(f"  Heartbeat interval: {heartbeat_interval}s")
        print(f"  Stuck timeout: {stuck_timeout} minutes")
        
        # Validate settings
        print("Validating database connection...")
        try:
            # Try to access settings to validate connection
            db_host = getattr(settings, 'postgres_host', None)
            print(f"  Database host: {db_host}")
        except Exception as e:
            print(f"WARNING: Could not validate database settings: {e}")
        
        # Create worker
        print("Creating OCRWorkerService...")
        worker = OCRWorkerService(
            worker_id=worker_id,
            poll_interval=poll_interval,
            max_concurrent=max_concurrent,
            heartbeat_interval=heartbeat_interval,
            stuck_job_timeout_minutes=stuck_timeout
        )
        print("OCRWorkerService created successfully")
        
        # Run worker
        print("Starting worker...")
        await worker.run()
        
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        if 'worker' in locals():
            worker.running = False
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        print("Starting asyncio event loop...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWorker interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"FATAL ERROR in event loop: {e}")
        traceback.print_exc()
        sys.exit(1)

