#!/usr/bin/env python
"""
Purge Worker Entry Point
Standalone service for purging soft-deleted documents past their grace period
"""
import asyncio
import argparse
import sys
import os
import signal
import traceback
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=== Purge Worker Main Starting ===")
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
    print("Importing purge_worker...")
    from app.workers.purge_worker import run_purge_worker
    print("purge_worker imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import purge_worker: {e}")
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
    parser = argparse.ArgumentParser(description="Purge Worker Service")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=None,
        help="Poll interval in seconds (default: from env PURGE_WORKER_POLL_INTERVAL or 3600)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Batch size - max documents to process per run (default: from env PURGE_WORKER_BATCH_SIZE or 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - only report what would be purged without actually deleting"
    )
    return parser.parse_args()


class PurgeWorkerService:
    """Service class for purge worker with graceful shutdown"""
    
    def __init__(self, poll_interval: int, batch_size: int, dry_run: bool = False):
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.running = True
        
    async def run(self):
        """Main worker loop"""
        logger.info("Purge worker service started")
        logger.info(f"Configuration:")
        logger.info(f"  Poll interval: {self.poll_interval}s ({self.poll_interval / 3600:.2f} hours)")
        logger.info(f"  Batch size: {self.batch_size}")
        logger.info(f"  Dry run: {self.dry_run}")
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        iteration = 0
        while self.running:
            try:
                iteration += 1
                logger.info(f"=== Purge worker iteration {iteration} ===")
                
                # Run purge worker
                stats = await run_purge_worker(
                    dry_run=self.dry_run,
                    batch_size=self.batch_size
                )
                
                logger.info(f"Purge iteration {iteration} completed: {stats}")
                
                # If no documents found and we're not in first iteration, log it
                if stats["found"] == 0 and iteration > 1:
                    logger.debug("No documents found for purging")
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in purge worker iteration {iteration}: {e}", exc_info=True)
                # Continue running even if one iteration fails
                # Sleep a bit before retrying to avoid rapid error loops
                await asyncio.sleep(60)
            
            if not self.running:
                break
            
            # Sleep for poll interval
            logger.info(f"Sleeping for {self.poll_interval}s until next purge cycle...")
            try:
                # Sleep in smaller chunks to allow for faster shutdown
                sleep_chunks = self.poll_interval // 10  # Check every 10 seconds
                for _ in range(sleep_chunks):
                    if not self.running:
                        break
                    await asyncio.sleep(10)
                # Sleep remaining time
                if self.running:
                    remaining = self.poll_interval % 10
                    if remaining > 0:
                        await asyncio.sleep(remaining)
            except asyncio.CancelledError:
                logger.info("Sleep cancelled, shutting down...")
                self.running = False
                break
        
        logger.info("Purge worker service stopped")


async def main():
    """Main entry point"""
    try:
        logger.info("Parsing arguments...")
        args = parse_args()
        logger.info("Arguments parsed successfully")
        
        # Get configuration from args, env vars, or defaults
        poll_interval = (
            args.poll_interval or 
            int(os.getenv("PURGE_WORKER_POLL_INTERVAL", "3600"))
        )
        batch_size = (
            args.batch_size or 
            int(os.getenv("PURGE_WORKER_BATCH_SIZE", "100"))
        )
        dry_run = args.dry_run or (os.getenv("PURGE_WORKER_DRY_RUN", "false").lower() == "true")
        
        logger.info(f"Final configuration:")
        logger.info(f"  Poll interval: {poll_interval}s")
        logger.info(f"  Batch size: {batch_size}")
        logger.info(f"  Dry run: {dry_run}")
        
        # Validate settings
        logger.info("Validating database connection...")
        try:
            db_host = getattr(settings, 'postgres_host', None)
            logger.info(f"  Database host: {db_host}")
        except Exception as e:
            logger.warning(f"Could not validate database settings: {e}")
        
        # Create and run worker service
        logger.info("Creating PurgeWorkerService...")
        worker = PurgeWorkerService(
            poll_interval=poll_interval,
            batch_size=batch_size,
            dry_run=dry_run
        )
        logger.info("PurgeWorkerService created successfully")
        
        # Run worker
        logger.info("Starting purge worker...")
        await worker.run()
        
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
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
        logger.info("\nWorker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"FATAL ERROR in event loop: {e}", exc_info=True)
        sys.exit(1)


