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
import logging
from pathlib import Path

# Setup basic logging early (before imports that might need it)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=== OCR Worker Main Starting ===")
logger.info(f"Python version: {sys.version}")
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Python path: {sys.path}")

# Add src directory to Python path
try:
    backend_dir = Path(__file__).parent.parent.parent.parent
    src_dir = backend_dir / "src"
    logger.debug(f"Backend dir: {backend_dir}")
    logger.debug(f"Source dir: {src_dir}")
    logger.debug(f"Source dir exists: {src_dir.exists()}")
    
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))
        logger.debug(f"Added {src_dir} to Python path")
    else:
        # Try alternative path (if running from /app)
        alt_src_dir = Path("/app/src")
        if alt_src_dir.exists():
            sys.path.insert(0, str(alt_src_dir))
            logger.debug(f"Added {alt_src_dir} to Python path (alternative)")
        else:
            logger.warning(f"Source directory not found at {src_dir} or {alt_src_dir}")
except Exception as e:
    logger.error(f"Failed to setup Python path: {e}", exc_info=True)
    sys.exit(1)

# Import with error handling
try:
    logger.info("Importing OCRWorkerService...")
    from app.workers.ocr_worker_service import OCRWorkerService
    logger.info("OCRWorkerService imported successfully")
except ImportError as e:
    logger.error(f"Failed to import OCRWorkerService: {e}", exc_info=True)
    logger.error(f"Python path: {sys.path}")
    sys.exit(1)

try:
    logger.info("Importing settings...")
    from app.config import settings
    from app.utils.logging_config import setup_logging
    # Setup proper logging with settings
    setup_logging()
    logger.info("Settings imported successfully")
except ImportError as e:
    logger.error(f"Failed to import settings: {e}", exc_info=True)
    sys.exit(1)
except Exception as e:
    logger.error(f"Failed to load settings: {e}", exc_info=True)
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
        logger.info("Parsing arguments...")
        args = parse_args()
        logger.info("Arguments parsed successfully")
        
        # Get configuration
        worker_id = args.worker_id or os.getenv("WORKER_ID")
        poll_interval = args.poll_interval or int(os.getenv("OCR_WORKER_POLL_INTERVAL", "2"))
        max_concurrent = args.max_concurrent or int(os.getenv("OCR_WORKER_MAX_CONCURRENT", "2"))
        heartbeat_interval = args.heartbeat_interval or int(os.getenv("OCR_WORKER_HEARTBEAT_INTERVAL", "30"))
        stuck_timeout = args.stuck_timeout or int(os.getenv("OCR_WORKER_STUCK_TIMEOUT", "10"))
        
        logger.info("Worker configuration:")
        logger.info(f"  Worker ID: {worker_id}")
        logger.info(f"  Poll interval: {poll_interval}s")
        logger.info(f"  Max concurrent: {max_concurrent}")
        logger.info(f"  Heartbeat interval: {heartbeat_interval}s")
        logger.info(f"  Stuck timeout: {stuck_timeout} minutes")
        
        # Validate settings
        logger.info("Validating database connection...")
        try:
            # Try to access settings to validate connection
            db_host = getattr(settings, 'postgres_host', None)
            logger.info(f"  Database host: {db_host}")
        except Exception as e:
            logger.warning(f"Could not validate database settings: {e}")
        
        # Create worker
        logger.info("Creating OCRWorkerService...")
        worker = OCRWorkerService(
            worker_id=worker_id,
            poll_interval=poll_interval,
            max_concurrent=max_concurrent,
            heartbeat_interval=heartbeat_interval,
            stuck_job_timeout_minutes=stuck_timeout
        )
        logger.info("OCRWorkerService created successfully")
        
        # Run worker
        logger.info("Starting worker...")
        await worker.run()
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        if 'worker' in locals():
            worker.running = False
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        logger.info("Starting asyncio event loop...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"FATAL ERROR in event loop: {e}", exc_info=True)
        sys.exit(1)

