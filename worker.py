"""
Background worker for processing message queue
Runs continuously to process pending messages
"""
import asyncio
import signal
import sys
from app.api.webhook import process_message_queue
from app.utils.logger import setup_logging, get_worker_logger

# Set up logging
setup_logging()
logger = get_worker_logger("message_worker")


class Worker:
    """Background worker for message processing"""
    
    def __init__(self):
        self.running = True
        
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)
    
    async def run(self):
        """Run the worker"""
        logger.info("Starting message queue worker...")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        
        # Start processing queue
        try:
            await process_message_queue()
        except Exception as e:
            logger.error(f"Worker error: {str(e)}", exc_info=True)
            raise


async def main():
    """Main entry point for worker"""
    worker = Worker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())